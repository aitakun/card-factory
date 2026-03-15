#!/usr/bin/env python3

import os
from dotenv import load_dotenv
import requests

load_dotenv()

API_BASE_URL = "https://nitaku.onlyoffice.com/api/2.0"

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

def list_spreadsheet_files():
    """List all spreadsheet files in My Documents"""
    api_key = os.getenv("ONLYOFFICE_API_KEY")
    if not api_key:
        print("Please set ONLYOFFICE_API_KEY environment variable")
        return
    
    try:
        my_docs = get_my_documents(api_key)
        
        if 'response' in my_docs and 'files' in my_docs['response']:
            files = my_docs['response']['files']
            spreadsheet_files = []
            
            for file in files:
                ext = file.get('fileExst', '').lower()
                if ext in ['.xlsx', '.xls', '.ods', '.csv']:
                    spreadsheet_files.append({
                        'title': file.get('title'),
                        'id': file.get('id'),
                        'contentLength': file.get('contentLength'),
                        'viewUrl': file.get('viewUrl')
                    })
            
            print(f"Found {len(spreadsheet_files)} spreadsheet files:")
            print("=" * 60)
            for i, file in enumerate(spreadsheet_files, 1):
                print(f"{i}. {file['title']}")
                print(f"   ID: {file['id']}")
                print(f"   Size: {file['contentLength']}")
                print(f"   URL: {file['viewUrl']}")
                print()
            
            return spreadsheet_files
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_spreadsheet_files()