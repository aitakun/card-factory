# OnlyOffice Spreadsheet Reader

A script for downloading and extracting data from XLSX files stored in OnlyOffice DocSpace.

## Features

- ✅ **Authentication**: API key-based authentication with OnlyOffice
- ✅ **File Download**: Downloads XLSX files from OnlyOffice
- ✅ **Data Extraction**: Extracts spreadsheet data as list of dictionaries

## Requirements

- Python 3.7+
- Required packages: see `requirements.txt`

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


## Data Format

The extracted data is returned as a list of dictionaries, where:
- Each dictionary represents a row from the spreadsheet
- Keys are column headers from the first row
- Values are the cell contents converted to strings
- Empty cells are represented as empty strings
