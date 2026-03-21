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
                # Substitute the pattern
                new_text = INLINE_PATTERN_RE.sub(resolved, element.text, count=1)
                element.text = new_text
                # Apply text with markdown formatting (handles all cases)
                apply_formatted_text(element, new_text)
        
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
                    # Substitute the pattern
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
    Parse text with markdown-like formatting and return segments with nested structure.
    
    Supports nested formatting:
    - *text* for bold
    - !text! for heavy (font-weight: 900)
    - _text_ for italic
    
    Heavy and italic can be nested inside bold.
    """
    if not text:
        return []
    
    MARKERS = [
        ('*', '*', 'bold'),
        ('!', '!', 'heavy'),
        ('_', '_', 'italic'),
    ]
    
    def find_matching_close(txt, start):
        """Find the matching close marker for the opener at position start."""
        open_c = txt[start]
        close_c = None
        fmt = None
        
        for o, c, f in MARKERS:
            if o == open_c:
                close_c = c
                fmt = f
                break
        
        if not close_c:
            return None, None, None
        
        depth = 1
        i = start + 1
        while i < len(txt) and depth > 0:
            char = txt[i]
            # Check closer FIRST (important for same-char markers like *)
            if char == close_c and open_c == close_c:
                depth -= 1
                if depth == 0:
                    return i + 1, txt[start+1:i], fmt
            elif char == close_c:
                depth -= 1
                if depth == 0:
                    return i + 1, txt[start+1:i], fmt
            elif char == open_c:
                # Nested opener
                depth += 1
            i += 1
        
        return None, None, None
    
    segments = []
    i = 0
    
    while i < len(text):
        char = text[i]
        matched = False
        
        for open_c, close_c, fmt in MARKERS:
            if char == open_c:
                # Try to find a matching close
                end, inner, _ = find_matching_close(text, i)
                if end:
                    # Found a match
                    # Recursively parse inner content
                    inner_segments = parse_markdown_segments(inner)
                    
                    # Check if inner has formatting
                    has_inner = any(s.get("format") is not None for s in inner_segments)
                    
                    if has_inner:
                        # Inner has formatting - wrap it with outer
                        segments.append({
                            "format": fmt,
                            "content": inner_segments
                        })
                    else:
                        segments.append({"text": inner, "format": fmt})
                    
                    i = end
                    matched = True
                    break
        
        if not matched:
            # Not a marker start, collect as plain text
            if not segments or segments[-1].get("format") is not None:
                segments.append({"text": char, "format": None})
            else:
                segments[-1]["text"] += char
            i += 1
    
    # Merge consecutive plain segments
    merged = []
    for seg in segments:
        if seg.get("format") is None and merged and merged[-1].get("format") is None:
            merged[-1]["text"] += seg["text"]
        else:
            merged.append(seg)
    
    return merged


def apply_markdown_within_tspan(tspan: etree.Element, text: str) -> None:
    """
    Apply markdown formatting by creating nested tspans within an existing tspan.
    The parent tspan's base attributes are inherited, but font-weight/font-style
    are explicitly set for formatted segments.
    """
    segments = parse_markdown_segments(text)
    
    if not segments:
        tspan.text = None
        return
    
    # Check if any segment needs formatting
    needs_formatting = any(s.get("format") is not None for s in segments)
    
    if not needs_formatting:
        # No formatting needed, just set the text
        tspan.text = text
        return
    
    # Save the parent tspan's base attributes (excluding formatting-specific ones)
    base_attrs = {}
    for attr, val in tspan.attrib.items():
        if attr not in ('id',):
            base_attrs[attr] = val
    
    # Clear the parent tspan (both text and children)
    tspan.text = None
    for child in list(tspan):
        tspan.remove(child)
    
    # Create nested tspans recursively
    def create_nested_tspan(parent_tspan, segment, parent_format=None):
        """Recursively create tspans for segments with nested formatting support."""
        fmt = segment.get("format")
        content = segment.get("content")
        
        # Determine font attributes based on format
        font_weight = None
        font_style = None
        
        if fmt == "heavy":
            font_weight = "900"
        elif fmt == "bold":
            font_weight = "bold"
        elif fmt == "italic":
            font_style = "italic"
        
        # Create the tspan
        nested = etree.SubElement(parent_tspan, f"{SVG_NS}tspan")
        
        # Copy base attributes (but don't override font-weight/font-style from inner formatting)
        for attr, val in base_attrs.items():
            if attr not in ('font-weight', 'font-style'):
                nested.set(attr, val)
        
        # Apply this level's formatting (overrides base)
        if font_weight:
            nested.set("font-weight", font_weight)
        if font_style:
            nested.set("font-style", font_style)
        
        # Handle content
        if content is not None:
            # Has nested content - recursively create children
            for child_seg in content:
                create_nested_tspan(nested, child_seg, fmt)
        else:
            # Simple text
            nested.text = segment.get("text", "")
    
    for segment in segments:
        create_nested_tspan(tspan, segment)


def apply_formatted_text(element: etree.Element, text: str) -> None:
    """
    Apply text to element with markdown formatting support.
    
    Preserves existing tspan structure - only creates formatting tspans when needed.
    
    Handles different element types:
    - If element is a tspan (has ID on tspan): substitute text, apply markdown if needed
    - If element is a text (has ID on text): if no existing tspans, create one with markdown;
      if tspans exist, apply markdown within first tspan
    """
    
    # If element is a text element
    if element.tag == f"{SVG_NS}text":
        # Find all child tspans
        tspans = element.findall(f"{SVG_NS}tspan")
        
        if not tspans:
            # No existing tspans - create one with the text (markdown will be parsed within it)
            tspan = etree.SubElement(element, f"{SVG_NS}tspan")
            tspan.text = text
            apply_markdown_within_tspan(tspan, text)
            return
        
        # Has existing tspans - apply to first one
        tspan = tspans[0]
        tspan.text = text
        apply_markdown_within_tspan(tspan, text)
        return
    
    # If element is a tspan
    if element.tag == f"{SVG_NS}tspan":
        element.text = text
        apply_markdown_within_tspan(element, text)
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
