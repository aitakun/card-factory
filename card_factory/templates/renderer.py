"""SVG Template rendering and value substitution"""

import re
from typing import Dict, Any, List, Tuple, Set
from lxml import etree
from pathlib import Path


SVG_NS = "{http://www.w3.org/2000/svg}"

INLINE_PATTERN_RE = re.compile(r'\$\{([^}]+)\}')


def resolve_inline_patterns(tree: etree.ElementTree, bindings: List[Dict[str, Any]], row_data: Dict[str, Any]) -> Set[str]:
    """Find and resolve ${binding_id} patterns in SVG elements.
    
    Searches for ${id} patterns in:
    - Element text content
    - Element tails (text following child elements)
    - Element attributes
    
    Patterns are resolved using the matching binding from the bindings list.
    After resolution, the pattern is replaced with the resolved value.
    
    Returns:
        Set of binding IDs that were resolved via inline patterns
    """
    # Build lookup from binding_id to binding config
    binding_lookup = {b["element_id"]: b for b in bindings}
    resolved_bindings: Set[str] = set()
    
    # Search all elements in the tree
    for element in tree.iter():
        # Check attributes
        for attr_name in list(element.attrib.keys()):
            attr_value = element.get(attr_name)
            matches = INLINE_PATTERN_RE.findall(attr_value)
            for binding_id in matches:
                resolved_bindings.add(binding_id)
                binding = binding_lookup.get(binding_id)
                if binding is None:
                    print(f"Warning: No binding found for ${{{binding_id}}} in attribute '{attr_name}'")
                    continue
                
                resolved = resolve_binding_value(binding, row_data)
                # Always substitute, even if empty string
                new_value = INLINE_PATTERN_RE.sub(resolved, attr_value, count=1)
                element.set(attr_name, new_value)
        
        # Check element text content
        if element.text:
            matches = INLINE_PATTERN_RE.findall(element.text)
            for binding_id in matches:
                resolved_bindings.add(binding_id)
                binding = binding_lookup.get(binding_id)
                if binding is None:
                    print(f"Warning: No binding found for ${{{binding_id}}} in text content")
                    continue
                
                resolved = resolve_binding_value(binding, row_data)
                # Always substitute, even if empty string
                element.text = INLINE_PATTERN_RE.sub(resolved, element.text, count=1)
        
        # Check element tail (text following child elements)
        for child in element:
            if child.tail:
                matches = INLINE_PATTERN_RE.findall(child.tail)
                for binding_id in matches:
                    resolved_bindings.add(binding_id)
                    binding = binding_lookup.get(binding_id)
                    if binding is None:
                        print(f"Warning: No binding found for ${{{binding_id}}} in text tail")
                        continue
                    
                    resolved = resolve_binding_value(binding, row_data)
                    # Always substitute, even if empty string
                    child.tail = INLINE_PATTERN_RE.sub(resolved, child.tail, count=1)
    
    return resolved_bindings


def resolve_binding_value(binding: Dict[str, Any], row_data: Dict[str, Any]) -> str:
    """Resolve a binding to its final value for inline pattern substitution.
    
    Used by inline pattern resolution to get the value without applying to an element.
    For inline patterns, the binding value is treated as a literal value (not a field reference).
    """
    element_id = binding["element_id"]
    template_value = binding.get("value", "")
    attribute = binding.get("attribute")
    
    # For image bindings (attribute), resolve the URL and embed as blob
    if attribute:
        url = resolve_url_template(template_value, row_data, element_id)
        if url:
            data_uri = download_and_embed_image(url, element_id)
            return data_uri
        return ""
    
    # Text binding - resolve template with row data
    value = resolve_template_value(template_value, row_data, element_id)
    
    # Apply prefix if specified and value is not empty
    prefix = binding.get("prefix")
    if prefix and value:
        value = prefix + value
    
    return value


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
    
    Handles different element types:
    - If element is a tspan (has ID on tspan): modify that tspan directly
    - If element is a text (has ID on text): create formatted tspans as children
    
    Special handling for nested tspan structures where parent is also a tspan.
    """
    
    # If element is a tspan itself (ID is on the tspan)
    if element.tag == f"{SVG_NS}tspan":
        segments = parse_markdown_segments(text)
        
        if not segments:
            element.text = None
            return
        
        if len(segments) == 1 and not segments[0]["bold"] and not segments[0]["italic"]:
            element.text = segments[0]["text"]
            return
        
        # Find the proper text parent (may be grandparent if parent is also a tspan)
        parent = element.getparent()
        if parent is None:
            element.text = text
            return
        
        # If parent is also a tspan, need to go up to find the text element
        actual_text_parent = None
        if parent.tag == f"{SVG_NS}tspan":
            grandparent = parent.getparent()
            if grandparent is not None and grandparent.tag == f"{SVG_NS}text":
                actual_text_parent = grandparent
                parent = grandparent
            else:
                element.text = text
                return
        elif parent.tag == f"{SVG_NS}text":
            actual_text_parent = parent
        else:
            element.text = text
            return
        
        # Find this tspan's position in parent
        tspans = [child for child in parent if child.tag == f"{SVG_NS}tspan"]
        if element in tspans:
            idx = tspans.index(element)
        else:
            idx = 0
        
        # Clear all tspans from parent
        for child in list(parent):
            if child.tag == f"{SVG_NS}tspan":
                parent.remove(child)
        
        # Create new tspans at the same position
        current_idx = 0
        for segment in segments:
            seg_text = segment["text"]
            if not seg_text:
                continue
            
            tspan = etree.Element(f"{SVG_NS}tspan")
            
            # Copy attributes from original tspan (first one only)
            if current_idx == idx and len(element.attrib) > 0:
                for attr, val in element.attrib.items():
                    if attr not in ('id',):
                        tspan.set(attr, val)
            
            # Set formatting attributes
            if segment["bold"]:
                tspan.set("font-weight", "bold")
            if segment["italic"]:
                tspan.set("font-style", "italic")
            
            tspan.text = seg_text
            
            parent.insert(current_idx, tspan)
            current_idx += 1
        
        parent.text = None
        return
    
    # If element is a text element (ID is on text)
    if element.tag == f"{SVG_NS}text":
        # Capture original tspan attributes (first one) for style preservation
        original_tspan_attrs = {}
        for child in element:
            if child.tag == f"{SVG_NS}tspan":
                original_tspan_attrs = dict(child.attrib)
                break
        
        # Clear all existing children tspans
        for child in list(element):
            if child.tag == f"{SVG_NS}tspan":
                element.remove(child)
        
        segments = parse_markdown_segments(text)
        
        if not segments:
            # Empty text - clear parent
            element.text = None
            return
        
        # Create tspans for each segment
        for segment in segments:
            seg_text = segment["text"]
            if not seg_text:
                continue
            
            tspan = etree.SubElement(element, f"{SVG_NS}tspan")
            
            # Copy original tspan attributes (except id)
            for attr, val in original_tspan_attrs.items():
                if attr != 'id':
                    tspan.set(attr, val)
            
            # Set formatting attributes
            if segment["bold"]:
                tspan.set("font-weight", "bold")
            if segment["italic"]:
                tspan.set("font-style", "italic")
            
            # Set text content (no spaces between tspans)
            tspan.text = seg_text
        
        element.text = None
        return
    
    # Non-text/tspan element, just set text
    set_element_text_content(element, text)


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
    
    # Remove formatting markers that resulted from empty fields
    # e.g., **** (from **empty**) should become empty, but **content** stays
    # Match pairs of ** or __ where there's nothing between them
    result = re.sub(r'\*\*\*\*+', '', result)  # **** or more
    result = re.sub(r'______+', '', result)      # ____ or more
    
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


def resolve_url_template(url_template: str, row_data: Dict[str, Any], element_id: str) -> str:
    """Resolve URL template by replacing {field} placeholders with values from row_data.
    
    Unlike text bindings, URLs should be returned as-is if they don't contain placeholders
    (rather than being looked up as column names).
    """
    if not url_template:
        return ""
    
    if '{' not in url_template:
        return url_template
    
    field_pattern = r'\{([^}]+)\}'
    
    def replace_field(match):
        field_name = match.group(1)
        if field_name not in row_data:
            print(f"Warning: Column '{field_name}' not found for element '{element_id}'")
            return ""
        return str(row_data.get(field_name, ""))
    
    return re.sub(field_pattern, replace_field, url_template)


def download_and_embed_image(url: str, element_id: str) -> str:
    """Download image from URL and convert to data URI blob.
    
    Downloads with caching, warns on failure and returns empty string.
    
    Returns:
        Data URI string for embedding, or empty string on failure
    """
    from ..utils.file_handler import download_image_cached, image_to_data_uri
    
    if not url:
        return ""
    
    try:
        image_bytes, mime_type = download_image_cached(url)
        return image_to_data_uri(image_bytes, mime_type)
    except Exception as e:
        print(f"Warning: Failed to download image for '{element_id}' from '{url}': {e}")
        return ""


def apply_image_to_element(element: etree.Element, attribute: str, data_uri: str) -> None:
    """Set an attribute on an SVG element (typically xlink:href for images)."""
    if not data_uri:
        return
    
    # Handle xlink:href specially (SVG uses xlink namespace)
    if attribute == 'xlink:href':
        element.set('{http://www.w3.org/1999/xlink}href', data_uri)
    else:
        element.set(attribute, data_uri)


def render_template(tree: etree.ElementTree, bindings: List[Dict[str, Any]], row_data: Dict[str, Any]) -> etree.ElementTree:
    """Substitute values from row_data into template elements based on bindings.
    
    Resolution order:
    1. Inline ${binding_id} patterns in SVG elements
    2. Standard bindings by element ID
    """
    
    # Step 1: Resolve inline ${id} patterns first
    resolved_bindings = resolve_inline_patterns(tree, bindings, row_data)
    
    # Step 2: Apply remaining bindings by element ID (skip if already resolved inline)
    for binding in bindings:
        element_id = binding["element_id"]
        
        # Skip if this binding was resolved via inline pattern
        if element_id in resolved_bindings:
            continue
        
        template_value = binding.get("value", "")
        attribute = binding.get("attribute")
        
        # Find element in template
        element = tree.find(f".//*[@id='{element_id}']")
        
        if element is None:
            print(f"Warning: Element '{element_id}' not found in template")
            continue
        
        # Check if this is an image binding (has attribute field)
        if attribute:
            # Image binding: resolve URL and embed as blob
            url = resolve_url_template(template_value, row_data, element_id)
            if url:
                data_uri = download_and_embed_image(url, element_id)
                if data_uri:
                    apply_image_to_element(element, attribute, data_uri)
            continue
        
        # Text binding (default behavior)
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
