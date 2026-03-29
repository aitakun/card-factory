"""Tests for PNG preview generation utilities - Unit Tests

This module contains unit tests that mock external dependencies.
For integration tests that require a working Inkscape installation,
see test_png_preview_integration.py.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from card_factory.utils.png_preview import (
    check_inkscape_available,
    check_inkscape_status,
    svg_to_png,
    generate_preview_directory,
)


class TestCheckInkscapeAvailable:
    """Tests for check_inkscape_available()"""

    def test_returns_boolean(self):
        result = check_inkscape_available()
        assert isinstance(result, bool)

    @patch('card_factory.utils.png_preview.shutil.which')
    def test_returns_true_when_found(self, mock_which):
        mock_which.return_value = '/usr/bin/inkscape'
        assert check_inkscape_available() is True

    @patch('card_factory.utils.png_preview.shutil.which')
    def test_returns_false_when_not_found(self, mock_which):
        mock_which.return_value = None
        assert check_inkscape_available() is False


class TestCheckInkscapeStatus:
    """Tests for check_inkscape_status()"""

    @patch('card_factory.utils.png_preview.shutil.which')
    def test_not_found_in_path(self, mock_which):
        mock_which.return_value = None
        
        status = check_inkscape_status()
        
        assert status.available is False
        assert status.path is None
        assert status.version is None
        assert status.working is False
        assert "not found" in status.error.lower()

    @patch('card_factory.utils.png_preview.subprocess.run')
    @patch('card_factory.utils.png_preview.shutil.which')
    def test_working(self, mock_which, mock_run):
        mock_which.return_value = '/usr/bin/inkscape'
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='Inkscape 1.3\n',
            stderr=''
        )
        
        status = check_inkscape_status()
        
        assert status.available is True
        assert status.path == '/usr/bin/inkscape'
        assert status.version == 'Inkscape 1.3'
        assert status.working is True
        assert status.error is None

    @patch('card_factory.utils.png_preview.subprocess.run')
    @patch('card_factory.utils.png_preview.shutil.which')
    def test_library_error(self, mock_which, mock_run):
        mock_which.return_value = '/usr/bin/inkscape'
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='',
            stderr='inkscape: symbol lookup error: ...undefined symbol...'
        )
        
        status = check_inkscape_status()
        
        assert status.available is True
        assert status.path == '/usr/bin/inkscape'
        assert status.version is None
        assert status.working is False
        assert "undefined symbol" in status.error

    @patch('card_factory.utils.png_preview.subprocess.run')
    @patch('card_factory.utils.png_preview.shutil.which')
    def test_nonzero_exit_code(self, mock_which, mock_run):
        mock_which.return_value = '/usr/bin/inkscape'
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='Some error'
        )
        
        status = check_inkscape_status()
        
        assert status.available is True
        assert status.working is False
        assert status.error is not None


class TestSvgToPng:
    """Tests for svg_to_png()"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.valid_svg = os.path.join(self.temp_dir, "valid.svg")
        self.valid_png = os.path.join(self.temp_dir, "valid.png")
        self.invalid_svg = os.path.join(self.temp_dir, "invalid.svg")
        self.output_png = os.path.join(self.temp_dir, "output.png")
        
        with open(self.valid_svg, 'w') as f:
            f.write('<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>')

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('card_factory.utils.png_preview.subprocess.run')
    @patch('card_factory.utils.png_preview.Path')
    def test_returns_true_on_success(self, mock_path, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr='')
        mock_path.return_value.exists.return_value = True
        
        success, error = svg_to_png(self.valid_svg, self.output_png)
        
        assert success is True
        assert error is None

    @patch('card_factory.utils.png_preview.subprocess.run')
    def test_returns_error_on_nonzero_exit(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr='Error: failed')
        
        success, error = svg_to_png(self.valid_svg, self.output_png)
        
        assert success is False
        assert error == 'Error: failed'

    @patch('card_factory.utils.png_preview.subprocess.run')
    def test_returns_error_when_png_not_created(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr='')
        
        success, error = svg_to_png(self.valid_svg, self.output_png)
        
        assert success is False
        assert 'not created' in error.lower()

    @patch('card_factory.utils.png_preview.subprocess.run')
    def test_success_with_width_parameter(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr='')
        
        with patch('card_factory.utils.png_preview.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            success, error = svg_to_png(self.valid_svg, self.output_png, width=800)
            
            assert success is True
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert '--export-width' in args
            assert '800' in args

    @patch('card_factory.utils.png_preview.subprocess.run')
    def test_handles_missing_file_error(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr="Can't open file: missing.svg (doesn't exist)"
        )
        
        success, error = svg_to_png('missing.svg', self.output_png)
        
        assert success is False
        assert 'missing.svg' in error

    @patch('card_factory.utils.png_preview.subprocess.run')
    def test_handles_corrupt_svg(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr='SVG parsing error: Invalid XML'
        )
        
        success, error = svg_to_png(self.invalid_svg, self.output_png)
        
        assert success is False

    @patch('card_factory.utils.png_preview.subprocess.run')
    def test_handles_inkscape_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        
        success, error = svg_to_png(self.valid_svg, self.output_png)
        
        assert success is False
        assert 'inkscape' in error.lower()
        assert 'not found' in error.lower()


class TestGeneratePreviewDirectory:
    """Tests for generate_preview_directory()"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.preview_dir = os.path.join(self.temp_dir, "preview")
        self.svg1 = os.path.join(self.temp_dir, "test1.svg")
        self.svg2 = os.path.join(self.temp_dir, "test2.svg")
        
        with open(self.svg1, 'w') as f:
            f.write('<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>')
        with open(self.svg2, 'w') as f:
            f.write('<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>')

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('card_factory.utils.png_preview.svg_to_png')
    def test_returns_successful_files(self, mock_svg_to_png):
        mock_svg_to_png.return_value = (True, None)
        
        success, failed = generate_preview_directory(
            [self.svg1, self.svg2],
            Path(self.preview_dir)
        )
        
        assert len(success) == 2
        assert len(failed) == 0

    @patch('card_factory.utils.png_preview.svg_to_png')
    def test_returns_failed_with_errors(self, mock_svg_to_png):
        mock_svg_to_png.return_value = (False, 'Inkscape error: test failure')
        
        success, failed = generate_preview_directory(
            [self.svg1, self.svg2],
            Path(self.preview_dir)
        )
        
        assert len(success) == 0
        assert len(failed) == 2
        assert all(isinstance(f, tuple) and len(f) == 2 for f in failed)
        assert all('test failure' in err for _, err in failed)

    @patch('card_factory.utils.png_preview.svg_to_png')
    def test_handles_mixed_results(self, mock_svg_to_png):
        mock_svg_to_png.side_effect = [
            (True, None),
            (False, 'File not found'),
            (True, None),
        ]
        
        success, failed = generate_preview_directory(
            [self.svg1, 'missing.svg', self.svg2],
            Path(self.preview_dir)
        )
        
        assert len(success) == 2
        assert len(failed) == 1
        assert failed[0][0] == 'missing.svg'
        assert 'File not found' in failed[0][1]

    @patch('card_factory.utils.png_preview.svg_to_png')
    def test_creates_preview_directory(self, mock_svg_to_png):
        mock_svg_to_png.return_value = (True, None)
        
        generate_preview_directory(
            [self.svg1],
            Path(self.preview_dir)
        )
        
        assert os.path.isdir(self.preview_dir)

    @patch('card_factory.utils.png_preview.svg_to_png')
    def test_preserves_svg_filename_in_png(self, mock_svg_to_png):
        mock_svg_to_png.return_value = (True, None)
        
        success, _ = generate_preview_directory(
            [self.svg1],
            Path(self.preview_dir)
        )
        
        assert 'test1.png' in success[0]
