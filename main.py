"""Main application for Card Factory - Hardware Card Generator"""

import os
import requests
from dotenv import load_dotenv

from card_factory.api.client import get_my_documents
from card_factory.api.auth import load_api_key_from_env
from card_factory.utils.file_handler import download_file
from card_factory.processors.file_filter import find_spreadsheet_file
from card_factory.processors.xlsx_extractor import extract_xlsx_data
from card_factory.binding.engine import CardBindingEngine


def main():
    print("=== Card Factory - Hardware Card Generator ===\n")
    
    try:
        api_key = load_api_key_from_env()
        print("Using API key from environment for authentication...\n")
        
        # Get user's documents and find spreadsheet
        print("Step 1: Finding spreadsheet in OnlyOffice...")
        documents = get_my_documents(api_key)
        spreadsheet_file = find_spreadsheet_file(documents)
        
        if not spreadsheet_file:
            print("No spreadsheet files found")
            return
        
        print(f"Found spreadsheet: {spreadsheet_file['title']}\n")
        
        # Download the file
        print("Step 2: Downloading spreadsheet...")
        file_id = spreadsheet_file.get('id')
        download_url = f"https://nitaku.onlyoffice.com/filehandler.ashx?action=download&fileid={file_id}"
        filename = f"downloaded_{spreadsheet_file['title']}"
        
        try:
            downloaded_file = download_file(api_key, download_url, filename)
            print(f"✓ File downloaded: {downloaded_file}\n")
        except Exception as e:
            print(f"✗ Download failed: {e}")
            return
        
        # Extract spreadsheet data
        print("Step 3: Extracting spreadsheet data...")
        try:
            spreadsheet_data = extract_xlsx_data(downloaded_file)
            print(f"✓ Extracted {len(spreadsheet_data)} rows of data\n")
            
            # Clean up downloaded file
            os.remove(downloaded_file)
            print(f"✓ Cleaned up downloaded file\n")
            
        except Exception as e:
            print(f"✗ Data extraction failed: {e}")
            return
        
        # Generate hardware cards
        print("Step 4: Generating hardware cards...")
        engine = CardBindingEngine(export_dir="export")
        generated_files = engine.generate_cards(spreadsheet_data)
        
        print(f"\n✓ Successfully generated {len(generated_files)} card(s)")
        print(f"Cards saved in: {engine.export_dir.absolute()}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
