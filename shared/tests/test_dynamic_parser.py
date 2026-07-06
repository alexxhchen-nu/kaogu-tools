import unittest

from app.parser import auto_parse


class DynamicParserTests(unittest.TestCase):
    def test_discovers_dynamic_schema_fields_from_report(self):
        content = """
        ## M1
        M1位于东区，年代战国。墓向南北向。墓口长2.5米，宽1.2米，深3.0米。
        埋葬方式土坑竖穴墓。封土直径4米。保存状态较好。出土器物2件：陶罐1件，铜剑1件。
        """

        parser = auto_parse("test-report", content)
        self.assertGreaterEqual(len(parser.tombs), 1)

        tomb = parser.tombs[0]
        self.assertEqual(tomb.get("墓葬编号"), "M1")
        self.assertIn("schema_fields", tomb)
        self.assertEqual(tomb["schema_fields"].get("埋葬方式"), "土坑竖穴墓")
        self.assertEqual(tomb["schema_fields"].get("封土直径"), "4米")
        self.assertEqual(tomb["schema_fields"].get("保存状态"), "较好")


if __name__ == "__main__":
    unittest.main()
