def get_file_url(api_key, file_id, file_path):
    """Construct the full URL to download a file"""
    # The API response may provide a download URL directly
    # Construct the URL based on the file info
    return f"https://nitaku.onlyoffice.com/download?file={file_id}"


def download_file(api_key, file_url, filename):
    """Download file from OnlyOffice URL with basic error handling"""
    import requests
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(file_url, headers=headers)
    response.raise_for_status()
    with open(filename, 'wb') as f:
        f.write(response.content)
    return filename