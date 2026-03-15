import requests

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