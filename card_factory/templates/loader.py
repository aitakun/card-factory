"""SVG Template loading utilities"""

from pathlib import Path
from typing import Optional
from lxml import etree

TEMPLATE_DIR = Path(__file__).parent.parent.parent / "template"


def extract_type_from_typeline(typeline: str) -> str:
    """Extract card type from type line (part before '-', lowercased, trimmed)"""
    if not typeline:
        return "unknown"
    
    type_part = typeline.split("-")[0].strip().lower()
    return type_part if type_part else "unknown"


def construct_template_filename(typeline: str, default: str = "hardware.svg") -> str:
    """Construct template filename from type line"""
    card_type = extract_type_from_typeline(typeline)
    template_path = TEMPLATE_DIR / f"{card_type}.svg"
    
    if template_path.exists():
        return str(template_path)
    
    # Fallback to default template
    default_path = TEMPLATE_DIR / default
    if default_path.exists():
        return str(default_path)
    
    raise FileNotFoundError(f"No template found for type: {card_type}")


def load_template(template_path: str) -> etree.ElementTree:
    """Load SVG template and return lxml tree"""
    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(path), parser)
    return tree


def find_element_by_id(tree: etree.ElementTree, element_id: str) -> Optional[etree.Element]:
    """Find SVG element by its ID attribute"""
    return tree.find(f".//*[@id='{element_id}']")
