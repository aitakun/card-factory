"""Tests for utility functions"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from card_factory.utils.file_handler import get_file_url


class TestUtils(unittest.TestCase):
    
    def setUp(self):
        self.api_key = "test_api_key"
        self.file_id = "12345"
        self.file_path = "/test/path"
    
    def test_get_file_url(self):
        result = get_file_url(self.api_key, self.file_id, self.file_path)
        
        expected = "https://nitaku.onlyoffice.com/download?file=12345"
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()