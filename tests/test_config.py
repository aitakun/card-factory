"""Tests for config loading"""

import pytest
import sys
import os
import tempfile
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from card_factory.config.loader import CardFactoryConfig


class TestCardFactoryConfig:
    """Tests for CardFactoryConfig class"""

    def test_default_values(self):
        config = CardFactoryConfig()
        assert config.template_default == "template/hardware.svg"
        assert config.output_directory == "export"
        assert config.filename_pattern == "{name}.svg"
        assert config.bindings == []
        assert config.visibility == []
        assert config.color_schemes == {}

    def test_load_minimal_config(self):
        config_content = """
template: template/test.svg
output: export/test
bindings: []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()
            config = CardFactoryConfig(f.name)

        assert config.template_default == "template/test.svg"
        assert config.output_directory == "export/test"
        os.unlink(f.name)

    def test_load_full_config(self):
        config_content = """
template:
  default: template/custom.svg
  pattern: "template/{faction}.svg"

filter:
  column: type
  contains: weapon|armor

bindings:
  - element_id: title
    value: "{name}"
  - element_id: cost
    value: "{cost}"
    prefix: "Cost: "

visibility:
  - element_id: elite_badge
    condition: rarity==elite

color_schemes:
  lookup_column: faction
  schemes:
    criminal:
      primary-color: "#ff0000"

output:
  directory: custom_export
  filename_pattern: "{faction}_{name}.svg"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()
            config = CardFactoryConfig(f.name)

        assert config.template_default == "template/custom.svg"
        assert config.template_pattern == "template/{faction}.svg"
        assert config.filter_column == "type"
        assert config.filter_contains == "weapon|armor"
        assert len(config.bindings) == 2
        assert config.bindings[0]["element_id"] == "title"
        assert config.bindings[1]["prefix"] == "Cost: "
        assert len(config.visibility) == 1
        assert config.visibility[0]["condition"] == "rarity==elite"
        assert config.color_schemes["lookup_column"] == "faction"
        assert config.output_directory == "custom_export"
        assert config.filename_pattern == "{faction}_{name}.svg"
        os.unlink(f.name)

    def test_get_bindings(self):
        config = CardFactoryConfig()
        config.bindings = [{"element_id": "test"}]
        assert config.get_bindings() == [{"element_id": "test"}]

    def test_get_visibility(self):
        config = CardFactoryConfig()
        config.visibility = [{"element_id": "test", "condition": "x==1"}]
        assert config.get_visibility() == [{"element_id": "test", "condition": "x==1"}]

    def test_get_color_schemes(self):
        config = CardFactoryConfig()
        config.color_schemes = {"lookup_column": "faction", "schemes": {}}
        assert config.get_color_schemes() == {"lookup_column": "faction", "schemes": {}}

    def test_get_filter(self):
        config = CardFactoryConfig()
        config.filter_column = "type"
        config.filter_contains = "weapon"
        assert config.get_filter() == ("type", "weapon")

    def test_get_substitutions(self):
        config = CardFactoryConfig()
        config.substitutions = {"[symbol]": "☆☆", "[star]": "★"}
        assert config.get_substitutions() == {"[symbol]": "☆☆", "[star]": "★"}

    def test_load_substitutions_from_config(self):
        config_content = """
template: template/test.svg
substitutions:
  "[symbol]": "☆☆"
  "[star]": "★"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()
            config = CardFactoryConfig(f.name)

        assert config.get_substitutions() == {"[symbol]": "☆☆", "[star]": "★"}
        os.unlink(f.name)


class TestShouldIncludeRow:
    """Tests for should_include_row() method"""

    def test_no_filter(self):
        config = CardFactoryConfig()
        config.filter_column = None
        config.filter_contains = None
        assert config.should_include_row({}) is True

    def test_filter_matches(self):
        config = CardFactoryConfig()
        config.filter_column = "type"
        config.filter_contains = "weapon"
        row = {"type": "sword weapon"}
        assert config.should_include_row(row) is True

    def test_filter_no_match(self):
        config = CardFactoryConfig()
        config.filter_column = "type"
        config.filter_contains = "weapon"
        row = {"type": "armor"}
        assert config.should_include_row(row) is False

    def test_filter_with_or_operator(self):
        config = CardFactoryConfig()
        config.filter_column = "type"
        config.filter_contains = "weapon|armor"
        row_weapon = {"type": "weapon"}
        row_armor = {"type": "armor"}
        row_other = {"type": "potion"}
        assert config.should_include_row(row_weapon) is True
        assert config.should_include_row(row_armor) is True
        assert config.should_include_row(row_other) is False

    def test_filter_case_insensitive(self):
        config = CardFactoryConfig()
        config.filter_column = "type"
        config.filter_contains = "weapon"
        row = {"type": "SWORD WEAPON"}
        assert config.should_include_row(row) is True

    def test_filter_missing_column(self):
        config = CardFactoryConfig()
        config.filter_column = "type"
        config.filter_contains = "weapon"
        row = {"name": "Sword"}
        assert config.should_include_row(row) is False


class TestSpreadsheetCleanup:
    """Tests for spreadsheet cleanup setting"""

    def test_default_cleanup_true(self):
        config = CardFactoryConfig()
        assert config.spreadsheet_cleanup is True
        assert config.should_cleanup_spreadsheet() is True

    def test_load_cleanup_true(self):
        config_content = """
spreadsheet:
  cleanup: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()
            config = CardFactoryConfig(f.name)

        assert config.spreadsheet_cleanup is True
        assert config.should_cleanup_spreadsheet() is True
        os.unlink(f.name)

    def test_load_cleanup_false(self):
        config_content = """
spreadsheet:
  cleanup: false
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()
            config = CardFactoryConfig(f.name)
        
        assert config.spreadsheet_cleanup is False
        assert config.should_cleanup_spreadsheet() is False
        os.unlink(f.name)


class TestSmallFontSize:
    """Tests for small_font_size configuration"""

    def test_default_small_font_size(self):
        config = CardFactoryConfig()
        assert config.small_font_size == 28

    def test_get_small_font_size(self):
        config = CardFactoryConfig()
        config.small_font_size = 24
        assert config.get_small_font_size() == 24

    def test_load_small_font_size_from_config(self):
        config_content = """
formatting:
  small_font_size: 20
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()
            config = CardFactoryConfig(f.name)
        
        assert config.small_font_size == 20
        assert config.get_small_font_size() == 20
        os.unlink(f.name)

    def test_load_small_font_size_with_other_settings(self):
        config_content = """
formatting:
  small_font_size: 32

bindings:
  - element_id: test
    value: "{name}"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()
            config = CardFactoryConfig(f.name)
        
        assert config.small_font_size == 32
        assert len(config.bindings) == 1
        os.unlink(f.name)
