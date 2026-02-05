"""Error types and Result type for DM Parser.

This module defines error handling utilities following functional programming
patterns. It provides a Result type (Success | Failure) for explicit error
handling without exceptions.

Error Types:
    - Success: Represents a successful operation with a value
    - Failure: Represents a failed operation with error details
    - Result: Type alias for Success[T] | Failure

Error Constants:
    - ERROR_FILE_NOT_FOUND: File does not exist
    - ERROR_INVALID_DM_FILE: File is not a valid DM format
    - ERROR_GEOMETRY_CONVERSION: Geometry conversion failed
    - ERROR_RECORD_PARSE: Record parsing failed
    - ERROR_FILE_WRITE: File write operation failed

Helper Functions:
    - is_success: Check if result is Success
    - is_failure: Check if result is Failure
    - unwrap: Extract value from Success, raises ValueError on Failure
    - unwrap_or: Extract value from Success, returns default on Failure
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar("T")


@dataclass(frozen=True)
class Success(Generic[T]):
    """Immutable success result containing a value.

    Attributes:
        value: The successful result value of type T
    """

    value: T


@dataclass(frozen=True)
class Failure:
    """Immutable failure result containing error details.

    Attributes:
        error_type: Error type identifier (use ERROR_* constants)
        message: Human-readable error message
        context: Optional additional context as key-value pairs
    """

    error_type: str
    message: str
    context: dict[str, str] | None = None


# Type alias for Result type (union of Success and Failure)
Result = Union[Success[T], Failure]

# Error type constants
ERROR_FILE_NOT_FOUND = "FileNotFound"
ERROR_INVALID_DM_FILE = "InvalidDMFile"
ERROR_GEOMETRY_CONVERSION = "GeometryConversion"
ERROR_RECORD_PARSE = "RecordParse"
ERROR_FILE_WRITE = "FileWrite"


def is_success(result: Result[T]) -> bool:
    """Check if result is a Success.

    Args:
        result: Result to check

    Returns:
        True if result is Success, False otherwise
    """
    return isinstance(result, Success)


def is_failure(result: Result[T]) -> bool:
    """Check if result is a Failure.

    Args:
        result: Result to check

    Returns:
        True if result is Failure, False otherwise
    """
    return isinstance(result, Failure)


def unwrap(result: Result[T]) -> T:
    """Extract value from Success, raises ValueError on Failure.

    Args:
        result: Result to unwrap

    Returns:
        The value contained in Success

    Raises:
        ValueError: If result is Failure
    """
    if isinstance(result, Success):
        return result.value
    raise ValueError(f"{result.error_type}: {result.message}")


def unwrap_or(result: Result[T], default: T) -> T:
    """Extract value from Success, returns default on Failure.

    Args:
        result: Result to unwrap
        default: Default value to return on Failure

    Returns:
        The value contained in Success, or default if Failure
    """
    if isinstance(result, Success):
        return result.value
    return default
