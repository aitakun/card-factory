"""SVG Template rendering and value substitution"""

import re
from typing import Dict, Any, List, Tuple
from lxml import etree
from pathlib import Path


SVG_NS = "{http://www.w3.org/2000/svg}"


def parse_markdown_segments(text: str) -> List[Dict[str, Any]]:
    """
    Parse text with markdown formatting and return segments with formatting info.
    
    Supports:
    - **text** or __text__ for bold
    - *text* or _text_ for italics
    
    Input: "This is **bold** and *italic* text"
    Output: [
        {"text": "This is ", "bold": False, "italic": False},
        {"text": "bold", "bold": True, "italic": False},
        {"text": " and ", "bold": False, "italic": False},
        {"text": "italic", "bold": False, "italic": True},
        {"text": " text", "bold": False, "italic": False}
    ]
    """
    if not text:
        return []
    
    segments = []
    
    # Combined pattern for all markers
    # Order: **bold**, __bold__, *italic*, _italic_, ***bold italic***
    # Need to handle *** (bold+italic) first
    pattern = r'(\*\*\*[^*]+\*\*\*|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_([^_]+)_)'
    
    last_end = 0
    
    for match in re.finditer(pattern, text):
        # Add plain text before this match
        if match.start() > last_end:
            plain_text = text[last_end:match.start()]
            if plain_text:
                segments.append({"text": plain_text, "bold": False, "italic": False})
        
        full_match = match.group(0)
        
        # Check for bold+italic (***text***)
        bold_italic_match = re.match(r'\*\*\*([^*]+)\*\*\*', full_match)
        if bold_italic_match:
            segments.append({
                "text": bold_italic_match.group(1),
                "bold": True,
                "italic": True
            })
            last_end = match.end()
            continue
        
        # Check for bold (**text** or __text__)
        bold_match = re.match(r'\*\*([^*]+)\*\*|__([^_]+)__', full_match)
        if bold_match:
            bold_text = bold_match.group(1) or bold_match.group(2)
            segments.append({"text": bold_text, "bold": True, "italic": False})
            last_end = match.end()
            continue
        
        # Check for italic (*text* or _text_)
        italic_match = re.match(r'\*([^*]+)\*|_([^_]+)_', full_match)
        if italic_match:
            italic_text = italic_match.group(1) or italic_match.group(2)
            segments.append({"text": italic_text, "bold": False, "italic": True})
            last_end = match.end()
            continue
    
    # Add remaining plain text
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            segments.append({"text": remaining, "bold": False, "italic": False})
    
    return segments


def apply_formatted_text(element: etree.Element, text: str) -> None:
    """
    Replace element's content with formatted tspans based on markdown.
    
    Creates multiple tspans without whitespace between them to prevent
    unwanted spaces in the rendered text.
    """
    # Find or create the parent text element
    if element.tag == f"{SVG_NS}text":
        parent = element
    elif element.tag == f"{SVG_NS}tspan":
        parent = element.getparent()
        if parent is None:
            parent = element
    else:
        # Non-text element, just set text
        set_element_text_content(element, text)
        return
    
    # Clear all existing children tspans
    for child in list(parent):
        if child.tag.endswith('}tspan'):
            parent.remove(child)
    
    # Parse markdown into segments
    segments = parse_markdown_segments(text)
    
    if not segments:
        # Empty text - clear parent
        parent.text = None
        return
    
    # Create tspans for each segment
    first = True
    for segment in segments:
        seg_text = segment["text"]
        if not seg_text:
            continue
        
        tspan = etree.SubElement(parent, f"{SVG_NS}tspan")
        
        # Copy x, y attributes from original tspan if it exists
        original_tspan = None
        for child in parent:
            if child.tag.endswith('}tspan') and child.get('x') and child.get('y'):
                original_tspan = child
                break
        
        if original_tspan is not None and first:
            # Copy position attributes only to first tspan
            if original_tspan.get('x'):
                tspan.set('x', original_tspan.get('x'))
            if original_tspan.get('y'):
                tspan.set('y', original_tspan.get('y'))
        
        # Set formatting attributes
        if segment["bold"]:
            tspan.set("font-weight", "bold")
        if segment["italic"]:
            tspan.set("font-style", "italic")
        
        # Set text content (no spaces between tspans)
        tspan.text = seg_text
        
        first = False
    
    # Set parent text to None (tspans contain the text)
    parent.text = None


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
    
    # Remove any remaining ** or __ pairs that resulted from empty fields
    result = re.sub(r'\*\*|__', '', result)
    
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
        
        # Apply formatted text to element (with markdown support)
        apply_formatted_text(element, value)
    
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
