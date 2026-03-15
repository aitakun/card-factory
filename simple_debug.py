#!/home/nitaku/repos/test-onlyoffice/.venv/bin/python

import docbuilder

def test_extraction():
    try:
        print("Starting extraction test...")
        
        # Initialize Document Builder
        builder = docbuilder.CDocBuilder()
        print("✓ Builder created")
        
        # Open the existing file
        builder.OpenFile("Netrunner Barebone.xlsx", docbuilder.FileTypes.Spreadsheet.XLSX)
        print("✓ File opened")
        
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
        rows = int(used_range.GetRowCount())
        cols = int(used_range.GetColumnCount())
        print(f"✓ Found {rows} rows and {cols} columns")
        
        # Get first row as headers
        if rows > 0:
            headers = []
            for col_idx in range(cols):
                cell = used_range.GetCell(0, col_idx)
                if cell:
                    value = cell.GetValue()
                    headers.append(str(value) if value is not None else "")
                else:
                    headers.append("")
            print(f"✓ Headers: {headers}")
        
        # Get first data row
        if rows > 1:
            data_row = []
            for col_idx in range(cols):
                cell = used_range.GetCell(1, col_idx)
                if cell:
                    value = cell.GetValue()
                    data_row.append(str(value) if value is not None else "")
                else:
                    data_row.append("")
            print(f"✓ Data row: {data_row}")
        
        builder.CloseFile()
        print("✓ File closed")
        
        print("✓ Test completed successfully!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_extraction()