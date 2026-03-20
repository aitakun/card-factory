"""SVG Template rendering and value substitution"""

from typing import Dict, Any, Optional, List
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


def render_template(tree: etree.ElementTree, bindings: List[Dict[str, Any]], row_data: Dict[str, Any]) -> etree.ElementTree:
    """Substitute values from row_data into template elements based on bindings"""
    
    # Group bindings by source_column for split handling
    bindings_by_column = {}
    for binding in bindings:
        source_column = binding.get("source_column")
        if source_column not in bindings_by_column:
            bindings_by_column[source_column] = []
        bindings_by_column[source_column].append(binding)
    
    # Process each source column once
    for source_column, column_bindings in bindings_by_column.items():
        raw_value = row_data.get(source_column, "")
        parts = []
        
        # Check if any binding for this column needs splitting
        split_by = None
        for binding in column_bindings:
            if "split_by" in binding:
                split_by = binding["split_by"]
                break
        
        if split_by:
            # Split the value
            parts = raw_value.split(split_by)
        
        # Process each binding for this column
        for binding in column_bindings:
            element_id = binding["element_id"]
            split_by = binding.get("split_by")
            part_index = binding.get("part_index", 0)
            
            # Find element in template
            element = tree.find(f".//*[@id='{element_id}']")
            
            if element is None:
                print(f"Warning: Element '{element_id}' not found in template")
                continue
            
            # Determine the value to use
            if split_by:
                if part_index < len(parts):
                    value = parts[part_index]
                    # First part: trim spaces, others: keep as is
                    if part_index == 0:
                        value = value.strip()
                else:
                    value = ""
            else:
                value = str(raw_value).strip()
            
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
                    # Set the tspan's text (or leave empty)
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
