"""レコード分離

読み取ったレコードを分類・仕分けする。
修正履歴レコード・G/Tレコードはスキップする。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Iterator

from core.dmconverter.constants import HISTORY_POSITION, INDEX_RECORD_COUNT


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

    record: str
    coordinate_lines: tuple[str, ...]


@dataclass(frozen=True)
class ElementGroup:
    """グループヘッダ＋配下の要素レコード"""

    header: str
    elements: tuple[ElementRecord, ...]


@dataclass(frozen=True)
class ClassifiedRecords:
    """分類済みレコード群"""

    index_records: tuple[str, str, str]
    map_sheet_records: tuple[str, ...]
    element_groups: tuple[ElementGroup, ...]


def _is_modification_history(record: str) -> bool:
    """修正履歴レコードか判定する。
    位置79（0始点）が "1"-"9" なら修正履歴レコード。
    """
    if len(record) <= HISTORY_POSITION:
        return False
    return record[HISTORY_POSITION] in "123456789"


def _is_element_prefix(record: str) -> bool:
    """Eレコード（E1-E8）か判定する。"""
    if len(record) < 2:
        return False
    return record[0] == "E" and record[1] in "12345678"


def _is_header_prefix(record: str) -> bool:
    """Hレコードか判定する。"""
    return record.startswith("H ")


def _is_skip_prefix(record: str) -> bool:
    """G/Tレコード（対応外）か判定する。"""
    return record.startswith("G ") or record.startswith("T ")


def _has_following_lines(element_type: str) -> bool:
    """後続行を持つ要素タイプか判定する。

    E1-E4: 後続行に座標データを持つ。
    E5:    座標がE行自体に埋め込まれているため後続行なし。
    E6:    後続行に座標データを持つ。
    E7/E8: 後続行に注記・属性データを持つ。
    """
    return element_type in "1234678"


def classify(records: Iterator[str]) -> ClassifiedRecords:
    """レコード列を分類し、構造化して返す。

    3フェーズで処理する:
        Phase 1: インデックスレコード（先頭3行）
        Phase 2: 図郭レコード（H/Eが出現するまで）
        Phase 3: 要素グループ（H + E + 座標行）
    Args:
        records: reader.read_records() の戻り値
    Returns:
        ClassifiedRecords
    Raises:
        ValueError: インデックスレコードが3行未満の場合
    """
    record_list = list(records)

    # --- Phase 1: インデックスレコード（先頭3行） ---
    if len(record_list) < INDEX_RECORD_COUNT:
        raise ValueError(
            f"インデックスレコードが{INDEX_RECORD_COUNT}行未満です"
            f"（{len(record_list)}行）"
        )
    index_records = (record_list[0], record_list[1], record_list[2])

    # --- Phase 2: 図郭レコード（H/Eが出現するまで） ---
    map_sheet_lines: list[str] = []
    pos = INDEX_RECORD_COUNT

    while pos < len(record_list):
        record = record_list[pos]
        if _is_header_prefix(record) or _is_element_prefix(record):
            break
        if not _is_modification_history(record):
            map_sheet_lines.append(record)
        pos += 1

    # --- Phase 3: 要素グループ（H + E + 座標行） ---
    element_groups: list[ElementGroup] = []
    current_header: str | None = None
    current_elements: list[ElementRecord] = []

    while pos < len(record_list):
        record = record_list[pos]

        # G/Tレコードは読み飛ばす
        if _is_skip_prefix(record):
            pos += 1
            continue

        # 修正履歴レコードは後続行ごとスキップする
        if _is_modification_history(record):
            pos += 1
            if _is_element_prefix(record) and _has_following_lines(record[1]):
                while pos < len(record_list):
                    next_record = record_list[pos]
                    if (
                        _is_header_prefix(next_record)
                        or _is_element_prefix(next_record)
                        or _is_skip_prefix(next_record)
                    ):
                        break
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
                # 座標行は84バイト全体がデータなので修正履歴チェックは行わない
                coord_lines: list[str] = []
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
        index_records=index_records,
        map_sheet_records=tuple(map_sheet_lines),
        element_groups=tuple(element_groups),
    )
