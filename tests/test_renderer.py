"""Tests for renderer functions"""

import pytest
import sys
import os
from lxml import etree
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from card_factory.templates.renderer import (
    parse_markdown_segments,
    resolve_template_value,
    resolve_url_template,
    evaluate_condition,
    apply_formatted_text,
)


class TestParseMarkdownSegments:
    """Tests for parse_markdown_segments()"""

    def test_plain_text(self):
        result = parse_markdown_segments("Hello World")
        assert len(result) == 1
        assert result[0]["text"] == "Hello World"
        assert result[0]["format"] is None

    def test_empty_string(self):
        result = parse_markdown_segments("")
        assert result == []

    def test_bold_simple(self):
        result = parse_markdown_segments("*bold text*")
        assert len(result) == 1
        assert result[0]["text"] == "bold text"
        assert result[0]["format"] == "bold"

    def test_heavy_simple(self):
        result = parse_markdown_segments("!heavy text!")
        assert len(result) == 1
        assert result[0]["text"] == "heavy text"
        assert result[0]["format"] == "heavy"

    def test_italic_simple(self):
        result = parse_markdown_segments("_italic text_")
        assert len(result) == 1
        assert result[0]["text"] == "italic text"
        assert result[0]["format"] == "italic"

    def test_mixed_plain_and_formatted(self):
        result = parse_markdown_segments("Hello *bold* World")
        assert len(result) == 3
        assert result[0]["text"] == "Hello "
        assert result[0]["format"] is None
        assert result[1]["text"] == "bold"
        assert result[1]["format"] == "bold"
        assert result[2]["text"] == " World"
        assert result[2]["format"] is None

    def test_nested_bold_with_italic(self):
        result = parse_markdown_segments("*bold _with italic_*")
        assert len(result) == 1
        assert result[0]["format"] == "bold"
        assert len(result[0]["content"]) == 2
        assert result[0]["content"][0]["text"] == "bold "
        assert result[0]["content"][0]["format"] is None
        assert result[0]["content"][1]["text"] == "with italic"
        assert result[0]["content"][1]["format"] == "italic"

    def test_nested_bold_with_heavy(self):
        result = parse_markdown_segments("*bold !with heavy!*")
        assert len(result) == 1
        assert result[0]["format"] == "bold"
        assert len(result[0]["content"]) == 2

    def test_multiple_bolds(self):
        result = parse_markdown_segments("*one* and *two*")
        assert len(result) == 3
        assert result[0]["format"] == "bold"
        assert result[0]["text"] == "one"
        assert result[2]["format"] == "bold"
        assert result[2]["text"] == "two"

    def test_multiple_formats_mixed(self):
        result = parse_markdown_segments("*bold* and _italic_ and !heavy!")
        assert len(result) == 5
        assert result[0]["format"] == "bold"
        assert result[2]["format"] == "italic"
        assert result[4]["format"] == "heavy"

    def test_adjacent_formats(self):
        result = parse_markdown_segments("*bold*_italic_")
        assert len(result) == 2
        assert result[0]["format"] == "bold"
        assert result[1]["format"] == "italic"

    def test_empty_format_markers(self):
        result = parse_markdown_segments("****")
        assert len(result) == 2
        assert result[0]["text"] == ""
        assert result[0]["format"] == "bold"
        assert result[1]["text"] == ""
        assert result[1]["format"] == "bold"

    def test_unclosed_marker(self):
        result = parse_markdown_segments("*unclosed")
        assert len(result) == 1
        assert result[0]["text"] == "*unclosed"
        assert result[0]["format"] is None


class TestResolveTemplateValue:
    """Tests for resolve_template_value()"""

    def test_simple_field(self):
        row_data = {"name": "Sword", "cost": "5"}
        result = resolve_template_value("{name}", row_data, "test_element")
        assert result == "Sword"

    def test_field_with_braces(self):
        row_data = {"name": "Sword", "cost": "5"}
        result = resolve_template_value("{name}", row_data, "test_element")
        assert result == "Sword"

    def test_concatenation(self):
        row_data = {"first": "Hello", "last": "World"}
        result = resolve_template_value("{first} {last}", row_data, "test_element")
        assert result == "Hello World"

    def test_uppercase_transform(self):
        row_data = {"name": "hello"}
        result = resolve_template_value("[uppercase]{name}[/uppercase]", row_data, "test_element")
        assert result == "HELLO"

    def test_lowercase_transform(self):
        row_data = {"name": "HELLO"}
        result = resolve_template_value("[lowercase]{name}[/lowercase]", row_data, "test_element")
        assert result == "hello"

    def test_missing_field(self):
        row_data = {"name": "Sword"}
        result = resolve_template_value("{missing}", row_data, "test_element")
        assert result == ""

    def test_empty_field_removes_surrounding(self):
        row_data = {"desc": ""}
        result = resolve_template_value("**{desc}**", row_data, "test_element")
        assert result == ""

    def test_text_preserved_without_fields(self):
        row_data = {"name": "Sword"}
        result = resolve_template_value("Static Text", row_data, "test_element")
        assert result == "Static Text"


class TestResolveUrlTemplate:
    """Tests for resolve_url_template()"""

    def test_url_without_placeholders(self):
        row_data = {"name": "Sword"}
        result = resolve_url_template("https://example.com/image.png", row_data, "test_element")
        assert result == "https://example.com/image.png"

    def test_url_with_field(self):
        row_data = {"name": "sword"}
        result = resolve_url_template("https://example.com/{name}.png", row_data, "test_element")
        assert result == "https://example.com/sword.png"

    def test_url_with_uppercase(self):
        row_data = {"name": "sword"}
        result = resolve_url_template("https://example.com/[uppercase]{name}.png", row_data, "test_element")
        assert result == "https://example.com/SWORD.png"

    def test_url_with_lowercase(self):
        row_data = {"name": "SWORD"}
        result = resolve_url_template("https://example.com/[lowercase]{name}.png", row_data, "test_element")
        assert result == "https://example.com/sword.png"

    def test_empty_url(self):
        row_data = {"name": "Sword"}
        result = resolve_url_template("", row_data, "test_element")
        assert result == ""


class TestEvaluateCondition:
    """Tests for evaluate_condition()"""

    def test_empty_condition(self):
        result = evaluate_condition("", {})
        assert result is True

    def test_equals_string_match(self):
        result = evaluate_condition("faction==criminal", {"faction": "criminal"})
        assert result is True

    def test_equals_string_no_match(self):
        result = evaluate_condition("faction==criminal", {"faction": "neutral"})
        assert result is False

    def test_equals_numeric(self):
        result = evaluate_condition("cost==5", {"cost": "5"})
        assert result is True

    def test_greater_than(self):
        result = evaluate_condition("cost>3", {"cost": "5"})
        assert result is True

    def test_greater_than_false(self):
        result = evaluate_condition("cost>5", {"cost": "3"})
        assert result is False

    def test_less_than(self):
        result = evaluate_condition("cost<10", {"cost": "5"})
        assert result is True

    def test_greater_than_or_equal(self):
        result = evaluate_condition("cost>=5", {"cost": "5"})
        assert result is True

    def test_less_than_or_equal(self):
        result = evaluate_condition("cost<=5", {"cost": "5"})
        assert result is True

    def test_numeric_with_float(self):
        result = evaluate_condition("cost>=3.5", {"cost": "4.2"})
        assert result is True

    def test_empty_value_with_greater_than(self):
        result = evaluate_condition("cost>5", {"cost": ""})
        assert result is False

    def test_non_numeric_with_greater_than(self):
        result = evaluate_condition("cost>5", {"cost": "abc"})
        assert result is False

    def test_invalid_condition_format(self):
        result = evaluate_condition("invalid", {})
        assert result is True

    def test_equals_with_numeric_0(self):
        result = evaluate_condition("amount==0", {"amount": "0"})
        assert result is True


class TestApplyFormattedText:
    """Tests for apply_formatted_text()"""

    def test_plain_text_on_text_element(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test">Original</text></svg>')
        text_element = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text(text_element, "New Text")
        tspan = svg.find(".//{http://www.w3.org/2000/svg}tspan")
        assert tspan is not None
        assert tspan.text == "New Text"

    def test_plain_text_on_tspan_element(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan id="inner">Original</tspan></text></svg>')
        tspan = svg.find(".//{http://www.w3.org/2000/svg}tspan")
        apply_formatted_text(tspan, "New Text")
        assert tspan.text == "New Text"
