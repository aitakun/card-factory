"""SVG Template rendering and value substitution"""

import re
from typing import Dict, Any, Optional, List
from lxml import etree
from pathlib import Path


def resolve_template_value(template: str, row_data: Dict[str, Any], element_id: str) -> str:
    """
    Resolve a template string by replacing {field} placeholders with values from row_data.
    
    Supports transform tags: [uppercase]{field}[/uppercase], [lowercase]{field}[/lowercase]
    
    If the template is just a simple field name (no special syntax), resolves it directly.
    
    If a field resolves to empty, surrounding text is also removed (e.g., ** becomes empty).
    
    Returns the resolved string with all placeholders replaced.
    Warns on missing columns.
    """
    # Check if template is just a simple field name (no { } or [ ] brackets)
    if not re.search(r'[\{\}\[\]]', template):
        # Simple field name - resolve directly
        field_name = template
        if field_name in row_data:
            return str(row_data.get(field_name, ""))
        else:
            print(f"Warning: Column '{field_name}' not found for element '{element_id}'")
            return ""
    
    result = template
    
    # Pattern to match transform tags with field: [uppercase]{field}[/uppercase]
    transform_pattern = r'\[(uppercase|lowercase)\]\{([^}]+)\}\[/\1\]'
    
    def replace_transform(match):
        transform_type = match.group(1)
        field_name = match.group(2)
        full_match = match.group(0)  # e.g., [uppercase]{field}[/uppercase]
        
        if field_name not in row_data:
            print(f"Warning: Column '{field_name}' not found for element '{element_id}'")
            return ""
        
        value = str(row_data.get(field_name, ""))
        
        if not value:
            # Field is empty, remove the entire tag including surrounding text
            return ""
        
        if transform_type == "uppercase":
            return value.upper()
        elif transform_type == "lowercase":
            return value.lower()
        return value
    
    # Replace transform tags first
    result = re.sub(transform_pattern, replace_transform, result)
    
    # Pattern to match simple field placeholders: {field_name}
    field_pattern = r'\{([^}]+)\}'
    
    def replace_field(match):
        field_name = match.group(1)
        
        if field_name not in row_data:
            print(f"Warning: Column '{field_name}' not found for element '{element_id}'")
            return ""
        
        return str(row_data.get(field_name, ""))
    
    # Replace remaining field placeholders
    result = re.sub(field_pattern, replace_field, result)
    
    # Remove any remaining ** pairs that resulted from empty fields
    result = re.sub(r'\*\*', '', result)
    
    # Clean up any extra whitespace/newlines from empty sections
    result = result.strip()
    
    return result


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


def render_template(tree: etree.ElementTree, bindings: List[Dict[str, Any]], row_data: Dict[str, Any]) -> etree.ElementTree:
    """Substitute values from row_data into template elements based on bindings"""
    
    for binding in bindings:
        element_id = binding["element_id"]
        template_value = binding.get("value", "")
        
        # Find element in template
        element = tree.find(f".//*[@id='{element_id}']")
        
        if element is None:
            print(f"Warning: Element '{element_id}' not found in template")
            continue
        
        # Resolve template with row data
        value = resolve_template_value(template_value, row_data, element_id)
        
        # Apply prefix if specified and value is not empty
        prefix = binding.get("prefix")
        if prefix and value:
            value = prefix + value
        
        # Handle text elements
        tag = element.tag.split("}")[-1]  # Get local name without namespace
        
        if tag == "text":
            # Find first direct tspan child
            tspan = element.find("{http://www.w3.org/2000/svg}tspan")
            if tspan is not None:
                # Clear nested children of tspan (keep tspan element with attributes)
                for child in list(tspan):
                    tspan.remove(child)
                # Set the tspan's text (or leave empty if value is empty)
                tspan.text = value if value else None
                # Remove any other tspan siblings
                for child in list(element):
                    if child is not tspan and child.tag.endswith('}tspan'):
                        element.remove(child)
            else:
                element.text = value if value else None
        elif tag == "tspan":
            # Clear all nested tspans before setting text
            for child in list(element):
                element.remove(child)
            element.text = value if value else None
        else:
            # For other elements, just set text content
            set_element_text_content(element, value if value else "")
    
    return tree


def save_svg(tree: etree.ElementTree, output_path: str) -> None:
    """Save SVG tree to file without pretty printing"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write without pretty printing
    tree.write(
        str(path),
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=False
    )
