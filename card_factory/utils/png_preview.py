"""PNG preview generation using Inkscape"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional


@dataclass
class InkscapeStatus:
    """Status result from checking Inkscape availability."""
    available: bool
    path: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None

    @property
    def working(self) -> bool:
        """True if Inkscape is available and can execute."""
        return self.available and self.version is not None


def check_inkscape_available() -> bool:
    """Check if inkscape is available in PATH.
    
    Note: This only checks PATH. For full status including execution test,
    use check_inkscape_status() instead.
    """
    return shutil.which("inkscape") is not None


def check_inkscape_status() -> InkscapeStatus:
    """Check Inkscape availability with full execution test.
    
    Performs a real execution check to verify Inkscape actually works,
    not just that it's in PATH. This catches issues like snap library
    conflicts where inkscape is found but fails to execute.
    
    Returns:
        InkscapeStatus with detailed information about Inkscape availability
    """
    path = shutil.which("inkscape")
    
    if path is None:
        return InkscapeStatus(
            available=False,
            error="Inkscape not found in PATH. Install with: apt install inkscape"
        )
    
    try:
        result = subprocess.run(
            ["inkscape", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        stderr = result.stderr.strip() if result.stderr else ""
        
        if "undefined symbol" in stderr or "symbol lookup error" in stderr:
            return InkscapeStatus(
                available=True,
                path=path,
                error=stderr,
                version=None
            )
        
        if result.returncode != 0:
            error_msg = stderr if stderr else f"Exit code {result.returncode}"
            return InkscapeStatus(
                available=True,
                path=path,
                error=f"Execution failed: {error_msg}",
                version=None
            )
        
        version = result.stdout.strip().split('\n')[0] if result.stdout else None
        
        return InkscapeStatus(
            available=True,
            path=path,
            version=version
        )
        
    except subprocess.TimeoutExpired:
        return InkscapeStatus(
            available=True,
            path=path,
            error="Timeout waiting for Inkscape to respond"
        )
    except Exception as e:
        return InkscapeStatus(
            available=True,
            path=path,
            error=str(e)
        )


def svg_to_png(svg_path: str, output_path: str, width: int = None) -> Tuple[bool, Optional[str]]:
    """Convert an SVG file to PNG using Inkscape.
    
    Args:
        svg_path: Path to the input SVG file
        output_path: Path for the output PNG file
        width: Optional width in pixels for the output
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
        error_message is None on success, or contains stderr on failure
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
        
        if result.returncode != 0:
            return False, result.stderr or f"Inkscape failed with exit code {result.returncode}"
        
        if not Path(output_path).exists():
            return False, result.stderr or "PNG file was not created"
        
        return True, None
    except FileNotFoundError:
        return False, "Inkscape not found. Is it installed and in PATH?"
    except PermissionError:
        return False, f"Permission denied: cannot write to {output_path}"
    except Exception as e:
        return False, str(e)


def generate_preview_directory(
    svg_files: List[str],
    preview_dir: Path,
    width: int = None
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Generate PNG previews for all SVG files in a directory.
    
    Args:
        svg_files: List of SVG file paths
        preview_dir: Directory to save PNG files
        width: Optional width in pixels for output
        
    Returns:
        Tuple of (successful_paths, failed_with_errors)
        where failed_with_errors is a list of (svg_path, error_message) tuples
    """
    preview_dir.mkdir(parents=True, exist_ok=True)
    
    successful = []
    failed = []
    
    for svg_path in svg_files:
        svg_path_obj = Path(svg_path)
        png_filename = svg_path_obj.with_suffix(".png").name
        png_path = preview_dir / png_filename
        
        success, error = svg_to_png(str(svg_path_obj), str(png_path), width)
        if success:
            successful.append(str(png_path))
        else:
            failed.append((svg_path, error))
    
    return successful, failed
