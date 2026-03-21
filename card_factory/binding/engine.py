"""Data binding engine for card generation"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import re

from ..templates.loader import load_template, construct_template_filename
from ..templates.renderer import render_template, save_svg


class CardBindingEngine:
    """Engine for binding spreadsheet data to SVG templates"""
    
    def __init__(self, config=None, export_dir: str = "export"):
        self.config = config
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # Default bindings if no config provided
        self.default_bindings = [
            {"element_id": "name", "value": "name"},
            {"element_id": "type", "value": "[uppercase]{type}[/uppercase]"},
            {"element_id": "subtypes", "value": "{subtypes}", "prefix": " - "},
            {"element_id": "cost", "value": "cost"},
            {"element_id": "text-body", "value": "{text}\n\n**{flavor}**"},
            {"element_id": "copyright", "value": "illustrator"}
        ]
    
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
    
    def get_bindings(self) -> List[Dict[str, Any]]:
        """Get bindings from config or use defaults"""
        if self.config and hasattr(self.config, 'get_bindings'):
            bindings = self.config.get_bindings()
            if bindings:
                return bindings
        return self.default_bindings
    
    def filter_cards(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter cards based on config filter settings"""
        if self.config and hasattr(self.config, 'should_include_row'):
            return [row for row in data if self.config.should_include_row(row)]
        
        # Default: filter hardware cards
        filtered = []
        for row in data:
            card_type = row.get("type", "")
            if card_type and "hardware" in card_type.lower():
                filtered.append(row)
        return filtered
    
    def get_template_path(self, row_data: Dict[str, Any]) -> str:
        """Get template path based on config or card type"""
        if self.config and hasattr(self.config, 'template_pattern') and self.config.template_pattern:
            # Replace placeholders in pattern with values from row
            template_path = self.config.template_pattern
            for key, value in row_data.items():
                placeholder = f"{{{key}}}"
                if placeholder in template_path:
                    # Convert to lowercase and replace spaces/dashes with underscores
                    safe_value = str(value).lower().replace(" ", "_").replace("-", "_")
                    template_path = template_path.replace(placeholder, safe_value)
            
            # Check if file exists
            if Path(template_path).exists():
                return template_path
        
        # Fallback to type-based template selection
        card_type = row_data.get("type", "")
        return construct_template_filename(card_type)
    
    def generate_output_filename(self, row_data: Dict[str, Any]) -> str:
        """Generate output filename based on config pattern"""
        if self.config and hasattr(self.config, 'filename_pattern'):
            filename = self.config.filename_pattern
            for key, value in row_data.items():
                placeholder = f"{{{key}}}"
                if placeholder in filename:
                    safe_value = self.sanitize_filename(str(value))
                    filename = filename.replace(placeholder, safe_value)
            return filename
        else:
            return f"{self.sanitize_filename(row_data.get('name', 'card'))}.svg"
    
    def generate_card(self, row_data: Dict[str, Any]) -> str:
        """Generate a single card SVG from template and data"""
        
        # Load appropriate template
        template_path = self.get_template_path(row_data)
        tree = load_template(template_path)
        
        # Render template with data bindings
        bindings = self.get_bindings()
        tree = render_template(tree, bindings, row_data)
        
        # Generate output filename
        filename = self.generate_output_filename(row_data)
        output_path = self.export_dir / filename
        
        # Save SVG
        save_svg(tree, str(output_path))
        
        return str(output_path)
    
    def generate_cards(self, data: List[Dict[str, Any]]) -> List[str]:
        """Generate all cards from spreadsheet data"""
        
        # Filter cards
        filtered_cards = self.filter_cards(data)
        
        print(f"Found {len(filtered_cards)} cards to generate")
        
        generated_files = []
        for i, row in enumerate(filtered_cards, 1):
            card_name = row.get("name", f"card_{i}")
            print(f"Generating card {i}/{len(filtered_cards)}: {card_name}")
            
            try:
                output_path = self.generate_card(row)
                generated_files.append(output_path)
                print(f"  ✓ Saved: {output_path}")
            except Exception as e:
                print(f"  ✗ Error generating {card_name}: {e}")
        
        return generated_files
