"""SVG Template rendering and value substitution"""

from typing import Dict, Any, Optional
from lxml import etree
from pathlib import Path


def get_element_text_content(element: etree.Element) -> str:
    """Extract text content from SVG element (recursive)"""
    text_parts = []
    
    if element.text:
        text_parts.append(element.text)
    
    for child in element:
        text_parts.append(get_element_text_content(child))
        if child.tail:
            text_parts.append(child.tail)
    
    return "".join(text_parts)


def set_element_text_content(element: etree.Element, new_text: str) -> None:
    """Set text content of SVG element, preserving structure"""
    for child in list(element):
        element.remove(child)
    
    element.text = new_text


def substitute_text_in_tspan(element: etree.Element, new_text: str) -> None:
    """Substitute text in tspan elements (common in Inkscape SVGs)"""
    for tspan in element.findall(".//{http://www.w3.org/2000/svg}tspan"):
        # Clear all nested tspans and set text
        for child in list(tspan):
            tspan.remove(child)
        tspan.text = new_text
        return  # Only modify the first tspan


def render_template(tree: etree.ElementTree, bindings: Dict[str, str], row_data: Dict[str, Any]) -> etree.ElementTree:
    """Substitute values from row_data into template elements based on bindings"""
    
    for element_id, source_column in bindings.items():
        # Get value from spreadsheet and strip whitespace
        value = str(row_data.get(source_column, "")).strip()
        
        # Find element in template
        element = tree.find(f".//*[@id='{element_id}']")
        
        if element is None:
            print(f"Warning: Element '{element_id}' not found in template")
            continue
        
        # Handle text elements
        tag = element.tag.split("}")[-1]  # Get local name without namespace
        
        if tag == "text":
            # For Inkscape text elements, modify the first tspan
            tspan = element.find(".//{http://www.w3.org/2000/svg}tspan")
            if tspan is not None:
                # Clear all nested tspans inside this tspan before setting text
                for child in list(tspan):
                    tspan.remove(child)
                tspan.text = value
            else:
                element.text = value
        elif tag == "tspan":
            # Clear all nested tspans before setting text
            for child in list(element):
                element.remove(child)
            element.text = value
        else:
            # For other elements, just set text content
            set_element_text_content(element, value)
    
    return tree


def save_svg(tree: etree.ElementTree, output_path: str) -> None:
    """Save SVG tree to file"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    tree.write(
        str(path),
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True
    )
