import pytest

from yumako.template import replace


class TestReplace:
    """Test cases for the replace function."""

    def test_simple_replacement(self):
        """Test basic variable replacement."""
        text = "Hello {{name}}, welcome to {{place}}!"
        mapping = {"name": "Alice", "place": "Wonderland"}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "Hello Alice, welcome to Wonderland!"

    def test_single_variable(self):
        """Test replacing a single variable."""
        text = "The answer is {{answer}}"
        mapping = {"answer": 42}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "The answer is 42"

    def test_repeated_variable(self):
        """Test replacing the same variable multiple times."""
        text = "{{name}} loves {{name}}"
        mapping = {"name": "Bob"}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "Bob loves Bob"

    def test_numeric_values(self):
        """Test replacing with numeric values."""
        text = "Count: {{count}}, Price: {{price}}"
        mapping = {"count": 10, "price": 99.99}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "Count: 10, Price: 99.99"

    def test_boolean_values(self):
        """Test replacing with boolean values."""
        text = "Is enabled: {{enabled}}"
        mapping = {"enabled": True}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "Is enabled: True"

    def test_no_variables(self):
        """Test text with no variables."""
        text = "This is plain text"
        mapping = {"unused": "value"}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "This is plain text"

    def test_empty_mapping(self):
        """Test with empty mapping dict."""
        text = "No variables here"
        mapping = {}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "No variables here"

    def test_unresolved_vars_default(self):
        """Test that unresolved variables raise exception by default."""
        text = "Hello {{name}}"
        mapping = {}
        with pytest.raises(ValueError, match="Strict mode: template variables unresolved"):
            replace(text, mapping)

    def test_unresolved_vars_raise_false(self):
        """Test unresolved variables when raise_on_unresolved_vars is False."""
        text = "Hello {{name}}"
        mapping = {}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "Hello {{name}}"

    def test_unused_vars_raise_true(self):
        """Test that unused variables raise exception when raise_on_unused_vars is True."""
        text = "Hello {{name}}"
        mapping = {"name": "Alice", "unused": "value"}
        with pytest.raises(ValueError, match="Strict mode: var specified but not in template"):
            replace(text, mapping, raise_on_unused_vars=True)

    def test_unused_vars_raise_false(self):
        """Test unused variables when raise_on_unused_vars is False."""
        text = "Hello {{name}}"
        mapping = {"name": "Alice", "unused": "value"}
        result = replace(text, mapping, raise_on_unused_vars=False)
        assert result == "Hello Alice"

    def test_strict_mode_both_true(self):
        """Test strict mode with both raise flags set to True."""
        text = "Hello {{name}}"
        mapping = {"name": "Alice"}
        result = replace(text, mapping, raise_on_unresolved_vars=True, raise_on_unused_vars=True)
        assert result == "Hello Alice"

    def test_partial_replacement(self):
        """Test when only some variables are in mapping."""
        text = "{{greeting}} {{name}}, welcome to {{place}}"
        mapping = {"greeting": "Hello", "name": "Charlie"}
        with pytest.raises(ValueError, match="Strict mode: template variables unresolved"):
            replace(text, mapping)

    def test_empty_text(self):
        """Test with empty text."""
        text = ""
        mapping = {"key": "value"}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == ""

    def test_special_characters_in_values(self):
        """Test replacing with values containing special characters."""
        text = "Path: {{path}}"
        mapping = {"path": "/usr/local/bin"}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "Path: /usr/local/bin"

    def test_multiline_text(self):
        """Test replacing in multiline text."""
        text = "Line 1: {{var1}}\nLine 2: {{var2}}"
        mapping = {"var1": "first", "var2": "second"}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "Line 1: first\nLine 2: second"

    def test_adjacent_variables(self):
        """Test adjacent variables without separator."""
        text = "{{first}}{{second}}"
        mapping = {"first": "Hello", "second": "World"}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "HelloWorld"

    def test_variable_like_text_without_braces(self):
        """Test that text with variable-like content but without braces is not replaced."""
        text = "The variable name is 'key'"
        mapping = {"key": "value"}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "The variable name is 'key'"

    def test_none_value(self):
        """Test replacing with None value."""
        text = "Value: {{val}}"
        mapping = {"val": None}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "Value: None"

    def test_list_value(self):
        """Test replacing with list value."""
        text = "Items: {{items}}"
        mapping = {"items": [1, 2, 3]}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "Items: [1, 2, 3]"

    def test_dict_value(self):
        """Test replacing with dict value."""
        text = "Config: {{config}}"
        mapping = {"config": {"key": "value"}}
        result = replace(text, mapping, raise_on_unresolved_vars=False)
        assert result == "Config: {'key': 'value'}"

    def test_mismatched_opening_braces(self):
        """Test that extra opening braces raise an error."""
        text = "Hello {{ {{name}}"
        mapping = {"name": "Alice"}
        with pytest.raises(ValueError, match="Mismatched braces"):
            replace(text, mapping)

    def test_mismatched_closing_braces(self):
        """Test that extra closing braces raise an error."""
        text = "Hello {{name}} }}"
        mapping = {"name": "Alice"}
        with pytest.raises(ValueError, match="Mismatched braces"):
            replace(text, mapping)

    def test_multiple_mismatched_braces(self):
        """Test with multiple mismatched braces."""
        text = "{{var1}} and {{ var2 and {{var3}}"
        mapping = {"var1": "a", "var2": "b", "var3": "c"}
        with pytest.raises(ValueError, match="Mismatched braces"):
            replace(text, mapping)

    def test_unmatched_opening_brace(self):
        """Test single unmatched opening brace."""
        text = "Start {{ middle }} end {{"
        mapping = {"middle": "value"}
        with pytest.raises(ValueError, match="Mismatched braces"):
            replace(text, mapping)

    def test_unmatched_closing_brace(self):
        """Test single unmatched closing brace."""
        text = "Start {{ middle }} end }}"
        mapping = {"middle": "value"}
        with pytest.raises(ValueError, match="Mismatched braces"):
            replace(text, mapping)
