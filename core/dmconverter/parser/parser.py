"""レコード解釈

分離したレコードの中身（分類コード、座標値など）を意味のあるデータとして解釈する。
PR1ではE1-E6（座標系要素）を対応する。E7/E8（注記・属性）はPR2で対応予定。
"""

from __future__ import annotations

from core.dmconverter.classifier import ClassifiedRecords, ElementGroup, ElementRecord
from core.dmconverter.constants import COORD_FIELD_WIDTH
from core.dmconverter.parser.models import (
    Coordinate,
    IndexInfo,
    ParsedDM,
    ParsedElement,
    ParsedGroup,
)

# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------


def _safe_int(text: str, default: int = 0) -> int:
    """文字列を安全に整数変換する。変換できなければdefaultを返す。"""
    stripped = text.strip()
    if not stripped:
        return default
    check = stripped.lstrip("-")
    if not check:
        return default
    if check.isdigit():
        return int(stripped)
    return default


def _parse_coordinate_line_2d(line: str, remaining: int) -> list[Coordinate]:
    """座標行から2D座標を固定7文字フィールドで抽出する。

    1行に最大6組の(x, y)ペアが格納されている。
    remainingで必要な座標数を制限する。
    """
    coords: list[Coordinate] = []
    w = COORD_FIELD_WIDTH
    for i in range(6):
        if remaining <= 0:
            break
        x_start = i * 14
        y_start = x_start + w
        if y_start + w > len(line):
            break
        x_val = _safe_int(line[x_start : x_start + w])
        y_val = _safe_int(line[y_start : y_start + w])
        if x_val == 0 and y_val == 0:
            continue
        coords.append(Coordinate(x=x_val, y=y_val))
        remaining -= 1
    return coords


def _parse_coordinate_line_3d(line: str, remaining: int) -> list[Coordinate]:
    """座標行から3D座標を固定7文字フィールドで抽出する。

    1行に最大4組の(x, y, z)トリプルが格納されている。
    """
    coords: list[Coordinate] = []
    w = COORD_FIELD_WIDTH
    for i in range(4):
        if remaining <= 0:
            break
        x_start = i * 21
        y_start = x_start + w
        z_start = x_start + w * 2
        if z_start + w > len(line):
            break
        x_val = _safe_int(line[x_start : x_start + w])
        y_val = _safe_int(line[y_start : y_start + w])
        z_val = _safe_int(line[z_start : z_start + w])
        if x_val == 0 and y_val == 0:
            continue
        coords.append(Coordinate(x=x_val, y=y_val, z=z_val))
        remaining -= 1
    return coords


def _extract_common_fields(record: str) -> dict:
    """E行から共通フィールドを抽出する。"""
    return {
        "element_type": record[0:2],
        "dm_code": record[2:6].strip(),
        "hierarchy": _safe_int(record[15:16]),
        "zukei_kubun": _safe_int(record[18:20]),
        "data_kubun": _safe_int(record[20:21]),
        "teni": _safe_int(record[24:26]),
        "kandan": _safe_int(record[26:27]),
        "coord_count": _safe_int(record[27:31]),
        "record_count": _safe_int(record[31:35]),
    }


# ---------------------------------------------------------------------------
# 要素タイプ別パーサー（E1-E6）
# ---------------------------------------------------------------------------


def _parse_coords_from_lines(
    fields: dict, coord_lines: tuple[str, ...]
) -> tuple[Coordinate, ...]:
    """後続座標行から座標列を解析する（E1-E4, E6共通）。"""
    is_3d = fields["data_kubun"] in (3, 6)
    count = fields["coord_count"]

    coords: list[Coordinate] = []
    remaining = count
    for line in coord_lines:
        if remaining <= 0:
            break
        if is_3d:
            parsed = _parse_coordinate_line_3d(line, remaining)
        else:
            parsed = _parse_coordinate_line_2d(line, remaining)
        coords.extend(parsed)
        remaining -= len(parsed)

    return tuple(coords)


def _parse_line_area_element(
    record: str, coord_lines: tuple[str, ...]
) -> ParsedElement:
    """E1-E4（面・線・円・弧）を解析する。座標は後続行から取得。"""
    fields = _extract_common_fields(record)
    coordinates = _parse_coords_from_lines(fields, coord_lines)

    return ParsedElement(
        element_type=fields["element_type"],
        dm_code=fields["dm_code"],
        hierarchy=fields["hierarchy"],
        zukei_kubun=fields["zukei_kubun"],
        data_kubun=fields["data_kubun"],
        teni=fields["teni"],
        kandan=fields["kandan"],
        coordinates=coordinates,
    )


def _parse_point_element(record: str) -> ParsedElement:
    """E5（点）を解析する。座標はE行自体に埋め込まれている。"""
    fields = _extract_common_fields(record)

    x_val = _safe_int(record[35:42])
    y_val = _safe_int(record[42:49])
    z_val = _safe_int(record[49:56]) if fields["data_kubun"] in (3, 6) else 0

    coordinates = (Coordinate(x=x_val, y=y_val, z=z_val),)

    return ParsedElement(
        element_type=fields["element_type"],
        dm_code=fields["dm_code"],
        hierarchy=fields["hierarchy"],
        zukei_kubun=fields["zukei_kubun"],
        data_kubun=fields["data_kubun"],
        teni=fields["teni"],
        kandan=fields["kandan"],
        coordinates=coordinates,
    )


def _parse_direction_element(
    record: str, coord_lines: tuple[str, ...]
) -> ParsedElement:
    """E6（方向）を解析する。座標は後続行から取得。"""
    return _parse_line_area_element(record, coord_lines)


_COORD_LINE_PARSERS = {
    "1": _parse_line_area_element,
    "2": _parse_line_area_element,
    "3": _parse_line_area_element,
    "4": _parse_line_area_element,
    "6": _parse_direction_element,
}


def _parse_element(elem: ElementRecord) -> ParsedElement:
    """ElementRecordを要素タイプに応じて解析する。"""
    element_type = elem.record[1]

    if element_type == "5":
        return _parse_point_element(elem.record)

    # E7/E8はPR2で対応。暫定的に座標なしで返す。
    if element_type in "78":
        fields = _extract_common_fields(elem.record)
        return ParsedElement(
            element_type=fields["element_type"],
            dm_code=fields["dm_code"],
            hierarchy=fields["hierarchy"],
            zukei_kubun=fields["zukei_kubun"],
            data_kubun=fields["data_kubun"],
            teni=fields["teni"],
            kandan=fields["kandan"],
            coordinates=(),
        )

    parser = _COORD_LINE_PARSERS.get(element_type)
    if parser is not None:
        return parser(elem.record, elem.coordinate_lines)

    # 未知の要素タイプ
    fields = _extract_common_fields(elem.record)
    return ParsedElement(
        element_type=fields["element_type"],
        dm_code=fields["dm_code"],
        hierarchy=fields["hierarchy"],
        zukei_kubun=fields["zukei_kubun"],
        data_kubun=fields["data_kubun"],
        teni=fields["teni"],
        kandan=fields["kandan"],
        coordinates=(),
    )


def _parse_element_group(group: ElementGroup) -> ParsedGroup:
    """ElementGroupを解析する。"""
    dm_code = group.header[2:6].strip()
    elements = tuple(_parse_element(elem) for elem in group.elements)
    return ParsedGroup(dm_code=dm_code, elements=elements)


def _parse_index(index_records: tuple[str, str, str]) -> IndexInfo:
    """インデックスレコードからIndexInfoを抽出する。

    1行目: M行 — 図郭名の先頭2文字が座標系番号
    """
    line_a = index_records[0]

    # 図郭名は位置2-9（"M "の後）
    # 先頭2文字が座標系番号（例: "02" → 系2）
    map_sheet_id = line_a[2:9].strip()
    coordinate_system = _safe_int(map_sheet_id[:2])

    # 図名は位置10-29
    map_name = line_a[10:29].strip()

    # 縮尺分母は位置29-33
    scale = _safe_int(line_a[29:33])

    return IndexInfo(
        coordinate_system=coordinate_system,
        map_name=map_name,
        scale=scale,
    )


def parse(classified: ClassifiedRecords) -> ParsedDM:
    """分類済みレコードを解析し、構造化データとして返す。

    Args:
        classified: classifier.classify() の戻り値

    Returns:
        ParsedDM: 解析済みDMデータ
    """
    index = _parse_index(classified.index_records)
    groups = tuple(_parse_element_group(group) for group in classified.element_groups)
    return ParsedDM(index=index, groups=groups)
