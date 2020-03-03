import unittest
from datetime import date
from decimal import Decimal
from unittest import TestCase

from datanorm_writer.base import (
    DateField,
    IntegerField,
    RowBase,
    ShortDateField,
    StaticField,
    StringField,
    charset_translations,
    chunk_text,
)
from datanorm_writer.rows import Artikelzeile, Artikelzeile2, VorlaufZeile


class IntegerFieldTest(TestCase):
    def test_padding(self):
        f = IntegerField(length=3)
        self.assertEqual(f.process(10), "010")

    def test_values(self):
        f = IntegerField(values=(0, 1, 2))
        with self.assertRaises(ValueError):
            f.process(4)


class RowTest(TestCase):
    def test_translation(self):
        class TestRow(RowBase):
            a = StringField(max_length=30)
            b = StringField(max_length=30)

        self.assertEqual(charset_translations["ü"], TestRow(a="ü", b="ß").output[:1])
        self.assertEqual(b"\x81;\xe1;", TestRow(a="ü", b="ß").output)

    def test_charset(self):
        class TestRow(RowBase):
            charset = {"a": b"b"}
            f = StringField(max_length=30)

        self.assertEqual(TestRow(f="a").output, b"b;")

    def test_separator(self):
        class TestRow(RowBase):
            separator = b"_"
            a = StringField(max_length=30)
            b = StringField(max_length=30)

        self.assertEqual(TestRow(a="a", b="b").output, b"a_b_")


class StringFieldTest(TestCase):
    def test_length_validation(self):
        f = StringField(length=5)
        with self.assertRaises(ValueError):
            f.process("abc")

    def test_max_length_validation(self):
        f = StringField(max_length=5)
        with self.assertRaises(ValueError):
            f.process("abcdef")


class StaticFieldTest(TestCase):
    def test_static_field(self):
        f = StaticField("a")
        self.assertEqual("a", f.process())

    def test_static_field_invalid(self):
        f = StaticField("abc")
        with self.assertRaises(ValueError):
            f.process("d")


class DateFieldTest(TestCase):
    def test_date(self):
        f = DateField()
        self.assertEqual(f.process(date(2014, 10, 11)), "20141011")


class ShortDateFieldTest(TestCase):
    def test_date(self):
        f = ShortDateField()
        self.assertEqual(f.process(date(2014, 10, 11)), "111014")


class ChunkTest(TestCase):
    def test_text_chunk_words(self):
        chunks = chunk_text("ABC DEF GHI JKL MNO QRS", 5)
        self.assertEqual(6, len(chunks))
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 5)

    def test_text_chunk_long_words(self):
        chunks = chunk_text("ABCDEFGHI JKLMNOQRS", 5)
        self.assertEqual(4, len(chunks))
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 5)


class CharsetTest(TestCase):
    def test_output_charset_translation(self):
        output = Artikelzeile(
            kurztext_1="üÜöÖäÄß",
            textkennzeichen="00",
            verarbeitungsmerker="0",
            preiskennzeichen=Artikelzeile.PREIS_LISTENPREIS,
            preiseinheit=Artikelzeile.PRICE_BY_1_UNIT,
        ).output

        self.assertIn(b"\x81\x9a\x94\x99\x84\x8e\xe1", output)

    def test_invalid_values_are_logged_and_removed(self):
        with self.assertLogs(level="ERROR"):
            output = Artikelzeile(
                kurztext_1="XXX°YYY",
                textkennzeichen="00",
                verarbeitungsmerker="0",
                preiskennzeichen=Artikelzeile.PREIS_LISTENPREIS,
                preiseinheit=Artikelzeile.PRICE_BY_1_UNIT,
            ).output
            self.assertIn(b"XXXYYY", output)


def example_export():
    lines = [
        VorlaufZeile(
            datenkennzeichen="A",
            waehrungskennzeichen="EUR",
            erstellungsdatum=date.today(),
            informationstext1=" " * 40,
            informationstext2=" " * 40,
            informationstext3=" " * 35,
        )
    ]

    products = [
        {
            "gtin": "0123456789012",
            "item_number": "12345",
            "name": "one product",
            "price_unit": "PCE",
            "price": Decimal("19.99"),
        },
        {
            "gtin": "0123456789013",
            "item_number": "12346",
            "name": "other product",
            "price_unit": "PCE",
            "price": Decimal("29.99"),
        },
    ]

    for product in products:
        lines.append(
            Artikelzeile(
                verarbeitungsmerker="N",
                artikelnummer=product["item_number"],
                textkennzeichen=Artikelzeile.TEXT_LANG_KURZ2
                + Artikelzeile.TEXT_HAS_KURZ2_TRUE,
                kurztext_1=product["name"][:40],
                kurztext_2=" ",
                preiskennzeichen=Artikelzeile.PREIS_LISTENPREIS,
                preiseinheit=Artikelzeile.PRICE_BY_1_UNIT,
                mengeneinheit=product["price_unit"][:4],
                preis=int((100 * product["price"])),
                rabattgruppe=" ",
                hauptwarengruppe=" ",
                warengruppe=" ",
                langtextnummer=" ",
            )
        )

        lines.append(
            Artikelzeile2(
                verarbeitungsmerker="N",
                artikelnummer=product["item_number"],
                matchcode=" ",
                alternativ_artikelnummer=" ",
                katalogseite=" ",
                ean=product["gtin"],
                anbindungsnummer=" ",
                warengruppe=" ",
                verpackungsmenge=1,
                referenznummer_erstellerkuerzel=" ",
                referenznummer=" ",
            )
        )

    return b"\r\n".join(l.output for l in lines) + b"\r\n"


class ExampleExportTest(TestCase):
    def test_example_output(self):
        output = example_export()
        header, content = output.split(b"\r\n", 1)
        self.assertEqual(len(header), 128)
        self.assertEqual(
            content,
            b"A;N;12345;10;one product; ;1;0;PCE;1999; ; ; ;\r\n"
            b"B;N;12345; ; ; ;0;0;0;0123456789012; ; ;0;1; ; ;\r\n"
            b"A;N;12346;10;other product; ;1;0;PCE;2999; ; ; ;\r\n"
            b"B;N;12346; ; ; ;0;0;0;0123456789013; ; ;0;1; ; ;\r\n",
        )


if __name__ == "__main__":
    unittest.main()
