"""Tests for API client functions"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from card_factory.api.client import get_current_user, get_folder_contents, get_my_documents


class TestAPIClient(unittest.TestCase):
    
    def setUp(self):
        self.api_key = "test_api_key"
    
    @patch('card_factory.api.client.requests.get')
    def test_get_current_user(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"id": 1, "name": "Test User"}
        mock_get.return_value = mock_response
        
        result = get_current_user(self.api_key)
        
        self.assertEqual(result, {"id": 1, "name": "Test User"})
        mock_get.assert_called_once()
    
    @patch('card_factory.api.client.requests.get')
    def test_get_folder_contents(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"files": []}
        mock_get.return_value = mock_response
        
        result = get_folder_contents(self.api_key, "test_folder_id")
        
        self.assertEqual(result, {"files": []})
        mock_get.assert_called_once()
    
    @patch('card_factory.api.client.requests.get')
    def test_get_my_documents(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"files": []}
        mock_get.return_value = mock_response
        
        result = get_my_documents(self.api_key)
        
        self.assertEqual(result, {"files": []})
        mock_get.assert_called_once()


if __name__ == '__main__':
    unittest.main()