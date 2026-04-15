"""レコード解釈

分離したレコードの中身（分類コード、座標値など）を意味のあるデータとして解釈する。
"""

from __future__ import annotations

import logging

from ..constants import COORD_FIELD_WIDTH
from .classifier import ClassifiedRecords, ElementGroup, ElementRecord
from .models import (
    AnnotationInfo,
    AttributeInfo,
    Coordinate,
    MapSheetInfo,
    MeshInfo,
    ParsedDM,
    ParsedElement,
    ParsedGroup,
)

logger = logging.getLogger(__name__)
_parse_warnings: list[str] = []

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


def _format_date(raw: str) -> str | None:
    """DM生データの4桁日付(YYMM)をYYYY/MM形式に変換する。

    "0000"や空文字はNoneを返す（GeoPackageでNULLになる）。
    例: "1703" → "2017/03", "0000" → None
    """
    stripped = raw.strip()
    if not stripped or stripped == "0000" or not stripped.isdigit():
        return None
    if len(stripped) != 4:
        return None
    yy = stripped[:2]
    mm = stripped[2:4]
    month = int(mm)
    if month < 1 or month > 12:
        return None
    year = f"20{yy}" if int(yy) < 50 else f"19{yy}"
    return f"{year}/{mm}"


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

    1行に最大4組の(x, y, z)が格納されている。
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
        "element_type": record[0:2],  # A2: レコードタイプ
        "dm_code": record[2:6].strip(),  # I4: 分類コード（レイヤ）
        "chiiki_bunrui": _safe_int(record[6:8]),  # I2: 地域分類
        "jouhou_bunrui": _safe_int(record[8:12]),  # I4: 情報分類
        "element_id": _safe_int(record[12:16]),  # I4: 要素識別番号
        "hierarchy": _safe_int(record[16:18]),  # I2: 階層レベル
        "zukei_kubun": _safe_int(record[18:20]),  # I2: 図形区分
        "data_kubun": _safe_int(record[20:21]),  # I1: 実データ区分
        "seido_kubun": _safe_int(record[21:23]),  # I2: 精度区分
        "chuki_kubun": _safe_int(record[23:24]),  # I1: 注記区分
        "teni": _safe_int(record[24:26]),  # I2: 転位区分
        "kandan": _safe_int(record[26:27]),  # I1: 間断区分
        "coord_count": _safe_int(record[27:31]),  # I4: データ数
        "record_count": _safe_int(record[31:35]),  # I4: レコード数
        "acquired_date": _format_date(record[65:69]) if len(record) >= 69 else None,
        "updated_date": _format_date(record[69:73]) if len(record) >= 73 else None,
        "deleted_date": _format_date(record[73:77]) if len(record) >= 77 else None,
    }


def _build_parsed_element(fields: dict, **kwargs) -> ParsedElement:
    """共通フィールドからParsedElementを生成するヘルパー。"""
    return ParsedElement(
        element_type=fields["element_type"],
        dm_code=fields["dm_code"],
        chiiki_bunrui=fields["chiiki_bunrui"],
        jouhou_bunrui=fields["jouhou_bunrui"],
        element_id=fields["element_id"],
        hierarchy=fields["hierarchy"],
        zukei_kubun=fields["zukei_kubun"],
        data_kubun=fields["data_kubun"],
        seido_kubun=fields["seido_kubun"],
        chuki_kubun=fields["chuki_kubun"],
        teni=fields["teni"],
        kandan=fields["kandan"],
        acquired_date=fields["acquired_date"],
        updated_date=fields["updated_date"],
        deleted_date=fields["deleted_date"],
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 要素タイプ別パーサー（E1-E8）
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
    """E1-E4（面・線・円・円弧）を解析する。座標は後続行から取得。"""
    fields = _extract_common_fields(record)
    coordinates = _parse_coords_from_lines(fields, coord_lines)
    return _build_parsed_element(fields, coordinates=coordinates)


def _parse_point_element(record: str) -> ParsedElement:
    """E5（点）を解析する。座標はE行自体に埋め込まれている。"""
    fields = _extract_common_fields(record)

    # レコード長チェック（座標・属性取得には58bytes必要）
    if len(record) < 58:
        msg = (
            f"E5 {fields['dm_code']} 要素ID={fields['element_id']}: "
            f"不正なレコード長 {len(record)} bytes（最低58bytes必要）"
        )
        logger.warning(msg)
        _parse_warnings.append(msg)
        return _build_parsed_element(fields, coordinates=())

    x_val = _safe_int(record[35:42])
    y_val = _safe_int(record[42:49])
    z_val = _safe_int(record[49:56]) if fields["data_kubun"] in (3, 6) else 0

    coordinates = (Coordinate(x=x_val, y=y_val, z=z_val),)

    attribute_value = _safe_int(record[49:56])
    zokusei_kubun = _safe_int(record[56:58])

    return _build_parsed_element(
        fields,
        coordinates=coordinates,
        attribute_value=attribute_value,
        zokusei_kubun=zokusei_kubun,
    )


def _parse_direction_element(
    record: str, coord_lines: tuple[str, ...]
) -> ParsedElement:
    """E6（方向）を解析する。座標は後続行から取得。"""
    return _parse_line_area_element(record, coord_lines)


def _parse_annotation_element(
    record: str, annotation_lines: tuple[str, ...]
) -> ParsedElement:
    """E7（注記）を解析する。代表点座標はE行、注記データは後続行から取得。"""
    fields = _extract_common_fields(record)

    # レコード長チェック（座標取得には56bytes必要）
    if len(record) < 56:
        msg = (
            f"E7 {fields['dm_code']} 要素ID={fields['element_id']}: "
            f"不正なレコード長 {len(record)} bytes（最低56bytes必要）"
        )
        logger.warning(msg)
        _parse_warnings.append(msg)
        return _build_parsed_element(fields, coordinates=())

    # 代表点座標（E5と同じ位置）
    x_val = _safe_int(record[35:42])
    y_val = _safe_int(record[42:49])
    z_val = _safe_int(record[49:56]) if fields["data_kubun"] in (3, 6) else 0
    coordinates = (Coordinate(x=x_val, y=y_val, z=z_val),)

    # 後続注記レコードの解析
    annotation: AnnotationInfo | None = None
    if annotation_lines:
        first = annotation_lines[0]
        # 注記メタデータ取得には20bytes必要
        if len(first) < 20:
            msg = (
                f"E7 {fields['dm_code']} 要素ID={fields['element_id']}: "
                f"不正な注記後続レコード長 {len(first)} bytes（最低20bytes必要）"
            )
            logger.warning(msg)
            _parse_warnings.append(msg)
            return _build_parsed_element(fields, coordinates=coordinates)
        orientation = _safe_int(first[0:1])
        angle = _safe_int(first[1:8])
        size = _safe_int(first[8:13])
        spacing = _safe_int(first[13:18])
        line_weight = _safe_int(first[18:20])

        # 注記データ（pos 20-83）を全レコードから結合
        text_parts: list[str] = []
        for line in annotation_lines:
            text_parts.append(line[20:84])
        text = "".join(text_parts).rstrip()

        annotation = AnnotationInfo(
            orientation=orientation,
            angle=angle,
            size=size,
            spacing=spacing,
            line_weight=line_weight,
            text=text,
        )

    return _build_parsed_element(
        fields,
        coordinates=coordinates,
        annotation=annotation,
    )


def _parse_attribute_element(
    record: str, attribute_lines: tuple[str, ...]
) -> ParsedElement:
    """E8（属性）を解析する。代表点座標はE行、属性データは後続行から取得。"""
    fields = _extract_common_fields(record)

    # レコード長チェック（座標取得には56bytes必要）
    if len(record) < 56:
        msg = (
            f"E8 {fields['dm_code']} 要素ID={fields['element_id']}: "
            f"不正なレコード長 {len(record)} bytes（最低56bytes必要）"
        )
        logger.warning(msg)
        _parse_warnings.append(msg)
        return _build_parsed_element(fields, coordinates=())

    # 代表点座標（E5と同じ位置）
    x_val = _safe_int(record[35:42])
    y_val = _safe_int(record[42:49])
    z_val = _safe_int(record[49:56]) if fields["data_kubun"] in (3, 6) else 0
    coordinates = (Coordinate(x=x_val, y=y_val, z=z_val),)

    # 後続属性レコードの解析（レコード全体が属性データ）
    attribute: AttributeInfo | None = None
    if attribute_lines:
        data = "".join(attribute_lines).rstrip()
        attribute = AttributeInfo(data=data)

    return _build_parsed_element(
        fields,
        coordinates=coordinates,
        attribute=attribute,
    )


_COORD_LINE_PARSERS = {
    "1": _parse_line_area_element,
    "2": _parse_line_area_element,
    "3": _parse_line_area_element,
    "4": _parse_line_area_element,
    "6": _parse_direction_element,
}


def _parse_element(elem: ElementRecord, encoding: str) -> ParsedElement:
    """ElementRecordを要素タイプに応じて解析する。"""
    record = elem.record.decode(encoding, errors="replace")
    coord_lines = tuple(
        line.decode(encoding, errors="replace") for line in elem.coordinate_lines
    )
    element_type = record[1]

    if element_type == "5":
        return _parse_point_element(record)

    if element_type == "7":
        return _parse_annotation_element(record, coord_lines)

    if element_type == "8":
        return _parse_attribute_element(record, coord_lines)

    parser = _COORD_LINE_PARSERS.get(element_type)
    if parser is not None:
        return parser(record, coord_lines)

    # 未知の要素タイプ
    fields = _extract_common_fields(record)
    return _build_parsed_element(fields, coordinates=())


def _parse_element_group(group: ElementGroup, encoding: str) -> ParsedGroup:
    """ElementGroupを解析する。"""
    header = group.header.decode(encoding, errors="replace")
    dm_code = header[2:6].strip()
    elements = tuple(_parse_element(elem, encoding) for elem in group.elements)
    return ParsedGroup(dm_code=dm_code, elements=elements)


def _parse_mesh_info(mesh_rows: tuple[bytes, ...], encoding: str) -> MeshInfo:
    """図郭レコード(a)からMeshInfoを抽出する。
    1行目: M行 — 図郭名の先頭2文字が座標系番号
    """
    line_a = mesh_rows[0]  # bytesのままスライスして日本語の位置ずれを防ぐ

    # 図郭識別番号: 位置3-10 (A8)
    map_sheet_id = line_a[2:10].decode("ascii", errors="replace").strip()
    coordinate_system = _safe_int(map_sheet_id[:2])

    # 図郭名称: 位置11-30 (A20, 日本語含む)
    map_name = line_a[10:30].decode(encoding, errors="replace").strip()

    # 地図情報レベル: 位置31-35 (I5)
    scale = _safe_int(line_a[30:35].decode("ascii", errors="replace"))

    return MeshInfo(
        coordinate_system=coordinate_system,
        map_name=map_name,
        scale=scale,
    )


def _parse_map_sheet(mesh_rows: tuple[bytes, ...]) -> MapSheetInfo:
    """Mレコードの(b)行からMapSheetInfoを抽出する。

    図郭レコード(b)のフィールド定義（0始点バイト位置）:
        0-6:   左下図郭座標 X (I7, メートル)
        7-13:  左下図郭座標 Y (I7, メートル)
        14-20: 右上図郭座標 X (I7, メートル)
        21-27: 右上図郭座標 Y (I7, メートル)
        44-46: 座標値の単位 (I3)
    """
    record = mesh_rows[1].decode("ascii", errors="replace")

    origin_x = _safe_int(record[0:7])
    origin_y = _safe_int(record[7:14])
    upper_x = _safe_int(record[14:21])
    upper_y = _safe_int(record[21:28])
    coord_unit = _safe_int(record[44:47])

    return MapSheetInfo(
        origin_x=origin_x,
        origin_y=origin_y,
        upper_x=upper_x,
        upper_y=upper_y,
        coord_unit=coord_unit,
    )


def parse(classified: ClassifiedRecords) -> ParsedDM:
    """分類済みレコードを解析し、構造化データとして返す。

    Args:
        classified: classifier.classify() の戻り値

    Returns:
        ParsedDM: 解析済みDMデータ
    """
    global _parse_warnings
    _parse_warnings = []

    enc = classified.encoding
    mesh_info = _parse_mesh_info(classified.mesh_rows, enc)
    map_sheet = _parse_map_sheet(classified.mesh_rows)
    groups = tuple(
        _parse_element_group(group, enc) for group in classified.element_groups
    )
    return ParsedDM(
        mesh_info=mesh_info,
        map_sheet=map_sheet,
        groups=groups,
        parse_warnings=tuple(_parse_warnings),
    )
