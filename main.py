"""Main application for OnlyOffice Spreadsheet Reader"""

import os
import requests
from dotenv import load_dotenv

# Import from the new package structure
from card_factory.api.client import get_current_user, get_folder_contents, get_my_documents
from card_factory.api.auth import load_api_key_from_env
from card_factory.processors.xlsx_extractor import extract_xlsx_data
from card_factory.utils.file_handler import get_file_url, download_file

def main():
    print("=== OnlyOffice Spreadsheet Reader ===\n")
    
    try:
        # Get API key using the new auth module
        api_key = load_api_key_from_env()
        print("Using API key from environment for authentication...\n")
        
        # Hardcoded file ID
        TARGET_FILE_ID = 3510351
        print(f"Using hardcoded file ID: {TARGET_FILE_ID}")
        
        # Step 1: Get file URL using hardcoded ID (same format as working version)
        print("\nStep 1: Getting file URL...")
        file_url = f"https://nitaku.onlyoffice.com/filehandler.ashx?action=download&fileid={TARGET_FILE_ID}"
        print(f"File URL: {file_url}\n")
        
        # Step 2: Download the file
        print("Step 2: Downloading file...")
        # Use the filename that was working before
        filename = "Netrunner Barebone.xlsx"
        try:
            downloaded_file = download_file(api_key, file_url, filename)
            print(f"✓ File downloaded successfully: {downloaded_file}")
        except Exception as e:
            print(f"✗ Download failed: {e}")
            return
        
        # Step 3: Extract spreadsheet data
        print("\nStep 3: Extracting spreadsheet data...")
        try:
            spreadsheet_data = extract_xlsx_data(downloaded_file)
            print(f"✓ Data extracted successfully ({len(spreadsheet_data)} rows):")
            for row in spreadsheet_data:
                print(row)
            
            # Clean up: Remove the downloaded file
            try:
                os.remove(downloaded_file)
                print(f"✓ Cleaned up downloaded file: {downloaded_file}")
            except Exception as cleanup_error:
                print(f"Warning: Could not remove downloaded file: {cleanup_error}")
                
        except Exception as e:
            print(f"✗ Data extraction failed: {e}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
    except KeyError as e:
        print(f"Missing expected key in response: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()