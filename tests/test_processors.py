"""Tests for file filter functions"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from card_factory.processors.file_filter import filter_spreadsheet_files, find_spreadsheet_file


class TestFileFilter(unittest.TestCase):
    
    def setUp(self):
        self.test_files = {
            "response": {
                "files": [
                    {"title": "test.xlsx", "fileExst": ".xlsx"},
                    {"title": "document.pdf", "fileExst": ".pdf"},
                    {"title": "data.csv", "fileExst": ".csv"},
                    {"title": "presentation.ods", "fileExst": ".ods"}
                ]
            }
        }
    
    def test_filter_spreadsheet_files(self):
        result = filter_spreadsheet_files(self.test_files)
        
        self.assertEqual(len(result), 3)
        titles = [file["title"] for file in result]
        self.assertIn("test.xlsx", titles)
        self.assertIn("data.csv", titles)
        self.assertIn("presentation.ods", titles)
        self.assertNotIn("document.pdf", titles)
    
    def test_find_spreadsheet_file(self):
        result = find_spreadsheet_file(self.test_files)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "test.xlsx")
        self.assertEqual(result["fileExst"], ".xlsx")
    
    def test_find_spreadsheet_file_none(self):
        empty_files = {"response": {"files": []}}
        result = find_spreadsheet_file(empty_files)
        
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()