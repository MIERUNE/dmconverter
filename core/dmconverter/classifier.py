"""レコード分離

読み取ったレコードを分類・仕分けする。
G/Tレコードはスキップする。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Iterator

from core.dmconverter.constants import (
    MESH_BASE_ROWS,
    MESH_HISTORY_SET_ROWS,
    REVISION_COUNT_POSITION,
)


class RecordType(enum.Enum):
    """レコードタイプ"""

    INDEX = "index"
    MAP_SHEET = "map_sheet"
    HEADER = "header"
    ELEMENT = "element"
    COORDINATE = "coordinate"


@dataclass(frozen=True)
class ElementRecord:
    """要素レコード（E行 + 後続の座標行）"""

    record: bytes
    coordinate_lines: tuple[bytes, ...]


@dataclass(frozen=True)
class ElementGroup:
    """グループヘッダ＋配下の要素レコード"""

    header: bytes
    elements: tuple[ElementRecord, ...]


@dataclass(frozen=True)
class ClassifiedRecords:
    """分類済みレコード群"""

    mesh_rows: tuple[bytes, ...]
    element_groups: tuple[ElementGroup, ...]


def _is_element_prefix(record: bytes) -> bool:
    """Eレコード（E1-E8）か判定する。"""
    if len(record) < 2:
        return False
    return record[0:1] == b"E" and ord(b"1") <= record[1] <= ord(b"8")


def _is_header_prefix(record: bytes) -> bool:
    """Hレコードか判定する。"""
    return record.startswith(b"H ")


def _is_skip_prefix(record: bytes) -> bool:
    """G/Tレコード（対応外）か判定する。"""
    return record.startswith(b"G ") or record.startswith(b"T ")


def _has_following_lines(element_type: int) -> bool:
    """後続行を持つ要素タイプか判定する。

    E1-E4: 後続行に座標データを持つ。
    E5:    座標がE行自体に埋め込まれているため後続行なし。
    E6:    後続行に座標データを持つ。
    E7/E8: 後続行に注記・属性データを持つ。
    """
    return element_type in b"1234678"


def _get_revision_count(mesh_row_a: bytes) -> int:
    """図郭レコード(a)から修正回数を取得する。

    位置65-66（0始点、I2）に格納されている。
    新規作成時は0。
    """
    pos = REVISION_COUNT_POSITION
    if len(mesh_row_a) < pos + 2:
        return 0
    raw = mesh_row_a[pos : pos + 2].strip()
    if not raw or not raw.isdigit():
        return 0
    return int(raw)


def _calc_mesh_row_count(revision_count: int) -> int:
    """Mレコード全体の行数を計算する。

    (a)(b)(c)の3行 + (d)(e)(f)×(修正回数+1)
    """
    return MESH_BASE_ROWS + MESH_HISTORY_SET_ROWS * (revision_count + 1)


def classify(records: Iterator[bytes]) -> ClassifiedRecords:
    """レコード列を分類し、構造化して返す。

    2フェーズで処理する:
        Phase 1: Mレコード（図郭レコード全行を可変長で収集）
        Phase 2: 要素グループ（H + E + 座標行）
    Args:
        records: reader.read_records() の戻り値
    Returns:
        ClassifiedRecords
    Raises:
        ValueError: Mレコードの行数が不足している場合
    """
    record_list = list(records)

    # --- Phase 1: Mレコード（図郭レコード）を可変長で収集 ---
    if len(record_list) < MESH_BASE_ROWS:
        raise ValueError(
            f"Mレコードが{MESH_BASE_ROWS}行未満です（{len(record_list)}行）"
        )

    revision_count = _get_revision_count(record_list[0])
    mesh_row_count = _calc_mesh_row_count(revision_count)

    if len(record_list) < mesh_row_count:
        raise ValueError(
            f"Mレコードが不足しています（修正回数{revision_count}→"
            f"必要{mesh_row_count}行、実際{len(record_list)}行）"
        )

    mesh_rows = tuple(record_list[:mesh_row_count])
    pos = mesh_row_count

    # --- Phase 2: 要素グループ（H + E + 座標行） ---
    element_groups: list[ElementGroup] = []
    current_header: bytes | None = None
    current_elements: list[ElementRecord] = []

    while pos < len(record_list):
        record = record_list[pos]

        # G/Tレコードは読み飛ばす
        if _is_skip_prefix(record):
            pos += 1
            continue

        # H行: 新しい要素グループの開始
        # 直前のグループがあれば確定して保存し、新しいグループを開始する
        if _is_header_prefix(record):
            if current_header is not None:
                element_groups.append(
                    ElementGroup(
                        header=current_header,
                        elements=tuple(current_elements),
                    )
                )
            current_header = record
            current_elements = []
            pos += 1
            continue

        # E行: 要素レコードの処理
        if _is_element_prefix(record):
            element_type = record[1]

            if _has_following_lines(element_type):
                # 後続行（座標行/注記行）を収集
                coord_lines: list[bytes] = []
                pos += 1
                while pos < len(record_list):
                    next_record = record_list[pos]
                    if (
                        _is_header_prefix(next_record)
                        or _is_element_prefix(next_record)
                        or _is_skip_prefix(next_record)
                    ):
                        break
                    coord_lines.append(next_record)
                    pos += 1
                current_elements.append(
                    ElementRecord(
                        record=record,
                        coordinate_lines=tuple(coord_lines),
                    )
                )
            else:
                # E5-E8: 座標はE行自体に埋め込まれているため後続行なし
                current_elements.append(
                    ElementRecord(
                        record=record,
                        coordinate_lines=(),
                    )
                )
                pos += 1
            continue

        pos += 1

    if current_header is not None:
        element_groups.append(
            ElementGroup(
                header=current_header,
                elements=tuple(current_elements),
            )
        )

    return ClassifiedRecords(
        mesh_rows=mesh_rows,
        element_groups=tuple(element_groups),
    )
