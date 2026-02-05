"""Unit tests for error types and Result type.

TDD Red phase: Test Result type and error handling utilities.
Requirements: 6.1, 6.2
"""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from dmconverter.dm_parser.errors import (
    ERROR_FILE_NOT_FOUND,
    ERROR_FILE_WRITE,
    ERROR_GEOMETRY_CONVERSION,
    ERROR_INVALID_DM_FILE,
    ERROR_RECORD_PARSE,
    Failure,
    Result,
    Success,
    is_failure,
    is_success,
    unwrap,
    unwrap_or,
)


class TestSuccess(unittest.TestCase):
    """Tests for Success type."""

    def test_create_success_with_value(self) -> None:
        """Success should hold a value."""
        result = Success(value=42)
        self.assertEqual(result.value, 42)

    def test_create_success_with_string(self) -> None:
        """Success should work with string values."""
        result = Success(value="test data")
        self.assertEqual(result.value, "test data")

    def test_create_success_with_complex_type(self) -> None:
        """Success should work with complex types like tuples."""
        data = (1, 2, 3)
        result = Success(value=data)
        self.assertEqual(result.value, (1, 2, 3))

    def test_success_is_immutable(self) -> None:
        """Success should be immutable (frozen dataclass)."""
        result = Success(value=42)
        with self.assertRaises(FrozenInstanceError):
            result.value = 100  # type: ignore[misc]

    def test_success_equality(self) -> None:
        """Success with same value should be equal."""
        result1 = Success(value=42)
        result2 = Success(value=42)
        self.assertEqual(result1, result2)


class TestFailure(unittest.TestCase):
    """Tests for Failure type."""

    def test_create_failure_with_required_fields(self) -> None:
        """Failure should hold error_type and message."""
        failure = Failure(error_type="TestError", message="Something went wrong")
        self.assertEqual(failure.error_type, "TestError")
        self.assertEqual(failure.message, "Something went wrong")
        self.assertIsNone(failure.context)

    def test_create_failure_with_context(self) -> None:
        """Failure should optionally hold context dict."""
        context = {"file": "test.dm", "line": "42"}
        failure = Failure(
            error_type="ParseError", message="Invalid record", context=context
        )
        self.assertEqual(failure.context, {"file": "test.dm", "line": "42"})

    def test_failure_is_immutable(self) -> None:
        """Failure should be immutable (frozen dataclass)."""
        failure = Failure(error_type="TestError", message="Test message")
        with self.assertRaises(FrozenInstanceError):
            failure.message = "New message"  # type: ignore[misc]

    def test_failure_equality(self) -> None:
        """Failure with same values should be equal."""
        failure1 = Failure(error_type="TestError", message="Test message")
        failure2 = Failure(error_type="TestError", message="Test message")
        self.assertEqual(failure1, failure2)


class TestErrorConstants(unittest.TestCase):
    """Tests for error type constants."""

    def test_error_file_not_found_constant(self) -> None:
        """ERROR_FILE_NOT_FOUND constant should be defined."""
        self.assertEqual(ERROR_FILE_NOT_FOUND, "FileNotFound")

    def test_error_invalid_dm_file_constant(self) -> None:
        """ERROR_INVALID_DM_FILE constant should be defined."""
        self.assertEqual(ERROR_INVALID_DM_FILE, "InvalidDMFile")

    def test_error_geometry_conversion_constant(self) -> None:
        """ERROR_GEOMETRY_CONVERSION constant should be defined."""
        self.assertEqual(ERROR_GEOMETRY_CONVERSION, "GeometryConversion")

    def test_error_record_parse_constant(self) -> None:
        """ERROR_RECORD_PARSE constant should be defined."""
        self.assertEqual(ERROR_RECORD_PARSE, "RecordParse")

    def test_error_file_write_constant(self) -> None:
        """ERROR_FILE_WRITE constant should be defined."""
        self.assertEqual(ERROR_FILE_WRITE, "FileWrite")


class TestIsSuccess(unittest.TestCase):
    """Tests for is_success helper function."""

    def test_is_success_returns_true_for_success(self) -> None:
        """is_success should return True for Success."""
        result = Success(value=42)
        self.assertTrue(is_success(result))

    def test_is_success_returns_false_for_failure(self) -> None:
        """is_success should return False for Failure."""
        result = Failure(error_type="TestError", message="Error")
        self.assertFalse(is_success(result))


class TestIsFailure(unittest.TestCase):
    """Tests for is_failure helper function."""

    def test_is_failure_returns_true_for_failure(self) -> None:
        """is_failure should return True for Failure."""
        result = Failure(error_type="TestError", message="Error")
        self.assertTrue(is_failure(result))

    def test_is_failure_returns_false_for_success(self) -> None:
        """is_failure should return False for Success."""
        result = Success(value=42)
        self.assertFalse(is_failure(result))


class TestUnwrap(unittest.TestCase):
    """Tests for unwrap helper function."""

    def test_unwrap_returns_value_for_success(self) -> None:
        """unwrap should return the value for Success."""
        result = Success(value=42)
        self.assertEqual(unwrap(result), 42)

    def test_unwrap_raises_for_failure(self) -> None:
        """unwrap should raise ValueError for Failure."""
        result = Failure(error_type="TestError", message="Something went wrong")
        with self.assertRaises(ValueError) as ctx:
            unwrap(result)
        self.assertIn("TestError", str(ctx.exception))
        self.assertIn("Something went wrong", str(ctx.exception))


class TestUnwrapOr(unittest.TestCase):
    """Tests for unwrap_or helper function."""

    def test_unwrap_or_returns_value_for_success(self) -> None:
        """unwrap_or should return the value for Success."""
        result = Success(value=42)
        self.assertEqual(unwrap_or(result, default=0), 42)

    def test_unwrap_or_returns_default_for_failure(self) -> None:
        """unwrap_or should return default for Failure."""
        result = Failure(error_type="TestError", message="Error")
        self.assertEqual(unwrap_or(result, default=0), 0)


class TestResultTypeAnnotation(unittest.TestCase):
    """Tests for Result type alias."""

    def test_result_can_be_success(self) -> None:
        """Result type should accept Success."""
        result: Result[int] = Success(value=42)
        self.assertIsInstance(result, Success)

    def test_result_can_be_failure(self) -> None:
        """Result type should accept Failure."""
        result: Result[int] = Failure(error_type="Error", message="Failed")
        self.assertIsInstance(result, Failure)


if __name__ == "__main__":
    unittest.main()
