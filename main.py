import requests
import json
import os
import csv
import io
from dotenv import load_dotenv

# Import openpyxl for XLSX processing
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    print("Warning: openpyxl not available. Install with: pip install openpyxl")
    openpyxl = None
    OPENPYXL_AVAILABLE = False

API_BASE_URL = "https://nitaku.onlyoffice.com/api/2.0"
CONVERSION_BASE_URL = "https://nitaku.onlyoffice.com/converter"

def get_current_user(api_key):
    """Get current user profile using API key authentication"""
    url = f"{API_BASE_URL}/people/@self"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    print(f"Making request to: {url}")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    result = response.json()
    return result

def get_folder_contents(api_key, folder_id):
    """Get contents of a folder or room in OnlyOffice DocSpace"""
    url = f"{API_BASE_URL}/files/{folder_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    
    print(f"Getting contents for folder ID: {folder_id}")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    result = response.json()
    return result

def get_my_documents(api_key):
    """Get contents of 'My Documents' folder"""
    url = f"{API_BASE_URL}/files/@my"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    
    print("Getting contents of 'My Documents'")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    result = response.json()
    return result

def filter_spreadsheet_files(files):
    """Filter files to get only spreadsheet files (xlsx, xls, ods, csv)"""
    spreadsheet_extensions = ['.xlsx', '.xls', '.ods', '.csv']
    spreadsheet_files = []
    
    if 'response' in files and 'files' in files['response']:
        for file in files['response']['files']:
            title = file.get('title', '')
            ext = file.get('fileExst', '')
            
            if ext.lower() in spreadsheet_extensions:
                spreadsheet_files.append(file)
    
    return spreadsheet_files

def find_spreadsheet_file(files):
    """Find the first spreadsheet file in a list of files"""
    spreadsheet_extensions = ['.xlsx', '.xls', '.ods', '.csv']
    
    if 'response' in files and 'files' in files['response']:
        for file in files['response']['files']:
            title = file.get('title', '')
            ext = file.get('fileExst', '')
            
            if ext.lower() in spreadsheet_extensions:
                print(f"Found spreadsheet file: {title}")
                return file
    
    print("No spreadsheet files found")
    return None

def get_file_url(api_key, file_id, file_path):
    """Construct the full URL to download a file"""
    # The API response may provide a download URL directly
    # Construct the URL based on the file info
    return f"https://nitaku.onlyoffice.com/download?file={file_id}"

def download_file(api_key, file_url, filename):
    """Download file from OnlyOffice URL with basic error handling"""
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(file_url, headers=headers)
    response.raise_for_status()
    with open(filename, 'wb') as f:
        f.write(response.content)
    return filename

def extract_xlsx_data(file_path):
    """Extract first sheet data as list of dicts, using first row as keys"""
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl is required for XLSX extraction. Install with: pip install openpyxl")
    
    try:
        # Use openpyxl with read_only=True for better performance
        workbook = openpyxl.load_workbook(file_path, read_only=True)
        sheet = workbook.active
        
        # Get all data from the sheet
        values = []
        for row in sheet.iter_rows(values_only=True):
            values.append([str(cell) if cell is not None else "" for cell in row])
        
        workbook.close()
        
        # Convert to list of dicts using first row as keys
        result = []
        if len(values) > 0:
            keys = values[0]
            # Remove empty keys and handle duplicate keys
            valid_keys = []
            key_counts = {}
            for key in keys:
                if key.strip():  # Only non-empty keys
                    if key in key_counts:
                        key_counts[key] += 1
                        valid_keys.append(f"{key}_{key_counts[key]}")
                    else:
                        key_counts[key] = 1
                        valid_keys.append(key)
                else:
                    valid_keys.append(f"Column_{len(valid_keys) + 1}")
            
            # Process data rows (skip first row which contains keys)
            for row_idx in range(1, len(values)):
                row_data = values[row_idx]
                # Skip entirely empty rows
                if any(cell.strip() for cell in row_data):
                    row_dict = {}
                    for col_idx, key in enumerate(valid_keys):
                        row_dict[key] = row_data[col_idx] if col_idx < len(row_data) else ""
                    result.append(row_dict)
        
        return result
        
    except Exception as e:
        print(f"Error extracting XLSX data: {e}")
        raise

def main():
    print("=== OnlyOffice Spreadsheet Reader ===\n")
    
    try:
        # Get API key from .env file only
        load_dotenv()  # Load environment variables from .env file
        api_key = os.getenv("ONLYOFFICE_API_KEY")
        if not api_key:
            raise ValueError("API key not found. Please set ONLYOFFICE_API_KEY in your .env file")
        
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