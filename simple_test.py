#!/usr/bin/env python3

import docbuilder

def simple_test():
    """Simple test of Document Builder functionality"""
    try:
        # Initialize Document Builder
        builder = docbuilder.CDocBuilder()
        print("✓ Builder created successfully")
        
        # Create a new spreadsheet file
        builder.CreateFile(docbuilder.FileTypes.Spreadsheet.XLSX)
        print("✓ File created successfully")
        
        # Get context and API
        context = builder.GetContext()
        global_obj = context.GetGlobal()
        api = global_obj["Api"]
        print("✓ Context and API obtained")
        
        # Get the active worksheet
        worksheet = api.GetActiveSheet()
        print("✓ Worksheet obtained")
        
        # Get the used range
        used_range = worksheet.GetUsedRange()
        print("✓ Used range obtained")
        
        # Get number of rows and columns
        rows = used_range.GetRowCount()
        cols = used_range.GetColumnCount()
        print(f"✓ Found {rows} rows and {cols} columns")
        
        builder.CloseFile()
        print("✓ File closed successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    simple_test()