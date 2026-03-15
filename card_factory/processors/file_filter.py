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