try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    print("Warning: openpyxl not available. Install with: pip install openpyxl")
    openpyxl = None
    OPENPYXL_AVAILABLE = False


def extract_xlsx_data(file_path):
    """Extract first sheet data as list of dicts, using first row as keys"""
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl is required for XLSX extraction. Install with: pip install openpyxl")
    
    try:
        # Use openpyxl with read_only=True for better performance
        workbook = openpyxl.load_workbook(file_path, read_only=True)
        sheet = workbook.active
        
        # Get all data from the sheet
        values = []
        for row in sheet.iter_rows(values_only=True):
            values.append([str(cell) if cell is not None else "" for cell in row])
        
        workbook.close()
        
        # Convert to list of dicts using first row as keys
        result = []
        if len(values) > 0:
            keys = values[0]
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
            
            # Process data rows (skip first row which contains keys)
            for row_idx in range(1, len(values)):
                row_data = values[row_idx]
                # Skip entirely empty rows
                if any(cell.strip() for cell in row_data):
                    row_dict = {}
                    for col_idx, key in enumerate(valid_keys):
                        row_dict[key] = row_data[col_idx] if col_idx < len(row_data) else ""
                    result.append(row_dict)
        
        return result
        
    except Exception as e:
        print(f"Error extracting XLSX data: {e}")
        raise