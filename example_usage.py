#!/usr/bin/env python3
"""
Example usage of the card_factory package.

This script demonstrates how to use the OnlyOffice Spreadsheet Reader
package as a library instead of running the main application.
"""

import sys
import os
from dotenv import load_dotenv

# Import the package functions
from card_factory.api.client import get_my_documents
from card_factory.api.auth import load_api_key_from_env
from card_factory.utils.file_handler import download_file
from card_factory.processors.file_filter import filter_spreadsheet_files, find_spreadsheet_file
from card_factory.processors.xlsx_extractor import extract_xlsx_data


def example_usage():
    """Example of using the card_factory package as a library"""
    print("=== Card Factory Package Example ===\n")
    
    try:
        # Load API key
        api_key = load_api_key_from_env()
        print("✓ API key loaded successfully\n")
        
        # Get user's documents
        print("Getting your documents...")
        documents = get_my_documents(api_key)
        print(f"✓ Found {len(documents.get('response', {}).get('files', []))} files\n")
        
        # Find spreadsheet files
        print("Looking for spreadsheet files...")
        spreadsheet_file = find_spreadsheet_file(documents)
        
        if spreadsheet_file:
            print(f"✓ Found spreadsheet: {spreadsheet_file['title']}")
            print(f"  File ID: {spreadsheet_file.get('fileId', 'N/A')}")
            print(f"  Extension: {spreadsheet_file.get('fileExst', 'N/A')}\n")
            
            # Construct download URL
            file_id = spreadsheet_file.get('fileId')
            if file_id:
                download_url = f"https://nitaku.onlyoffice.com/filehandler.ashx?action=download&fileid={file_id}"
                print(f"Download URL: {download_url}\n")
                
                # Download the file
                filename = f"downloaded_{spreadsheet_file['title']}"
                print(f"Downloading {filename}...")
                downloaded_file = download_file(api_key, download_url, filename)
                print(f"✓ File downloaded successfully: {downloaded_file}\n")
                
                # Extract data
                print("Extracting spreadsheet data...")
                try:
                    data = extract_xlsx_data(downloaded_file)
                    print(f"✓ Extracted {len(data)} rows of data")
                    if data:
                        print("\nFirst row sample:")
                        print(data[0])
                except Exception as e:
                    print(f"✗ Data extraction failed: {e}")
                
                # Clean up
                try:
                    os.remove(downloaded_file)
                    print(f"✓ Cleaned up downloaded file")
                except Exception as e:
                    print(f"Warning: Could not remove downloaded file: {e}")
        else:
            print("✗ No spreadsheet files found in your documents")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    example_usage()