"""PNG preview generation using Inkscape"""

import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple


def check_inkscape_available() -> bool:
    """Check if inkscape is available in PATH"""
    return shutil.which("inkscape") is not None


def svg_to_png(svg_path: str, output_path: str, width: int = None) -> bool:
    """Convert an SVG file to PNG using Inkscape.
    
    Args:
        svg_path: Path to the input SVG file
        output_path: Path for the output PNG file
        width: Optional width in pixels for the output
        
    Returns:
        True if conversion succeeded, False otherwise
    """
    try:
        cmd = ["inkscape", str(svg_path), "--export-filename", str(output_path)]
        if width:
            cmd.extend(["--export-width", str(width)])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        return result.returncode == 0
    except Exception:
        return False


def generate_preview_directory(
    svg_files: List[str],
    preview_dir: Path,
    width: int = None
) -> Tuple[List[str], List[str]]:
    """Generate PNG previews for all SVG files in a directory.
    
    Args:
        svg_files: List of SVG file paths
        preview_dir: Directory to save PNG files
        width: Optional width in pixels for output
        
    Returns:
        Tuple of (successful_paths, failed_paths)
    """
    preview_dir.mkdir(parents=True, exist_ok=True)
    
    successful = []
    failed = []
    
    for svg_path in svg_files:
        svg_path_obj = Path(svg_path)
        png_filename = svg_path_obj.with_suffix(".png").name
        png_path = preview_dir / png_filename
        
        if svg_to_png(str(svg_path_obj), str(png_path), width):
            successful.append(str(png_path))
        else:
            failed.append(svg_path)
    
    return successful, failed
