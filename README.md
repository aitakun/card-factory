# OnlyOffice Spreadsheet Reader

A clean, robust script for downloading and extracting data from XLSX files stored in OnlyOffice DocSpace.

## Features

- ✅ **Authentication**: API key-based authentication with OnlyOffice
- ✅ **File Discovery**: Automatically finds spreadsheet files in "My Documents"
- ✅ **File Download**: Downloads XLSX files from OnlyOffice
- ✅ **Data Extraction**: Extracts spreadsheet data as list of dictionaries
- ✅ **No Segfaults**: Uses openpyxl for stable, crash-free extraction
- ✅ **Clean Code**: Simple, maintainable implementation

## Requirements

- Python 3.7+
- Required packages (see `requirements.txt`):
  - `requests==2.31.0`
  - `python-dotenv==1.0.0`
  - `openpyxl==3.1.2`

## Setup

1. Install dependencies:
   ```bash
   .venv/bin/pip install -r requirements.txt
   ```

2. Set up API key in `.env` file:
   ```
   ONLYOFFICE_API_KEY=your_api_key_here
   ```

## Usage

Run the script:
```bash
.venv/bin/python main.py
```

The script will:
1. Authenticate with OnlyOffice using your API key
2. List spreadsheet files in your "My Documents" folder
3. Download the first spreadsheet file found
4. Extract data from the XLSX file
5. Display the extracted data as list of dictionaries

## Example Output

```
=== OnlyOffice Spreadsheet Reader ===

Step 1: Getting 'My Documents' folder contents...
✓ Successfully retrieved folder contents

Step 2: Finding spreadsheet files...
Found spreadsheet file: Netrunner Barebone.xlsx

Step 3: Getting file URL...
File URL: https://nitaku.onlyoffice.com/download?file=3510351

Step 4: Downloading file...
✓ File downloaded successfully: Netrunner Barebone.xlsx

Step 5: Extracting spreadsheet data...
✓ Data extracted successfully (4 rows):
{'name': 'bla', 'text': '', 'cost': '3'}
{'name': 'ble', 'text': '', 'cost': '1'}
{'name': 'bli', 'text': '', 'cost': '0'}
{'name': 'blo blu', 'text': '', 'cost': '3'}
```

## Data Format

The extracted data is returned as a list of dictionaries, where:
- Each dictionary represents a row from the spreadsheet
- Keys are column headers from the first row
- Values are the cell contents converted to strings
- Empty cells are represented as empty strings

## Key Improvements

- **No more segfaults**: Replaced problematic Document Builder with stable openpyxl
- **Simplified code**: Removed complex fallback logic and error handling
- **Better performance**: openpyxl is faster and more memory-efficient
- **Cleaner dependencies**: Only essential packages required

## File Structure

```
├── main.py              # Main script
├── requirements.txt     # Python dependencies
├── .env               # Environment variables (API key)
└── .venv/            # Virtual environment
```

## Troubleshooting

If you encounter issues:

1. **API Key Issues**: Ensure your `.env` file contains a valid API key
2. **openpyxl Missing**: Install with `pip install openpyxl`
3. **Network Issues**: Check your internet connection and OnlyOffice server status
4. **File Permissions**: Ensure the script has write permissions for downloaded files