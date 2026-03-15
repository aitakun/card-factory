#!/usr/bin/env python3

import os
import sys
sys.path.append('/home/nitaku/repos/test-onlyoffice')
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

def examine_api_response():
    """Examine the API response structure to find proper download URLs"""
    api_key = os.getenv("ONLYOFFICE_API_KEY")
    if not api_key:
        print("Please set ONLYOFFICE_API_KEY environment variable")
        return
    
    try:
        my_docs = get_my_documents(api_key)
        
        print("API Response Structure:")
        print("=" * 50)
        
        if 'response' in my_docs and 'files' in my_docs['response']:
            files = my_docs['response']['files']
            print(f"Found {len(files)} files")
            
            for i, file in enumerate(files):
                print(f"\nFile {i+1}:")
                print(f"  ID: {file.get('id')}")
                print(f"  Title: {file.get('title')}")
                print(f"  Extension: {file.get('fileExst')}")
                print(f"  Path: {file.get('path')}")
                print(f"  Content Length: {file.get('contentLength')}")
                
                # Check for download-related fields
                print(f"  All keys: {list(file.keys())}")
                
                # Look for any URL-like fields
                for key, value in file.items():
                    if 'url' in key.lower() or 'download' in key.lower():
                        print(f"  Potential download field - {key}: {value}")
                
                if i >= 2:  # Limit to first 3 files
                    break
        
        print("\n" + "=" * 50)
        print("Full response structure:")
        print(json.dumps(my_docs, indent=2)[:1000] + "..." if len(str(my_docs)) > 1000 else json.dumps(my_docs, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import json
    examine_api_response()