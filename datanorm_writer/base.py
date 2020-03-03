import logging
from collections import OrderedDict
from typing import Mapping
from unicodedata import normalize

logger = logging.getLogger(__name__)


class FieldBase(object):
    creation_counter = 0

    def __init__(
        self,
        max_length=None,
        length=None,
        name=None,
        index=None,
        blank=False,
        required=False,
    ):
        if length and max_length and length != max_length:
            raise ValueError("max_length != length")

        self.creation_counter = FieldBase.creation_counter
        FieldBase.creation_counter += 1

        self.length = length
        self.max_length = max_length
        self.name = name
        self.required = required
        self.index = index
        self.blank = blank
        self.field_name = None
        self._value = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = self.process(value)

    @property
    def feldnummer(self):
        return self.index + 1

    def __str__(self):
        return self.name

    def process(self, value=None) -> str:
        raise NotImplementedError("Define in concrete field types")


def get_declared_fields(bases, attrs):
    """
    Create a list of form field instances from the passed in 'attrs', plus any
    similar fields on the base classes (in 'bases'). This is used by both the
    Form and ModelForm metclasses.
    """
    fields = [
        (field_name, attrs.get(field_name))
        for field_name, obj in list(attrs.items())
        if isinstance(obj, FieldBase)
    ]
    fields = sorted(fields, key=lambda x: x[1].creation_counter)
    for index, (field_name, field) in enumerate(fields):
        assert isinstance(field_name, str)
        assert isinstance(field, FieldBase)
        if field.name is None:
            field.name = field_name.replace("_", " ").capitalize()
            field.index = index
        field.field_name = field_name

    fields.sort(key=lambda x: x[1].creation_counter)
    return OrderedDict(fields)


valid_ascii_characters = (
    "\t !\"#$%&'()*+,-./0123456789:<=>?@^_"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz[]"
)


custom_characters = {
    "ü": b"\x81",
    "ö": b"\x94",
    "ä": b"\x84",
    "Ü": b"\x9a",
    "Ä": b"\x8e",
    "Ö": b"\x99",
    "ß": b"\xe1",
}


charset_translations = dict((x, x.encode("ascii")) for x in valid_ascii_characters)
charset_translations.update(custom_characters)


def normalize_and_encode(
    charset: Mapping[str, bytes], value: str, field_name=None
) -> bytes:
    """
    unicode normalize value and translate it into the datanorm charset

    :param charset: A mapping from string to bytes
    :param value: A unicode string to be translated.
    :param field_name: An optional field name to improve errors
    :return:
    """
    value = normalize(
        "NFKC", value
    )  # normalize composed unicode characters into decomposed ones

    invalid = set(value) - set(charset.keys())

    if invalid:
        error = "Invalid characters %s in string" % ", ".join(invalid)
        if field_name:
            error += " translating field {}".format(field_name)
        logger.error(error)

    return b"".join(charset.get(x, b"") for x in value)


def chunk_text(text, chunk_size, split_char=" "):
    text = normalize(
        "NFKC", text
    )  # normalize composed unicode characters into decomposed ones

    lines = text.splitlines()
    chunks = []
    for line in lines:
        while True:
            line = line.strip()
            if len(line) > chunk_size:
                separate_at = line[:chunk_size].rfind(split_char)
                if separate_at == -1:
                    separate_at = chunk_size
                chunk, line = line[:separate_at], line[separate_at:]
                chunks.append(chunk)
            else:
                chunks.append(line)
                break
    return chunks


class StringField(FieldBase):
    def __init__(self, values=None, **kwargs):
        self.values = None
        super(StringField, self).__init__(**kwargs)

    def process(self, value=None) -> str:
        if not value and self.blank:
            return ""

        if not value and self.required:
            raise ValueError(self.field_name, "Field must not be empty")

        if self.values and value not in self.values:
            raise ValueError(
                self.field_name, "Value %s not in %s" % (value, self.values)
            )

        if value is None and self.length:
            raise ValueError(self.field_name, "Field with fixed length can't be None")

        value = str(value or "")
        if self.length and len(value) != self.length:
            raise ValueError(
                self.field_name, "Fixed length string needs value of matching length"
            )
        elif self.max_length and len(value) > self.max_length:
            raise ValueError(self.field_name, "Value longer than max_length")

        value = value.replace(
            "\n", " "
        )  # This doesn't change the length, so it's okay after the length check

        return value


class IntegerField(FieldBase):
    def __init__(self, values=None, **kwargs):
        self.values = values
        super(IntegerField, self).__init__(**kwargs)

    def process(self, value=None) -> str:
        if self.blank and value is None:
            return ""

        if value is None and self.length:
            raise ValueError(self.field_name, "Field with fixed length can't be None")
        if self.values and value not in self.values:
            raise ValueError(self.field_name, "Value %s not allowed" % value)

        if self.length:
            try:
                return "%0*d" % (self.length, value)
            except TypeError as e:
                raise ValueError(
                    "{}: Value {} can't be converted".format(self.field_name, value)
                ) from e

        if value is None:
            return ""

        as_bytes = "%d" % (value,)
        if len(as_bytes) > self.max_length:
            raise ValueError(
                self.field_name,
                "Number %s too big for max_length %s" % (value, self.max_length),
            )
        return as_bytes


class ShortDateField(StringField):
    """Format is TTMMJJ"""

    def __init__(self, **kwargs):
        kwargs["length"] = 6
        super(ShortDateField, self).__init__(**kwargs)

    def process(self, value=None) -> str:
        if not value and self.blank:
            return ""

        if value is None:
            raise ValueError("None is not a valid date")

        if hasattr(value, "date"):
            value = value.date

        return super(ShortDateField, self).process(value.strftime("%d%m%y"))


class DateField(StringField):
    """Format is JJJJMMTT"""

    def __init__(self, **kwargs):
        kwargs["length"] = 8
        super(DateField, self).__init__(**kwargs)

    def process(self, value=None) -> str:
        if not value and self.blank:
            return ""
        if value is None:
            raise ValueError("None is not a valid date")

        if hasattr(value, "date"):
            value = value.date

        return super(DateField, self).process(
            "%04d%02d%02d" % (value.year, value.month, value.day)
        )


class CurrencyField(StringField):
    """ISO 4217, eg EUR, USD, ..."""

    def __init__(self, **kwargs):
        kwargs["length"] = 3
        super(CurrencyField, self).__init__(**kwargs)


class StaticField(StringField):
    def __init__(self, static_value, **kwargs):
        self.static_value = static_value
        kwargs["length"] = len(static_value)
        super(StaticField, self).__init__(**kwargs)

    def process(self, value=None) -> str:
        if value is not None and value != self.static_value:
            raise ValueError(
                self.field_name,
                "invalid value %s should be %s" % (value, self.static_value),
            )
        return self.static_value


class RowMeta(type):
    def __new__(cls, name, bases, attrs):
        attrs["base_fields"] = get_declared_fields(bases, attrs)
        new_class = super(RowMeta, cls).__new__(cls, name, bases, attrs)
        return new_class


class RowBase(object, metaclass=RowMeta):
    base_fields = OrderedDict()
    separator = b";"
    charset = charset_translations

    def __init__(self, **kwargs):
        self.fields = self.base_fields
        super(RowBase, self).__init__()
        self.values = {}
        for field_name in self.fields:
            self.values[field_name] = kwargs.get(field_name)

    def __str__(self):
        return self.separator.decode("ascii").join(
            "%s:%s" % (field.feldnummer, field.name)
            for field in list(self.fields.values())
        )

    @property
    def output(self) -> bytes:
        return (
            self.separator.join(
                normalize_and_encode(
                    self.charset, field.process(self.values[field_name]), field_name
                )
                for (field_name, field) in list(self.fields.items())
            )
            + self.separator
        )


class ChoiceMeta(type):
    def __new__(cls, name, bases, attrs):
        fields = {}
        fields.update(attrs)
        attrs["_fields"] = fields
        new_class = super(ChoiceMeta, cls).__new__(cls, name, bases, attrs)
        return new_class


class ChoiceBase(object, metaclass=ChoiceMeta):
    _fields = {}

    @classmethod
    def values(cls):
        return list(cls._fields.values())
