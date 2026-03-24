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
    apply_markdown_within_tspan,
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

    def test_bold_resumes_after_nested_heavy(self):
        result = parse_markdown_segments("*bold !heavy! bold again*")
        assert len(result) == 1
        assert result[0]["format"] == "bold"
        assert len(result[0]["content"]) == 3
        assert result[0]["content"][0]["text"] == "bold "
        assert result[0]["content"][0]["format"] is None
        assert result[0]["content"][1]["text"] == "heavy"
        assert result[0]["content"][1]["format"] == "heavy"
        assert result[0]["content"][2]["text"] == " bold again"
        assert result[0]["content"][2]["format"] is None

    def test_italic_with_bold_inside(self):
        result = parse_markdown_segments("_italic *bold italic* plain_")
        assert len(result) == 1
        assert result[0]["format"] == "italic"
        assert len(result[0]["content"]) == 3
        assert result[0]["content"][0]["text"] == "italic "
        assert result[0]["content"][0]["format"] is None
        assert result[0]["content"][1]["text"] == "bold italic"
        assert result[0]["content"][1]["format"] == "bold"
        assert result[0]["content"][2]["text"] == " plain"
        assert result[0]["content"][2]["format"] is None

    def test_heavy_with_bold_inside(self):
        result = parse_markdown_segments("!heavy *bold heavy* plain!")
        assert len(result) == 1
        assert result[0]["format"] == "heavy"
        assert len(result[0]["content"]) == 3
        assert result[0]["content"][0]["text"] == "heavy "
        assert result[0]["content"][0]["format"] is None
        assert result[0]["content"][1]["text"] == "bold heavy"
        assert result[0]["content"][1]["format"] == "bold"
        assert result[0]["content"][2]["text"] == " plain"
        assert result[0]["content"][2]["format"] is None

    def test_plain_surrounding_nested_format(self):
        result = parse_markdown_segments("before *bold _italic_ bold* after")
        assert len(result) == 3
        assert result[0]["text"] == "before "
        assert result[0]["format"] is None
        assert result[1]["format"] == "bold"
        assert len(result[1]["content"]) == 3
        assert result[1]["content"][0]["text"] == "bold "
        assert result[1]["content"][1]["text"] == "italic"
        assert result[1]["content"][1]["format"] == "italic"
        assert result[1]["content"][2]["text"] == " bold"
        assert result[2]["text"] == " after"
        assert result[2]["format"] is None

    def test_multiple_alternating_nested_in_bold(self):
        result = parse_markdown_segments("*!heavy! and _italic_ and !heavy! and _italic_*")
        assert len(result) == 1
        assert result[0]["format"] == "bold"
        assert len(result[0]["content"]) == 7
        assert result[0]["content"][0]["text"] == "heavy"
        assert result[0]["content"][0]["format"] == "heavy"
        assert result[0]["content"][1]["text"] == " and "
        assert result[0]["content"][1]["format"] is None
        assert result[0]["content"][2]["text"] == "italic"
        assert result[0]["content"][2]["format"] == "italic"
        assert result[0]["content"][3]["text"] == " and "
        assert result[0]["content"][3]["format"] is None
        assert result[0]["content"][4]["text"] == "heavy"
        assert result[0]["content"][4]["format"] == "heavy"
        assert result[0]["content"][5]["text"] == " and "
        assert result[0]["content"][5]["format"] is None
        assert result[0]["content"][6]["text"] == "italic"
        assert result[0]["content"][6]["format"] == "italic"

    def test_triple_nesting_bold_italic_heavy(self):
        result = parse_markdown_segments("*bold _italic !heavy! italic_ bold*")
        assert len(result) == 1
        assert result[0]["format"] == "bold"
        assert len(result[0]["content"]) == 3
        assert result[0]["content"][0]["text"] == "bold "
        assert result[0]["content"][1]["format"] == "italic"
        assert len(result[0]["content"][1]["content"]) == 3
        assert result[0]["content"][1]["content"][0]["text"] == "italic "
        assert result[0]["content"][1]["content"][0]["format"] is None
        assert result[0]["content"][1]["content"][1]["text"] == "heavy"
        assert result[0]["content"][1]["content"][1]["format"] == "heavy"
        assert result[0]["content"][1]["content"][2]["text"] == " italic"
        assert result[0]["content"][1]["content"][2]["format"] is None
        assert result[0]["content"][2]["text"] == " bold"
        assert result[0]["content"][2]["format"] is None

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

    def test_simple_substitution(self):
        row_data = {"column_1": "baz"}
        substitutions = {"[symbol]": "☆☆"}
        result = resolve_template_value("{column_1} [symbol]", row_data, "test_element", substitutions)
        assert result == "baz ☆☆"

    def test_substitution_in_column_value(self):
        row_data = {"column_1": "baz [symbol] bar"}
        substitutions = {"[symbol]": "☆☆"}
        result = resolve_template_value("{column_1}", row_data, "test_element", substitutions)
        assert result == "baz ☆☆ bar"

    def test_multiple_substitutions(self):
        row_data = {"name": "test"}
        substitutions = {"[star]": "★", "[heart]": "♥"}
        result = resolve_template_value("{name} [star] and [heart]", row_data, "test_element", substitutions)
        assert result == "test ★ and ♥"

    def test_substitution_before_markdown(self):
        row_data = {"text": "value"}
        substitutions = {"[symbol]": "☆☆"}
        result = resolve_template_value("*{text} [symbol]*", row_data, "test_element", substitutions)
        assert result == "*value ☆☆*"

    def test_substitution_before_uppercase(self):
        row_data = {"name": "test"}
        substitutions = {"[suffix]": " [suffix]", "[suffix]": " SUFFIX"}
        result = resolve_template_value("{name}[suffix]", row_data, "test_element", substitutions)
        assert result == "test SUFFIX"

    def test_substitution_before_lowercase(self):
        row_data = {"name": "TEST"}
        substitutions = {"[suffix]": " [suffix]", "[suffix]": " suffix"}
        result = resolve_template_value("[lowercase]{name}[/lowercase][suffix]", row_data, "test_element", substitutions)
        assert result == "test suffix"

    def test_no_substitutions(self):
        row_data = {"name": "Sword"}
        result = resolve_template_value("{name}", row_data, "test_element")
        assert result == "Sword"

    def test_substitution_not_found(self):
        row_data = {"name": "Sword"}
        substitutions = {"[other]": "☆"}
        result = resolve_template_value("{name} [symbol]", row_data, "test_element", substitutions)
        assert result == "Sword [symbol]"


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

    def test_bold_creates_nested_tspan(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan id="inner">Original</tspan></text></svg>')
        tspan = svg.find(".//{http://www.w3.org/2000/svg}tspan")
        apply_markdown_within_tspan(tspan, "*bold text*")
        all_tspans = svg.findall(".//{http://www.w3.org/2000/svg}tspan")
        assert len(all_tspans) == 2
        parent = all_tspans[0]
        nested = all_tspans[1]
        assert parent.get("id") == "inner"
        assert nested.get("font-weight") == "bold"
        assert nested.text == "bold text"

    def test_italic_creates_nested_tspan(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan id="inner">Original</tspan></text></svg>')
        tspan = svg.find(".//{http://www.w3.org/2000/svg}tspan")
        apply_markdown_within_tspan(tspan, "_italic text_")
        all_tspans = svg.findall(".//{http://www.w3.org/2000/svg}tspan")
        assert len(all_tspans) == 2
        nested = all_tspans[1]
        assert nested.get("font-style") == "italic"
        assert nested.text == "italic text"

    def test_heavy_creates_nested_tspan(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan id="inner">Original</tspan></text></svg>')
        tspan = svg.find(".//{http://www.w3.org/2000/svg}tspan")
        apply_markdown_within_tspan(tspan, "!heavy text!")
        all_tspans = svg.findall(".//{http://www.w3.org/2000/svg}tspan")
        assert len(all_tspans) == 2
        nested = all_tspans[1]
        assert nested.get("font-weight") == "900"
        assert nested.text == "heavy text"

    def test_plain_text_replaces_parent_text(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan id="inner">Original</tspan></text></svg>')
        tspan = svg.find(".//{http://www.w3.org/2000/svg}tspan")
        apply_markdown_within_tspan(tspan, "plain text")
        all_tspans = svg.findall(".//{http://www.w3.org/2000/svg}tspan")
        assert len(all_tspans) == 1
        assert all_tspans[0].text == "plain text"
        assert all_tspans[0].get("font-weight") is None
        assert all_tspans[0].get("font-style") is None

    def test_nested_bold_with_italic_creates_deep_hierarchy(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan id="inner">Original</tspan></text></svg>')
        tspan = svg.find(".//{http://www.w3.org/2000/svg}tspan")
        apply_markdown_within_tspan(tspan, "*bold _italic_*")
        all_tspans = svg.findall(".//{http://www.w3.org/2000/svg}tspan")
        assert len(all_tspans) == 4
        assert all_tspans[1].get("font-weight") == "bold"
        assert all_tspans[3].get("font-style") == "italic"

    def test_multiple_formats_creates_sibling_tspans(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan id="inner">Original</tspan></text></svg>')
        tspan = svg.find(".//{http://www.w3.org/2000/svg}tspan")
        apply_markdown_within_tspan(tspan, "*bold* and _italic_ and !heavy!")
        all_tspans = svg.findall(".//{http://www.w3.org/2000/svg}tspan")
        assert len(all_tspans) == 6
        assert all_tspans[1].get("font-weight") == "bold"
        assert all_tspans[3].get("font-style") == "italic"
        assert all_tspans[5].get("font-weight") == "900"

    def test_triple_nesting_creates_deep_hierarchy(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan id="inner">Original</tspan></text></svg>')
        tspan = svg.find(".//{http://www.w3.org/2000/svg}tspan")
        apply_markdown_within_tspan(tspan, "*bold _italic !heavy! italic_ bold*")
        all_tspans = svg.findall(".//{http://www.w3.org/2000/svg}tspan")
        assert len(all_tspans) == 8
        assert all_tspans[1].get("font-weight") == "bold"
        assert all_tspans[3].get("font-style") == "italic"
        assert all_tspans[5].get("font-weight") == "900"

    def test_base_attributes_preserved_on_nested(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan id="inner" font-family="Arial" font-size="12">Original</tspan></text></svg>')
        tspan = svg.find(".//{http://www.w3.org/2000/svg}tspan")
        apply_markdown_within_tspan(tspan, "*bold text*")
        nested = svg.findall(".//{http://www.w3.org/2000/svg}tspan")[1]
        assert nested.get("font-family") == "Arial"
        assert nested.get("font-size") == "12"
        assert nested.get("font-weight") == "bold"

    def test_plain_surrounding_formatted(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan id="inner">Original</tspan></text></svg>')
        tspan = svg.find(".//{http://www.w3.org/2000/svg}tspan")
        apply_markdown_within_tspan(tspan, "before *bold* after")
        all_tspans = svg.findall(".//{http://www.w3.org/2000/svg}tspan")
        assert all_tspans[1].text == "before "
        assert all_tspans[2].get("font-weight") == "bold"
        assert all_tspans[2].text == "bold"
        assert all_tspans[3].text == " after"


class TestApplyFormattedTextIntegration:
    """Integration tests for apply_formatted_text() on text elements"""

    def test_text_element_with_bold(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text(text_elem, "*bold* and plain")
        all_tspans = svg.findall(".//{http://www.w3.org/2000/svg}tspan")
        assert len(all_tspans) == 3
        assert all_tspans[1].get("font-weight") == "bold"
        assert all_tspans[1].text == "bold"
        assert all_tspans[2].text == " and plain"

    def test_text_element_with_nested_formats(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text(text_elem, "*bold _italic_ bold*")
        all_tspans = svg.findall(".//{http://www.w3.org/2000/svg}tspan")
        assert len(all_tspans) == 5
        assert all_tspans[1].get("font-weight") == "bold"
        assert all_tspans[3].get("font-style") == "italic"
        assert all_tspans[3].text == "italic"

    def test_text_element_with_existing_tspan(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan id="inner">Old text</tspan></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text(text_elem, "*new bold*")
        all_tspans = svg.findall(".//{http://www.w3.org/2000/svg}tspan")
        assert len(all_tspans) == 2
        assert all_tspans[1].text == "new bold"
        assert all_tspans[1].get("font-weight") == "bold"

    def test_complex_text_with_all_formats(self):
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text(text_elem, "*bold* and _italic_ and !heavy! and plain")
        all_tspans = svg.findall(".//{http://www.w3.org/2000/svg}tspan")
        assert len(all_tspans) == 7
        assert all_tspans[1].get("font-weight") == "bold"
        assert all_tspans[3].get("font-style") == "italic"
        assert all_tspans[5].get("font-weight") == "900"
        assert all_tspans[6].text == " and plain"


class TestApplyFormattedTextWithParagraphs:
    """Tests for apply_formatted_text_with_paragraphs()"""

    def test_single_paragraph_creates_one_tspan(self):
        from card_factory.templates.renderer import apply_formatted_text_with_paragraphs
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan>Placeholder</tspan></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text_with_paragraphs(text_elem, "Single line", 10)
        children = list(text_elem)
        assert len(children) == 1

    def test_multiple_paragraphs_creates_correct_count(self):
        from card_factory.templates.renderer import apply_formatted_text_with_paragraphs
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan>Placeholder</tspan></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text_with_paragraphs(text_elem, "Line 1\nLine 2\nLine 3", 10)
        children = list(text_elem)
        assert len(children) == 3

    def test_paragraphs_have_correct_indices(self):
        from card_factory.templates.renderer import apply_formatted_text_with_paragraphs
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan>Placeholder</tspan></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text_with_paragraphs(text_elem, "Line 1\nLine 2", 10)
        children = list(text_elem)
        assert children[0].get("data-paragraph-index") == "0"
        assert children[1].get("data-paragraph-index") == "1"

    def test_first_paragraph_visible_others_hidden(self):
        from card_factory.templates.renderer import apply_formatted_text_with_paragraphs
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan>Placeholder</tspan></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text_with_paragraphs(text_elem, "Line 1\nLine 2", 10)
        children = list(text_elem)
        assert children[0].get("fill-opacity") is None
        assert children[1].get("fill-opacity") == "0"

    def test_markdown_preserved_with_paragraphs(self):
        from card_factory.templates.renderer import apply_formatted_text_with_paragraphs
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan>Placeholder</tspan></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text_with_paragraphs(text_elem, "*Bold*\n_Italic_", 10)
        children = list(text_elem)
        assert len(children) == 2
        inner0 = children[0][0]
        assert inner0.get("font-weight") == "bold"
        inner1 = children[1][0]
        assert inner1.get("font-style") == "italic"

    def test_paragraph_wrapper_has_newline_for_spacing(self):
        """Paragraph wrapper tspans should have newline characters for vertical spacing (not on first)."""
        from card_factory.templates.renderer import apply_formatted_text_with_paragraphs
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve"><text id="test"><tspan>Placeholder</tspan></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text_with_paragraphs(text_elem, "Line 1\nLine 2", 10)
        children = list(text_elem)
        # First paragraph should NOT have newline (starts at original position)
        assert children[0].text is None

    def test_three_paragraphs_have_correct_newlines(self):
        """Three paragraphs: first has none, middle has newline, last has none."""
        from card_factory.templates.renderer import apply_formatted_text_with_paragraphs
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve"><text id="test"><tspan>Placeholder</tspan></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text_with_paragraphs(text_elem, "A\nB\nC", 10)
        children = list(text_elem)
        assert len(children) == 3
        # First: no newline (starts at original position)
        assert children[0].text is None
        # Middle: has newline (pushes next paragraph down)
        assert children[1].text == "\n"

    def test_newline_in_markdown_paragraphs(self):
        """Markdown paragraphs should also have newlines for spacing (not on first)."""
        from card_factory.templates.renderer import apply_formatted_text_with_paragraphs
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve"><text id="test"><tspan>Placeholder</tspan></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text_with_paragraphs(text_elem, "*Bold*\n_Italic_", 10)
        children = list(text_elem)
        # First: no newline
        assert children[0].text is None

    def test_no_orphan_tspans_without_paragraph_index(self):
        """Verify all DIRECT child tspans of text element have data-paragraph-index."""
        from card_factory.templates.renderer import apply_formatted_text_with_paragraphs
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test"><tspan>Placeholder</tspan></text></svg>')
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_formatted_text_with_paragraphs(text_elem, "Line 1\nLine 2", 10)
        # Check direct children of text element (the paragraph wrapper tspans)
        direct_children = list(text_elem)
        assert len(direct_children) == 2
        for ts in direct_children:
            assert ts.get("data-paragraph-index") is not None


class TestApplyParagraphSpacing:
    """Tests for apply_paragraph_spacing()"""

    def test_single_paragraph_no_cloning(self):
        from card_factory.templates.renderer import apply_paragraph_spacing
        svg = etree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><text id="test" transform="translate(0,10)"><tspan data-paragraph-index="0" fill-opacity="0">Text</tspan></text></svg>')
        tree = etree.ElementTree(svg)
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_paragraph_spacing(tree, text_elem, 10)
        all_text = svg.findall(".//{http://www.w3.org/2000/svg}text")
        assert len(all_text) == 1

    def test_multiple_paragraphs_creates_clones(self):
        from card_factory.templates.renderer import apply_paragraph_spacing
        svg = etree.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <text id="test" transform="translate(0,10)">
                <tspan data-paragraph-index="0" fill-opacity="0">Line 1</tspan>
                <tspan data-paragraph-index="1" fill-opacity="0">Line 2</tspan>
            </text>
        </svg>''')
        tree = etree.ElementTree(svg)
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_paragraph_spacing(tree, text_elem, 10)
        all_text = svg.findall(".//{http://www.w3.org/2000/svg}text")
        assert len(all_text) == 2

    def test_clones_have_unique_ids(self):
        from card_factory.templates.renderer import apply_paragraph_spacing
        svg = etree.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <text id="test" transform="translate(0,10)">
                <tspan data-paragraph-index="0" fill-opacity="0">Line 1</tspan>
                <tspan data-paragraph-index="1" fill-opacity="0">Line 2</tspan>
            </text>
        </svg>''')
        tree = etree.ElementTree(svg)
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_paragraph_spacing(tree, text_elem, 10)
        ids = [t.get("id") for t in svg.findall(".//{http://www.w3.org/2000/svg}text")]
        assert "test" in ids
        assert "test-1" in ids

    def test_first_paragraph_visible_in_original(self):
        from card_factory.templates.renderer import apply_paragraph_spacing
        svg = etree.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <text id="test" transform="translate(0,10)">
                <tspan data-paragraph-index="0" fill-opacity="0">Line 1</tspan>
                <tspan data-paragraph-index="1" fill-opacity="0">Line 2</tspan>
            </text>
        </svg>''')
        tree = etree.ElementTree(svg)
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_paragraph_spacing(tree, text_elem, 10)
        # Original element should have ALL paragraphs, with first visible
        p_tspans = text_elem.findall(".//{http://www.w3.org/2000/svg}tspan[@data-paragraph-index]")
        assert len(p_tspans) == 2
        assert p_tspans[0].get("data-paragraph-index") == "0"
        assert p_tspans[0].get("fill-opacity") is None
        assert p_tspans[1].get("data-paragraph-index") == "1"
        assert p_tspans[1].get("fill-opacity") == "0"

    def test_clone_translated_downward(self):
        from card_factory.templates.renderer import apply_paragraph_spacing
        svg = etree.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <text id="test" transform="translate(0,10)">
                <tspan data-paragraph-index="0" fill-opacity="0">Line 1</tspan>
                <tspan data-paragraph-index="1" fill-opacity="0">Line 2</tspan>
            </text>
        </svg>''')
        tree = etree.ElementTree(svg)
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_paragraph_spacing(tree, text_elem, 10)
        all_text = svg.findall(".//{http://www.w3.org/2000/svg}text")
        assert len(all_text) == 2
        assert all_text[0].get("transform") == "translate(0,10)"
        assert all_text[1].get("transform") == "translate(0,20)"

    def test_each_clone_has_all_paragraphs(self):
        """Each text element should contain ALL paragraphs, with fill-opacity controlling visibility."""
        from card_factory.templates.renderer import apply_paragraph_spacing
        svg = etree.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <text id="test" transform="translate(0,10)">
                <tspan data-paragraph-index="0" fill-opacity="0">Line 1</tspan>
                <tspan data-paragraph-index="1" fill-opacity="0">Line 2</tspan>
            </text>
        </svg>''')
        tree = etree.ElementTree(svg)
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_paragraph_spacing(tree, text_elem, 10)
        
        all_text = svg.findall(".//{http://www.w3.org/2000/svg}text")
        assert len(all_text) == 2
        
        # Each text element should have BOTH paragraphs
        for te in all_text:
            p_tspans = te.findall(".//{http://www.w3.org/2000/svg}tspan[@data-paragraph-index]")
            assert len(p_tspans) == 2, f"Expected 2 paragraphs, got {len(p_tspans)}"

    def test_hidden_paragraphs_act_as_spacers(self):
        """Hidden paragraphs should be present but invisible (fill-opacity=0), acting as spacers."""
        from card_factory.templates.renderer import apply_paragraph_spacing
        svg = etree.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <text id="test" transform="translate(0,10)">
                <tspan data-paragraph-index="0" fill-opacity="0">Line 1</tspan>
                <tspan data-paragraph-index="1" fill-opacity="0">Line 2</tspan>
            </text>
        </svg>''')
        tree = etree.ElementTree(svg)
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_paragraph_spacing(tree, text_elem, 10)
        
        all_text = svg.findall(".//{http://www.w3.org/2000/svg}text")
        
        # First element: paragraph 0 visible, paragraph 1 hidden
        p0 = all_text[0].find(".//{http://www.w3.org/2000/svg}tspan[@data-paragraph-index='0']")
        p1 = all_text[0].find(".//{http://www.w3.org/2000/svg}tspan[@data-paragraph-index='1']")
        assert p0.get("fill-opacity") is None
        assert p1.get("fill-opacity") == "0"
        
        # Second element: paragraph 0 hidden, paragraph 1 visible
        p0 = all_text[1].find(".//{http://www.w3.org/2000/svg}tspan[@data-paragraph-index='0']")
        p1 = all_text[1].find(".//{http://www.w3.org/2000/svg}tspan[@data-paragraph-index='1']")
        assert p0.get("fill-opacity") == "0"
        assert p1.get("fill-opacity") is None

    def test_paragraph_spacing_zero_skips_feature(self):
        from card_factory.templates.renderer import apply_paragraph_spacing
        svg = etree.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <text id="test" transform="translate(0,10)">
                <tspan data-paragraph-index="0" fill-opacity="0">Line 1</tspan>
                <tspan data-paragraph-index="1" fill-opacity="0">Line 2</tspan>
            </text>
        </svg>''')
        tree = etree.ElementTree(svg)
        text_elem = svg.find(".//{http://www.w3.org/2000/svg}text")
        apply_paragraph_spacing(tree, text_elem, 0)
        all_text = svg.findall(".//{http://www.w3.org/2000/svg}text")
        assert len(all_text) == 1


class TestModifyTranslateY:
    """Tests for modify_translate_y()"""

    def test_no_existing_transform(self):
        from card_factory.templates.renderer import modify_translate_y
        result = modify_translate_y(None, 10)
        assert result == "translate(0,10)"

    def test_existing_translate(self):
        from card_factory.templates.renderer import modify_translate_y
        result = modify_translate_y("translate(5,10)", 10)
        assert result == "translate(5,20)"

    def test_existing_matrix(self):
        from card_factory.templates.renderer import modify_translate_y
        result = modify_translate_y("matrix(1,0,0,1,0,10)", 10)
        assert "matrix" in result
        assert result.endswith(",20)")


class TestRenderTemplateParagraphSpacing:
    """Integration tests for paragraph spacing in render_template()"""

    def test_paragraph_spacing_creates_multiple_text_elements(self):
        from card_factory.templates.renderer import render_template
        from card_factory.templates.loader import load_template
        tree = load_template("template/programma.svg")
        bindings = [
            {"element_id": "text-body", "value": "Line 1\nLine 2", "paragraph_spacing": 10}
        ]
        tree = render_template(tree, bindings, {})
        all_text = tree.findall(".//{http://www.w3.org/2000/svg}text[@id='text-body']")
        assert len(all_text) == 1
        all_text_ids = [t.get("id") for t in tree.findall(".//{http://www.w3.org/2000/svg}text")]
        assert "text-body" in all_text_ids
        assert "text-body-1" in all_text_ids

    def test_paragraph_spacing_zero_no_clones(self):
        from card_factory.templates.renderer import render_template
        from card_factory.templates.loader import load_template
        tree = load_template("template/programma.svg")
        bindings = [
            {"element_id": "text-body", "value": "Line 1\nLine 2", "paragraph_spacing": 0}
        ]
        tree = render_template(tree, bindings, {})
        all_text = tree.findall(".//{http://www.w3.org/2000/svg}text[@id='text-body']")
        assert len(all_text) == 1

    def test_paragraph_spacing_with_markdown(self):
        from card_factory.templates.renderer import render_template
        from card_factory.templates.loader import load_template
        tree = load_template("template/programma.svg")
        bindings = [
            {"element_id": "text-body", "value": "*Bold*\n_Italic_", "paragraph_spacing": 10}
        ]
        tree = render_template(tree, bindings, {})
        all_text_ids = [t.get("id") for t in tree.findall(".//{http://www.w3.org/2000/svg}text")]
        assert "text-body" in all_text_ids
        assert "text-body-1" in all_text_ids
