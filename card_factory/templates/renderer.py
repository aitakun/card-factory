"""SVG Template rendering and value substitution"""

import math
import re
from typing import Dict, Any, List, Tuple, Set, Optional
from lxml import etree
from pathlib import Path


SVG_NS = "{http://www.w3.org/2000/svg}"

INLINE_PATTERN_RE = re.compile(r'\$\{([^}]+)\}')

MARKERS = [
    ('*', '*', 'bold'),
    ('!', '!', 'heavy'),
    ('_', '_', 'italic'),
    ('#', '#', 'small'),
]

CHAR_WIDTH_FACTOR = 0.30
LINE_HEIGHT_FACTOR = 0.65


def calculate_fitting_font_size(
    text: str,
    box_width: float,
    box_height: float,
    min_size: int = 8,
    max_size: int = 32,
    step: int = 2,
    aggression: float = 1.0
) -> int:
    """Calculate font size that fits text within a bounding box.

    Uses a shrink-to-fit algorithm: starts at max_size and decreases
    until text fits or min_size is reached.

    Args:
        text: The text content to fit
        box_width: Width of the bounding box in SVG units
        box_height: Height of the bounding box in SVG units
        min_size: Minimum font size to allow (default: 8)
        max_size: Maximum font size to start from (default: 32)
        step: Font size decrement step (default: 2)
        aggression: Scaling factor - higher = less shrinking (default: 1.0)

    Returns:
        The computed font size that fits the text
    """
    if not text or not box_width or not box_height or box_width <= 0 or box_height <= 0:
        return max_size

    for font_size in range(max_size, min_size - 1, -step):
        if _does_text_fit(text, font_size, box_width, box_height, aggression):
            return font_size

    return min_size


def _does_text_fit(
    text: str,
    font_size: int,
    box_width: float,
    box_height: float,
    aggression: float = 1.0
) -> bool:
    """Check if text fits within box at given font size.

    Uses character-length mapping with adjustable aggression:
    - Higher aggression = more shrinking (more text fits at each size)
    - Lower aggression = less shrinking (less text fits at each size)
    
    Base thresholds (at aggression=1.0):
    - 32: <= 75 chars
    - 30: <= 150 chars
    - 28: <= 250 chars
    - 26: <= 350 chars
    - 24: <= 450 chars
    
    With aggression factor, thresholds scale proportionally.
    """
    text_len = len(text.replace('\n', ''))
    
    # Scale thresholds by aggression factor
    # Higher aggression = can fit more text at each size
    if font_size == 32:
        return text_len <= 75 * aggression
    elif font_size == 30:
        return text_len <= 150 * aggression
    elif font_size == 28:
        return text_len <= 250 * aggression
    elif font_size == 26:
        return text_len <= 350 * aggression
    elif font_size == 24:
        return text_len <= 450 * aggression
    elif font_size == 22:
        return text_len <= 550 * aggression
    else:
        return True


def get_text_box_dimensions(tree: etree.ElementTree, element: etree.Element) -> Tuple[Optional[float], Optional[float]]:
    """Find bounding box dimensions from text element's shape-inside attribute.

    Looks for shape-inside:url(#rectId) in the element's style, then finds
    the rect element with matching id and returns (width, height).

    Args:
        tree: The SVG element tree
        element: The text element to find box for

    Returns:
        Tuple of (box_width, box_height) or (None, None) if not found
    """
    if element is None:
        return None, None

    style = element.get("style", "")
    if not style:
        return None, None

    match = re.search(r'shape-inside:\s*url\(#([^)]+)\)', style)
    if not match:
        return None, None

    rect_id = match.group(1)
    rect = tree.find(f".//*[@id='{rect_id}']")

    if rect is None:
        return None, None

    width = rect.get("width")
    height = rect.get("height")

    try:
        w = float(width) if width else None
        h = float(height) if height else None
        return (w, h) if w is not None and h is not None else (None, None)
    except (ValueError, TypeError):
        return None, None


def get_format_attributes(fmt: str, small_font_size: int = 28) -> Dict[str, str]:
    """Map format names to SVG attributes.
    
    Args:
        fmt: Format name ('bold', 'heavy', 'italic', 'small', or None)
        small_font_size: Font size in pixels for small text (default: 28)
        
    Returns:
        Dictionary of SVG attribute names to values for this format
    """
    attrs = {}
    if fmt == "heavy":
        attrs["font-weight"] = "900"
    elif fmt == "bold":
        attrs["font-weight"] = "bold"
    elif fmt == "italic":
        attrs["font-style"] = "italic"
    elif fmt == "small":
        attrs["font-size"] = str(small_font_size)
    return attrs


def get_excluded_base_attributes() -> Set[str]:
    """Base attributes NOT inherited when formatting is applied.
    
    These attributes are set by the formatting logic and should not be
    inherited from the base tspan attributes.
    """
    return {'id', 'font-weight', 'font-style'}


def create_formatting_tspan(
    parent: etree.Element,
    segment: Dict[str, Any],
    base_attrs: Dict[str, str],
    small_font_size: int = 28
) -> etree.Element:
    """Create tspan with formatting attributes applied.
    
    Args:
        parent: Parent SVG element to add the tspan to
        segment: Segment dictionary with 'format', 'text', and optional 'content'
        base_attrs: Base attributes to inherit from parent
        small_font_size: Font size in pixels for small text (default: 28)
        
    Returns:
        The created tspan element
    """
    fmt = segment.get("format")
    content = segment.get("content")
    
    nested = etree.SubElement(parent, f"{SVG_NS}tspan")
    
    for attr, val in base_attrs.items():
        if attr not in get_excluded_base_attributes():
            nested.set(attr, val)
    
    for attr, val in get_format_attributes(fmt, small_font_size).items():
        nested.set(attr, val)
    
    if content is not None:
        for child_seg in content:
            create_formatting_tspan(nested, child_seg, base_attrs, small_font_size)
    else:
        nested.text = segment.get("text", "")
    
    return nested


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
    - #text# for small (font-size: 28px)
    
    All formats can be nested within each other.
    """
    if not text:
        return []
    
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


def apply_markdown_within_tspan(tspan: etree.Element, text: str, small_font_size: int = 28) -> None:
    """
    Apply markdown formatting by creating nested tspans within an existing tspan.
    The parent tspan's base attributes are inherited, but font-weight/font-style/font-size
    are explicitly set for formatted segments.
    
    Args:
        tspan: The SVG tspan element to apply formatting to
        text: Text content with markdown-like formatting
        small_font_size: Font size in pixels for small text (default: 28)
    """
    segments = parse_markdown_segments(text)
    
    if not segments:
        tspan.text = None
        return
    
    needs_formatting = any(s.get("format") is not None for s in segments)
    
    if not needs_formatting:
        tspan.text = text
        return
    
    base_attrs = {}
    for attr, val in tspan.attrib.items():
        if attr not in ('id',):
            base_attrs[attr] = val
    
    tspan.text = None
    for child in list(tspan):
        tspan.remove(child)
    
    for segment in segments:
        create_formatting_tspan(tspan, segment, base_attrs, small_font_size)


def apply_formatted_text(element: etree.Element, text: str, small_font_size: int = 28) -> None:
    """
    Apply text to element with markdown formatting support.
    
    Preserves existing tspan structure - only creates formatting tspans when needed.
    
    Handles different element types:
    - If element is a tspan (has ID on tspan): substitute text, apply markdown if needed
    - If element is a text (has ID on text): if no existing tspans, create one with markdown;
      if tspans exist, apply markdown within first tspan
    
    Args:
        element: The SVG element to apply text to
        text: Text content with markdown-like formatting
        small_font_size: Font size in pixels for small text (default: 28)
    """
    
    # If element is a text element
    if element.tag == f"{SVG_NS}text":
        # Find all child tspans
        tspans = element.findall(f"{SVG_NS}tspan")
        
        if not tspans:
            # No existing tspans - create one with the text (markdown will be parsed within it)
            tspan = etree.SubElement(element, f"{SVG_NS}tspan")
            tspan.text = text
            apply_markdown_within_tspan(tspan, text, small_font_size)
            return
        
        # Has existing tspans - apply to first one
        tspan = tspans[0]
        tspan.text = text
        apply_markdown_within_tspan(tspan, text, small_font_size)
        return
    
    # If element is a tspan
    if element.tag == f"{SVG_NS}tspan":
        element.text = text
        apply_markdown_within_tspan(element, text, small_font_size)
        return
    
    # Non-text/tspan element, just set text
    set_element_text_content(element, text)


def apply_formatted_text_with_paragraphs(element: etree.Element, text: str, paragraph_spacing: int, small_font_size: int = 28) -> None:
    """
    Apply text to element with markdown formatting AND paragraph support.
    
    This function builds the entire tspan tree in one go:
    - text element
      - paragraph_tspan (data-paragraph-index="0", fill-opacity="0" or None)
        - markdown_tspan (with formatting from *bold*, _italic_, !heavy!, #small#)
          - text content
      - paragraph_tspan (data-paragraph-index="1", fill-opacity="0")
        - ...
    
    This avoids the complexity of trying to wrap existing tspans after they're created.
    
    Args:
        element: The SVG text element to apply text to
        text: Text content with markdown-like formatting
        paragraph_spacing: Spacing in SVG units between paragraphs
        small_font_size: Font size in pixels for small text (default: 28)
    """
    if element.tag != f"{SVG_NS}text":
        set_element_text_content(element, text)
        return
    
    paragraphs = text.split('\n')
    num_paragraphs = len(paragraphs)
    
    # Get base attributes from existing tspan BEFORE clearing
    base_tspan = element.find(f"{SVG_NS}tspan")
    base_attrs = {}
    if base_tspan is not None:
        for attr, val in base_tspan.attrib.items():
            if attr not in ('id',):
                base_attrs[attr] = val
    
    # Clear existing content
    element.text = None
    for child in list(element):
        element.remove(child)
    
    for p_idx in range(num_paragraphs):
        paragraph_text = paragraphs[p_idx]
        
        # Create paragraph wrapper tspan
        p_tspan = etree.SubElement(element, f"{SVG_NS}tspan")
        p_tspan.set("data-paragraph-index", str(p_idx))
        
        # First paragraph is visible, others hidden
        if p_idx > 0:
            p_tspan.set("fill-opacity", "0")
        
        # Parse markdown and create nested tspans for this paragraph
        segments = parse_markdown_segments(paragraph_text)
        needs_formatting = any(s.get("format") is not None for s in segments)
        
        # Add newline to paragraph wrapper to create vertical spacing (except first and last)
        # First paragraph starts at original position, subsequent ones need newlines
        if p_idx > 0 and p_idx < num_paragraphs:
            p_tspan.text = "\n"
        
        if not needs_formatting:
            inner_tspan = etree.SubElement(p_tspan, f"{SVG_NS}tspan")
            for attr, val in base_attrs.items():
                inner_tspan.set(attr, val)
            inner_tspan.text = paragraph_text
        else:
            for segment in segments:
                create_formatting_tspan(p_tspan, segment, base_attrs, small_font_size)


def resolve_template_value(template: str, row_data: Dict[str, Any], element_id: str, substitutions: Dict[str, str] = None) -> str:
    """
    Resolve a template string by replacing {field} placeholders with values from row_data.
    
    Supports transform tags: [uppercase]{field}[/uppercase], [lowercase]{field}[/lowercase]
    
    If the template is just a simple field name (no special syntax), resolves it directly.
    
    If a field resolves to empty, surrounding text is also removed (e.g., ** becomes empty).
    
    Substitutions (if provided) are applied after field replacement but before transforms.
    
    Processing order:
    1. Replace {field} placeholders
    2. Apply substitutions
    3. Apply [uppercase]/[lowercase] transforms
    
    Returns the resolved string with all placeholders replaced.
    Warns on missing columns.
    """
    if substitutions is None:
        substitutions = {}
    
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
            return ""
        
        if transform_type == "uppercase":
            return value.upper()
        elif transform_type == "lowercase":
            return value.lower()
        return value
    
    # Step 1: Apply transforms first (to handle normal transforms without substitutions)
    result = re.sub(transform_pattern, replace_transform, result)
    
    # Pattern to match simple field placeholders: {field_name}
    field_pattern = r'\{([^}]+)\}'
    
    def replace_field(match):
        field_name = match.group(1)
        
        if field_name not in row_data:
            print(f"Warning: Column '{field_name}' not found for element '{element_id}'")
            return ""
        
        return str(row_data.get(field_name, ""))
    
    # Step 2: Replace field placeholders
    result = re.sub(field_pattern, replace_field, result)
    
    # Step 3: Apply substitutions
    for pattern, replacement in substitutions.items():
        result = result.replace(pattern, replacement)
    
    # Step 4: Re-apply transforms to handle any transforms created by substitutions
    result = re.sub(transform_pattern, replace_transform, result)
    
    # Remove formatting markers that resulted from empty fields
    # e.g., **** (from **empty**) should become empty, but **content** stays
    result = re.sub(r'\*\*\*\*+', '', result)
    result = re.sub(r'______+', '', result)
    
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


def apply_paragraph_spacing(tree: etree.ElementTree, element: etree.Element, paragraph_spacing: int) -> None:
    """Apply paragraph spacing workaround for Inkscape.
    
    Since Inkscape doesn't support proper paragraph spacing, we create copies
    of the text element - one for each paragraph - and translate them vertically.
    Each text element contains ALL paragraphs, with fill-opacity controlling visibility.
    Hidden paragraphs act as spacers to push the visible paragraph to the correct position.
    
    Steps:
    1. Find all paragraph tspans (identified by data-paragraph-index attribute)
    2. Count paragraphs
    3. Clone the <text> element N times (N = number of paragraphs)
    4. Translate each copy down by index * paragraph_spacing
    5. In each copy, set fill-opacity="0" on all paragraphs except the one with matching index
    """
    if element.tag != f"{SVG_NS}text":
        return
    
    # Use namespace-prefixed xpath for original element
    paragraph_tspans = element.findall(f"{SVG_NS}tspan[@data-paragraph-index]")
    
    if not paragraph_tspans:
        return
    
    num_paragraphs = len(set(tspan.get("data-paragraph-index") for tspan in paragraph_tspans))
    
    if num_paragraphs <= 1 or paragraph_spacing <= 0:
        # Remove fill-opacity from single paragraph (not needed when no cloning)
        for p_tspan in paragraph_tspans:
            if p_tspan.get("fill-opacity") == "0":
                del p_tspan.attrib["fill-opacity"]
        return
    
    # Serialize original element ONCE before any modifications
    original_xml = etree.tostring(element)
    
    # First, set all paragraphs to hidden in original element
    for p_tspan in paragraph_tspans:
        p_tspan.set("fill-opacity", "0")
    
    # Make first paragraph visible in original element
    if paragraph_tspans:
        if paragraph_tspans[0].get("fill-opacity") == "0":
            del paragraph_tspans[0].attrib["fill-opacity"]
    
    # Create clones for remaining paragraphs
    for idx in range(1, num_paragraphs):
        cloned = etree.fromstring(original_xml)
        
        existing_id = cloned.get("id")
        if existing_id:
            cloned.set("id", f"{existing_id}-{idx}")
        
        existing_transform = element.get("transform")
        new_transform = modify_translate_y(existing_transform, idx * paragraph_spacing)
        cloned.set("transform", new_transform)
        
        # Set all paragraphs in clone to hidden, then make matching one visible
        cloned_paragraphs = cloned.findall(f"{SVG_NS}tspan[@data-paragraph-index]")
        for p_tspan in cloned_paragraphs:
            p_tspan.set("fill-opacity", "0")
        
        # Make the paragraph matching this clone's index visible
        for p_tspan in cloned_paragraphs:
            if p_tspan.get("data-paragraph-index") == str(idx):
                if p_tspan.get("fill-opacity") == "0":
                    del p_tspan.attrib["fill-opacity"]
                break
        
        parent = element.getparent()
        parent.append(cloned)


def modify_translate_y(existing_transform: str, delta_y: float) -> str:
    """Modify the translateY component of a transform attribute.
    
    Supports:
    - transform="translate(x,y)"
    - transform="matrix(a,b,c,d,e,f)" - extracts and modifies the e/f components
    
    Returns the modified transform string.
    """
    def format_num(n):
        if n == int(n):
            return str(int(n))
        return str(n)
    
    if not existing_transform:
        return f"translate(0,{format_num(delta_y)})"
    
    translate_match = re.match(r'translate\s*\(\s*([^,)]+)\s*,\s*([^)]+)\s*\)', existing_transform, re.IGNORECASE)
    if translate_match:
        x = float(translate_match.group(1))
        y = float(translate_match.group(2))
        new_y = y + delta_y
        return f"translate({format_num(x)},{format_num(new_y)})"
    
    matrix_match = re.match(r'matrix\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)', existing_transform)
    if matrix_match:
        a, b, c, d, e, f = matrix_match.groups()
        new_f = float(f) + delta_y
        return f"matrix({a},{b},{c},{d},{e},{format_num(new_f)})"
    
    return f"translate(0,{format_num(delta_y)})"


def resolve_url_template(url_template: str, row_data: Dict[str, Any], element_id: str) -> str:
    """Resolve URL template by replacing {field} placeholders with values from row_data.
    
    Unlike text bindings, URLs should be returned as-is if they don't contain placeholders
    (rather than being looked up as column names).
    
    Supports transform tags: [uppercase]{field}[/uppercase], [lowercase]{field}[/lowercase]
    Also supports shorthand: [uppercase]{field} (auto-closes at {field})
    """
    if not url_template:
        return ""
    
    if '{' not in url_template:
        return url_template
    
    result = url_template
    
    # Pattern for closing tag format: [uppercase]{field}[/uppercase]
    transform_pattern_closed = r'\[(uppercase|lowercase)\]\{([^}]+)\}\[/\1\]'
    
    # Pattern for shorthand format: [uppercase]{field} (auto-closes)
    transform_pattern_shorthand = r'\[(uppercase|lowercase)\]\{([^}]+)\}'
    
    def replace_transform(match):
        transform_type = match.group(1)
        field_name = match.group(2)
        
        if field_name not in row_data:
            print(f"Warning: Column '{field_name}' not found for element '{element_id}'")
            return ""
        
        value = str(row_data.get(field_name, ""))
        
        if not value:
            return ""
        
        if transform_type == "uppercase":
            return value.upper()
        elif transform_type == "lowercase":
            return value.lower()
        return value
    
    # Replace transform tags first (both formats)
    result = re.sub(transform_pattern_closed, replace_transform, result)
    result = re.sub(transform_pattern_shorthand, replace_transform, result)
    
    # Pattern to match simple field placeholders: {field_name}
    field_pattern = r'\{([^}]+)\}'
    
    def replace_field(match):
        field_name = match.group(1)
        if field_name not in row_data:
            print(f"Warning: Column '{field_name}' not found for element '{element_id}'")
            return ""
        return str(row_data.get(field_name, ""))
    
    return re.sub(field_pattern, replace_field, result)


def download_and_embed_image(url: str, element_id: str) -> str:
    """Download image from URL(s) and convert to data URI blob.
    
    Supports multiple URLs as fallback, separated by | or ,
    Tries each URL in order until one succeeds.
    
    Returns:
        Data URI string for embedding, or empty string if all fail
    """
    from ..utils.file_handler import get_image, image_to_data_uri, is_remote_url
    
    if not url:
        return ""
    
    # Split by | or , for fallback URLs
    urls = [u.strip() for u in re.split(r'[|,]', url) if u.strip()]
    
    last_error = None
    for attempt_url in urls:
        try:
            image_bytes, mime_type = get_image(attempt_url)
            return image_to_data_uri(image_bytes, mime_type)
        except FileNotFoundError as e:
            if is_remote_url(attempt_url):
                last_error = f"Failed to download from '{attempt_url}': {e}"
            else:
                last_error = f"Local image not found: '{attempt_url}'"
        except Exception as e:
            last_error = f"Failed to get image from '{attempt_url}': {e}"
    
    print(f"Warning: Could not load image for '{element_id}' from any URL. Last error: {last_error}")
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


def render_template(tree: etree.ElementTree, bindings: List[Dict[str, Any]], row_data: Dict[str, Any], substitutions: Dict[str, str] = None, small_font_size: int = 28) -> etree.ElementTree:
    """Substitute values from row_data into template elements based on bindings.
    
    Resolution order:
    1. Inline ${binding_id} patterns in SVG elements
    2. Standard bindings by element ID
    
    Args:
        tree: The SVG template tree
        bindings: List of binding configurations
        row_data: Data from spreadsheet row
        substitutions: Optional dict of string replacements applied after field substitution
        small_font_size: Font size in pixels for small text (default: 28)
    """
    if substitutions is None:
        substitutions = {}
    
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
        value = resolve_template_value(template_value, row_data, element_id, substitutions)
        
        # Apply prefix if specified and value is not empty
        prefix = binding.get("prefix")
        if prefix and value:
            value = prefix + value
        
# Calculate fitting font size if fit: "box" is specified
        fit_mode = binding.get("fit")
        computed_font_size = None
        if fit_mode == "box":
            min_size = binding.get("min_font_size", 8)
            max_size = binding.get("max_font_size", 32)
            aggression = binding.get("fit_aggression", 1.0)
            box_width, box_height = get_text_box_dimensions(tree, element)
            if box_width and box_height:
                computed_font_size = calculate_fitting_font_size(value, box_width, box_height, min_size, max_size, aggression=aggression)
                element.set("font-size", str(computed_font_size))
                # Also update style attribute (takes precedence in SVG)
                style = element.get("style", "")
                if style:
                    new_style = re.sub(r'font-size:\s*[\d.]+px', f'font-size:{computed_font_size}px', style)
                    element.set("style", new_style)
        
        # Apply formatted text to element (with markdown support)
        # Note: small_font_size (for #small# formatting) uses the default parameter,
        # not the computed font-size. This preserves existing behavior where
        # #small# text has its own fixed size. Relative scaling can be added later.
        paragraph_spacing = binding.get("paragraph_spacing")
        if paragraph_spacing and isinstance(paragraph_spacing, int) and paragraph_spacing > 0:
            # Use new function that builds entire tspan tree at once
            apply_formatted_text_with_paragraphs(element, value, paragraph_spacing, small_font_size)
            apply_paragraph_spacing(tree, element, paragraph_spacing)
        else:
            apply_formatted_text(element, value, small_font_size)
    
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


def evaluate_condition(condition: str, row_data: Dict[str, Any]) -> bool:
    """Evaluate a condition with support for ==, >, <, >=, <=, ~=.
    
    Returns True if condition passes (element should be shown),
    False if condition fails (element should be hidden).
    
    If condition is empty or invalid, returns True (show by default).
    
    Examples:
        - cost==5
        - strength>3
        - amount>=10
        - name~=Ice
    """
    if not condition:
        return True
    
    # Pattern to match all operators: ==, >, <, >=, <=, ~= (note: ~= must come before = to avoid = being matched first)
    match = re.match(r'^([^=]+)(~=|>=|<=|==|>|<)(.+)$', condition.strip())
    if not match:
        print(f"Warning: Invalid condition format: '{condition}' (expected 'column==value' or 'column>value', etc.)")
        return True
    
    column, operator, expected = match.groups()
    column = column.strip()
    expected = expected.strip()
    
    actual = str(row_data.get(column, ""))
    
    # Handle numeric comparisons
    if operator in ('>', '<', '>=', '<='):
        # Empty strings should warn and hide
        if not actual:
            print(f"Warning: Cannot compare empty value for '{column}' with {operator}")
            return False
        
        try:
            actual_num = float(actual)
            expected_num = float(expected)
        except ValueError:
            print(f"Warning: Cannot compare non-numeric value '{actual}' with {operator}")
            return False
        
        if operator == '>':
            return actual_num > expected_num
        elif operator == '<':
            return actual_num < expected_num
        elif operator == '>=':
            return actual_num >= expected_num
        elif operator == '<=':
            return actual_num <= expected_num
    
    # Handle contains (substring) check
    if operator == '~=':
        return expected in actual
    
    # For ==, keep existing string comparison (backwards compatible)
    return actual == expected


def apply_visibility(tree: etree.ElementTree, visibility_config: List[Dict[str, Any]], row_data: Dict[str, Any]) -> None:
    """Show/hide elements based on visibility conditions.
    
    Each config has:
    - element_id: ID of the element to control
    - condition: simple expression like 'unique==yes' (optional, defaults to show)
    
    When condition evaluates to False, sets display="none" on the element.
    """
    for config in visibility_config:
        element_id = config["element_id"]
        condition = config.get("condition", "")
        
        element = tree.find(f".//*[@id='{element_id}']")
        if element is None:
            print(f"Warning: Element '{element_id}' not found in template for visibility control")
            continue
        
        # Evaluate condition
        if not evaluate_condition(condition, row_data):
            element.set("display", "none")


def apply_color_schemes(tree: etree.ElementTree, color_config: Dict[str, Any], row_data: Dict[str, Any]) -> None:
    """Apply color scheme based on row data.
    
    color_config structure:
    {
        'lookup_column': 'faction',
        'schemes': {
            'criminal': {'primary-color': '#194c9b', ...},
            'neutral': {...}
        }
    }
    
    For each color mapping, finds the gradient and updates its stop-color.
    Lookup is case-insensitive.
    """
    if not color_config:
        return
    
    lookup_column = color_config.get('lookup_column')
    schemes = color_config.get('schemes', {})
    
    if not lookup_column or not schemes:
        return
    
    # Get lookup value (case-insensitive)
    lookup_value = str(row_data.get(lookup_column, "")).lower()
    
    # Find matching scheme (case-insensitive)
    colors = None
    for scheme_key, scheme_colors in schemes.items():
        if scheme_key.lower() == lookup_value:
            colors = scheme_colors
            break
    
    if not colors:
        # No matching scheme, keep existing colors
        return
    
    # Apply colors to gradients
    for gradient_id, color in colors.items():
        gradient = tree.find(f".//*[@id='{gradient_id}']")
        if gradient is None:
            print(f"Warning: Gradient '{gradient_id}' not found in template for color scheme")
            continue
        
        # Find stop element
        stop = gradient.find(f"{SVG_NS}stop")
        if stop is None:
            print(f"Warning: No stop element found in gradient '{gradient_id}'")
            continue
        
        # Update stop-color in style
        stop_style = stop.get('style', '')
        if 'stop-color:' in stop_style:
            new_style = re.sub(
                r'stop-color:[^;]+',
                f'stop-color:{color}',
                stop_style
            )
            stop.set('style', new_style)
        else:
            # No stop-color in style, add it
            if stop_style and not stop_style.endswith(';'):
                stop_style += ';'
            stop.set('style', stop_style + f"stop-color:{color};")
