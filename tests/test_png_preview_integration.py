"""Integration tests for PNG preview generation - requires native Inkscape

These tests require a working Inkscape installation with proper library paths.
They may fail in snap environments due to library conflicts.

To skip integration tests:
    pytest tests/ -v --ignore=tests/test_png_preview_integration.py
    pytest tests/test_png_preview.py  # Unit tests only
    pytest tests/test_png_preview_integration.py  # Integration tests only
"""

import pytest
import tempfile
import os
from pathlib import Path

from card_factory.utils.png_preview import (
    check_inkscape_status,
    svg_to_png,
    generate_preview_directory,
)


def inkscape_works() -> bool:
    """Check if inkscape can actually execute without library errors."""
    return check_inkscape_status().working


def inkscape_skip_reason() -> str:
    """Get a detailed reason for why Inkscape tests are being skipped."""
    status = check_inkscape_status()
    if not status.available:
        return "Inkscape not found in PATH"
    if status.error:
        return f"Inkscape error: {status.error[:80]}"
    return "Inkscape not working"


class TestSvgToPngIntegration:
    """Integration tests for svg_to_png (requires Inkscape)"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.svg_path = os.path.join(self.temp_dir, "test.svg")
        self.png_path = os.path.join(self.temp_dir, "test.png")
        
        with open(self.svg_path, 'w') as f:
            f.write('<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>')

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_converts_valid_svg_to_png(self):
        if not inkscape_works():
            pytest.skip(inkscape_skip_reason())
        success, error = svg_to_png(self.svg_path, self.png_path)
        
        assert success is True
        assert error is None
        assert os.path.exists(self.png_path)

    def test_fails_on_missing_svg(self):
        if not inkscape_works():
            pytest.skip(inkscape_skip_reason())
        success, error = svg_to_png(
            os.path.join(self.temp_dir, "missing.svg"),
            self.png_path
        )
        
        assert success is False
        assert error is not None
        assert 'missing.svg' in error or "doesn't exist" in error

    def test_fails_on_corrupt_svg(self):
        if not inkscape_works():
            pytest.skip(inkscape_skip_reason())
        corrupt_svg = os.path.join(self.temp_dir, "corrupt.svg")
        with open(corrupt_svg, 'w') as f:
            f.write('not valid xml <><><')
        
        success, error = svg_to_png(corrupt_svg, self.png_path)
        
        assert success is False
        assert error is not None

    def test_respects_width_parameter(self):
        if not inkscape_works():
            pytest.skip(inkscape_skip_reason())
        success, error = svg_to_png(self.svg_path, self.png_path, width=200)
        
        assert success is True
        assert os.path.exists(self.png_path)


class TestGeneratePreviewDirectoryIntegration:
    """Integration tests for generate_preview_directory (requires Inkscape)"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.preview_dir = Path(self.temp_dir) / "preview"
        
        self.valid_svg = Path(self.temp_dir) / "valid.svg"
        with open(self.valid_svg, 'w') as f:
            f.write('<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect/></svg>')

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generates_preview_for_valid_files(self):
        if not inkscape_works():
            pytest.skip(inkscape_skip_reason())
        success, failed = generate_preview_directory(
            [str(self.valid_svg)],
            self.preview_dir
        )
        
        assert len(success) == 1
        assert len(failed) == 0
        assert (self.preview_dir / "valid.png").exists()

    def test_reports_missing_files(self):
        if not inkscape_works():
            pytest.skip(inkscape_skip_reason())
        success, failed = generate_preview_directory(
            [str(self.valid_svg), "missing.svg"],
            self.preview_dir
        )
        
        assert len(success) == 1
        assert len(failed) == 1
        assert failed[0][0] == "missing.svg"
        assert failed[0][1] is not None
