"""DM Parser module for parsing Digital Map files.

This module provides functionality to parse DM (Digital Map) files
following the Japanese Public Survey Standard Map Format specification.
"""

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
from dmconverter.dm_parser.models import (
    AnnotationData,
    Coordinate,
    DMData,
    ElementGroup,
    ElementRecord,
    GeodeticDatum,
    IndexRecord,
    MapSheetRecord,
)
from dmconverter.dm_parser.record_helpers import (
    extract_field,
    is_modification_history_record,
    parse_float,
    parse_int,
    should_skip_record,
)
from dmconverter.dm_parser.index_record_parser import (
    parse_index_record_a,
    parse_index_record_b,
    parse_index_record_c,
    parse_index_records,
)
from dmconverter.dm_parser.api import (
    parse_dm_file,
    dm_to_layers,
    load_dm_to_qgis,
    save_dm_to_geopackage,
    get_map_sheet_info,
    get_element_summary,
    get_crs_info,
)

__all__ = [
    # Models
    "AnnotationData",
    "Coordinate",
    "DMData",
    "ElementGroup",
    "ElementRecord",
    "GeodeticDatum",
    "IndexRecord",
    "MapSheetRecord",
    # Error types
    "Failure",
    "Result",
    "Success",
    # Error constants
    "ERROR_FILE_NOT_FOUND",
    "ERROR_FILE_WRITE",
    "ERROR_GEOMETRY_CONVERSION",
    "ERROR_INVALID_DM_FILE",
    "ERROR_RECORD_PARSE",
    # Helper functions (errors)
    "is_failure",
    "is_success",
    "unwrap",
    "unwrap_or",
    # Helper functions (record parsing)
    "extract_field",
    "is_modification_history_record",
    "parse_float",
    "parse_int",
    "should_skip_record",
    # Index record parsing
    "parse_index_record_a",
    "parse_index_record_b",
    "parse_index_record_c",
    "parse_index_records",
    # Public API
    "parse_dm_file",
    "dm_to_layers",
    "load_dm_to_qgis",
    "save_dm_to_geopackage",
    "get_map_sheet_info",
    "get_element_summary",
    "get_crs_info",
]
