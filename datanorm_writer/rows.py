import itertools
import logging

from .base import IntegerField, RowBase, ShortDateField, StaticField, StringField

logger = logging.getLogger(__name__)


class VorlaufZeile(RowBase):
    satzartenkennzeichen = StaticField("V")
    dummy = StaticField(" ")
    erstellungsdatum = ShortDateField()

    informationstext1 = StringField(length=40)
    informationstext2 = StringField(length=40)
    informationstext3 = StringField(length=35)

    version = StaticField("04")

    # ISO 4217 currency
    waehrungskennzeichen = StaticField("EUR")

    separator = b""

    @property
    def output(self) -> bytes:
        output = super().output
        # has to be fixed size of 128 to be recognized as datanorm 4
        assert len(output) == 128
        return output


class Artikelzeile(RowBase):
    satzartenkennzeichen = StaticField("A")
    verarbeitungsmerker = StringField(values="AN", length=1)
    artikelnummer = StringField(max_length=15)

    TEXT_KURZ1_KURZ2 = "0"
    TEXT_LANG_KURZ2 = "1"
    TEXT_KURZ1_DIM = "2"
    TEXT_LANG_DIM = "3"
    TEXT_KURZ1_KURZ2_LANG = "4"
    TEXT_KURZ1_KURZ2_DIM = "5"
    TEXT_KURZ1_KURZ2_LANG_DIM = "6"

    TEXT_HAS_KURZ2_TRUE = "0"
    TEXT_HAS_KURZ2_FALSE = "1"

    # is actually an integer field but with fixed choices
    textkennzeichen = StringField(
        values=(
            "".join(x)
            for x in itertools.product(
                [
                    TEXT_KURZ1_KURZ2,
                    TEXT_LANG_KURZ2,
                    TEXT_KURZ1_DIM,
                    TEXT_LANG_DIM,
                    TEXT_KURZ1_KURZ2_LANG,
                    TEXT_KURZ1_KURZ2_DIM,
                    TEXT_KURZ1_KURZ2_LANG_DIM,
                ],
                [TEXT_HAS_KURZ2_TRUE, TEXT_HAS_KURZ2_FALSE],
            )
        ),
        length=2,
    )

    kurztext_1 = StringField(max_length=40)
    kurztext_2 = StringField(max_length=40)

    PREIS_LISTENPREIS = 1
    PREIS_NETTOPREIS = 2
    preiskennzeichen = IntegerField(
        values=(PREIS_LISTENPREIS, PREIS_NETTOPREIS,), length=1
    )

    PRICE_BY_1_UNIT = 0
    PRICE_BY_10_UNITS = 1
    PRICE_BY_100_UNITS = 2
    PRICE_BY_1000_UNITS = 3
    preiseinheit = IntegerField(
        max_length=6,
        values=[
            PRICE_BY_1_UNIT,
            PRICE_BY_10_UNITS,
            PRICE_BY_100_UNITS,
            PRICE_BY_1000_UNITS,
        ],
    )

    # unit that the price is based on
    mengeneinheit = StringField(max_length=4)

    # price in cents, just use the first of the level prices
    preis = IntegerField(max_length=8)

    rabattgruppe = StringField(max_length=4)

    hauptwarengruppe = StringField(max_length=3)

    langtextnummer = StringField(max_length=15)


class Artikelzeile2(RowBase):
    satzartenkennzeichen = StaticField("B")
    verarbeitungsmerker = StringField(values="AN", length=1)

    artikelnummer = StringField(max_length=15)

    matchcode = StringField(max_length=15)

    alternativ_artikelnummer = StringField(max_length=15)

    katalogseite = StringField(max_length=8)

    kupfer_gewichtsmerker = StaticField("0")
    kupfer_kennzahl = StaticField("0")
    kupfer_gewicht = StaticField("0")

    ean = StringField(max_length=18)

    anbindungsnummer = StringField(max_length=12)

    warengruppe = StringField(max_length=10)

    kostenart = StaticField("0")

    # smallest number of price units that can be ordered
    verpackungsmenge = IntegerField(max_length=5)

    referenznummer_erstellerkuerzel = StringField(max_length=4)

    referenznummer = StringField(max_length=17)


class Langtextzeile(RowBase):
    satzartenkennzeichen = StaticField("T")
    verarbeitungsmerker = StringField(values="ANL", length=1)
    langtextnummer = StringField(max_length=8)

    dummy_1 = StaticField("")

    zeilennummer_1 = IntegerField(max_length=2)

    dummy_2 = StaticField("")

    langtextzeile_1 = StringField(max_length=40)

    zeilennummer_2 = IntegerField(max_length=2)

    dummy_3 = StaticField("")

    langtextzeile_2 = StringField(max_length=40)


class Staffelpreiszeile(RowBase):
    satzartenkennzeichen = StaticField("Z")
    verarbeitungsmerker = StringField(values="ANL", length=1)
    artikelnummer = StringField(max_length=15)

    # starting at 1
    satznummer = IntegerField(max_length=2)

    bearbeitungsmerker = StaticField("1")  # scaled prices

    ORDER_QUANTITY = "1"
    DISTANCE_KM = "2"
    DATE = "3"
    OTHER = "4"
    basismerker = StringField(
        values=[ORDER_QUANTITY, DISTANCE_KM, DATE, OTHER], length=1
    )

    basisbeschreibung = StringField(max_length=28)

    LIST_PRICE = "1"
    NET_PRICE = "2"
    preiskennzeichen = StringField(length=1, values=[LIST_PRICE, NET_PRICE])

    # price in cents, implicit decimal separator before the last two digits
    preis = IntegerField(max_length=8)

    # could be string if basismerker == OTHER
    von_basis = IntegerField(max_length=8)
    bis_basis = IntegerField(max_length=8)
