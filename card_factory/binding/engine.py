"""Data binding engine for card generation"""

from typing import Dict, List, Any
from pathlib import Path
import re

from ..templates.loader import load_template, construct_template_filename
from ..templates.renderer import render_template, save_svg


class CardBindingEngine:
    """Engine for binding spreadsheet data to SVG templates"""
    
    def __init__(self, export_dir: str = "export"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # Default bindings for hardware cards (matching the actual spreadsheet columns)
        self.default_bindings = {
            "name": "name",
            "type-line": "type",
            "cost": "cost",
            "text-body": "text",
            "copyright": "illustrator"
        }
    
    def sanitize_filename(self, text: str) -> str:
        """Create safe filename from card name"""
        if not text:
            return "card"
        
        # Remove/replace invalid filename characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '', text)
        safe_name = safe_name.strip()
        
        # Limit length
        if len(safe_name) > 50:
            safe_name = safe_name[:50]
        
        return safe_name if safe_name else "card"
    
    def filter_hardware_cards(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter to only hardware-type cards"""
        hardware_cards = []
        
        for row in data:
            card_type = row.get("type", "")
            if card_type and "hardware" in card_type.lower():
                hardware_cards.append(row)
        
        return hardware_cards
    
    def generate_card(self, row_data: Dict[str, Any]) -> str:
        """Generate a single card SVG from template and data"""
        
        card_type = row_data.get("type", "")
        
        # Load appropriate template
        template_path = construct_template_filename(card_type)
        tree = load_template(template_path)
        
        # Render template with data bindings
        tree = render_template(tree, self.default_bindings, row_data)
        
        # Generate output filename
        card_name = self.sanitize_filename(row_data.get("name", ""))
        output_path = self.export_dir / f"{card_name}.svg"
        
        # Save SVG
        save_svg(tree, str(output_path))
        
        return str(output_path)
    
    def generate_cards(self, data: List[Dict[str, Any]]) -> List[str]:
        """Generate all cards from spreadsheet data"""
        
        # Filter to hardware cards only
        hardware_cards = self.filter_hardware_cards(data)
        
        print(f"Found {len(hardware_cards)} hardware cards to generate")
        
        generated_files = []
        for i, row in enumerate(hardware_cards, 1):
            card_name = row.get("name", f"card_{i}")
            print(f"Generating card {i}/{len(hardware_cards)}: {card_name}")
            
            try:
                output_path = self.generate_card(row)
                generated_files.append(output_path)
                print(f"  ✓ Saved: {output_path}")
            except Exception as e:
                print(f"  ✗ Error generating {card_name}: {e}")
        
        return generated_files
