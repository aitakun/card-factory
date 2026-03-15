#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/nitaku/repos/test-onlyoffice')

import docbuilder

def test_extract_xlsx_data():
    """Test the XLSX extraction function directly"""
    file_path = "Netrunner Barebone.xlsx"
    
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist")
        return
    
    try:
        # Initialize Document Builder
        builder = docbuilder.CDocBuilder()
        
        # Open the existing file using the correct method
        builder.OpenFile(file_path, docbuilder.FileTypes.Spreadsheet.XLSX)
        
        # Get context and API
        context = builder.GetContext()
        global_obj = context.GetGlobal()
        api = global_obj["Api"]
        
        # Get the active worksheet
        worksheet = api.GetActiveSheet()
        
        # Get the used range (all cells with data)
        used_range = worksheet.GetUsedRange()
        if not used_range:
            builder.CloseFile()
            print("No used range found")
            return
        
        # Get number of rows and columns
        rows = used_range.GetRowCount()
        cols = used_range.GetColumnCount()
        
        print(f"Found {rows} rows and {cols} columns")
        
        # Get all values from the used range
        values = []
        for row_idx in range(rows):
            row_values = []
            for col_idx in range(cols):
                cell = used_range.GetCell(row_idx, col_idx)
                if cell:
                    # Convert all values to text, use empty string if None
                    value = cell.GetValue()
                    row_values.append(str(value) if value is not None else "")
                else:
                    row_values.append("")
            values.append(row_values)
        
        print(f"Values extracted: {len(values)} rows")
        
        # Convert to list of dicts using first row as keys
        result = []
        if rows > 0:
            keys = values[0]
            print(f"Keys: {keys}")
            
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
            
            print(f"Valid keys: {valid_keys}")
            
            # Process data rows (skip first row which contains keys)
            for row_idx in range(1, rows):
                row_data = values[row_idx]
                # Skip entirely empty rows
                if any(cell.strip() for cell in row_data):
                    row_dict = {}
                    for col_idx, key in enumerate(valid_keys):
                        row_dict[key] = row_data[col_idx] if col_idx < len(row_data) else ""
                    result.append(row_dict)
        
        builder.CloseFile()
        
        print(f"Result: {len(result)} rows of data")
        for row in result:
            print(row)
        
        return result
        
    except Exception as e:
        print(f"Error in test_extract_xlsx_data: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    test_extract_xlsx_data()