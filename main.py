"""Main application for Card Factory - Card Generator from Spreadsheet"""

import os
import sys
import glob
import requests
from dotenv import load_dotenv

from pathlib import Path

from card_factory.api.client import get_my_documents
from card_factory.api.auth import load_api_key_from_env
from card_factory.utils.file_handler import download_file
from card_factory.utils.png_preview import check_inkscape_available, generate_preview_directory
from card_factory.processors.file_filter import find_spreadsheet_file
from card_factory.processors.xlsx_extractor import extract_xlsx_data
from card_factory.binding.engine import CardBindingEngine
from card_factory.config.loader import CardFactoryConfig


def find_local_xlsx():
    """Find an existing XLSX file in the current directory.
    
    Returns:
        Path to the first .xlsx file found, or None if not found.
    """
    xlsx_files = glob.glob("*.xlsx")
    if xlsx_files:
        return xlsx_files[0]
    return None


def main():
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        print(f"=== Card Factory - Using config: {config_path} ===\n")
    else:
        print("=== Card Factory - Using default settings ===\n")
    
    try:
        config = None
        if config_path:
            config = CardFactoryConfig(config_path)
            print(f"Loaded configuration from: {config_path}\n")
        
        local_xlsx = find_local_xlsx()
        
        if local_xlsx:
            print(f"Step 1: Using local spreadsheet: {local_xlsx}\n")
            spreadsheet_file = None
            downloaded_file = local_xlsx
        else:
            api_key = load_api_key_from_env()
            print("Using API key from environment for authentication...\n")
            
            print("Step 1: Finding spreadsheet in OnlyOffice...")
            documents = get_my_documents(api_key)
            spreadsheet_file = find_spreadsheet_file(documents)
            
            if not spreadsheet_file:
                print("No spreadsheet files found")
                return
            
            print(f"Found spreadsheet: {spreadsheet_file['title']}\n")
            
            print("Step 2: Downloading spreadsheet...")
            file_id = spreadsheet_file.get('id')
            download_url = f"https://nitaku.onlyoffice.com/filehandler.ashx?action=download&fileid={file_id}"
            filename = f"downloaded_{spreadsheet_file['title']}"
            
            try:
                downloaded_file = download_file(api_key, download_url, filename)
                print(f"✓ File downloaded: {downloaded_file}\n")
            except Exception as e:
                print(f"✗ Download failed: {e}")
                return
        
        step_num = 3 if spreadsheet_file else 2
        print(f"Step {step_num}: Extracting spreadsheet data...")
        try:
            spreadsheet_data = extract_xlsx_data(downloaded_file)
            print(f"✓ Extracted {len(spreadsheet_data)} rows of data\n")
            
            if local_xlsx:
                print(f"✓ Kept local file\n")
            elif config and config.spreadsheet_cleanup:
                os.remove(downloaded_file)
                print(f"✓ Cleaned up downloaded file\n")
            else:
                print(f"✓ Kept downloaded file\n")
            
        except Exception as e:
            print(f"✗ Data extraction failed: {e}")
            return
        
        print(f"Step {step_num + 1}: Generating cards...")
        export_dir = config.output_directory if config else "export"
        engine = CardBindingEngine(config=config, export_dir=export_dir)
        generated_files = engine.generate_cards(spreadsheet_data)
        
        print(f"\n✓ Successfully generated {len(generated_files)} card(s)")
        print(f"Cards saved in: {engine.export_dir.absolute()}")
        
        if config and config.preview_enabled:
            if not check_inkscape_available():
                print("\n⚠ Warning: Inkscape not found. Skipping PNG preview generation.")
            else:
                preview_dir = Path(export_dir) / "preview"
                png_success, png_failed = generate_preview_directory(
                    generated_files,
                    preview_dir,
                    config.preview_width
                )
                if png_success:
                    print(f"\n✓ Generated {len(png_success)} PNG preview(s) in: {preview_dir.absolute()}")
                if png_failed:
                    print(f"\n⚠ Warning: Failed to generate {len(png_failed)} PNG(s)")
                    for svg_path, error in png_failed:
                        print(f"  - {svg_path}: {error}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
