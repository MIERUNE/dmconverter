#!/usr/bin/env python3
"""tests/data の合成 DM データ生成器。

synthetic_*.dm は本スクリプトが規則的に生成する完全な合成データで、実測量 DM に由来する
座標・注記・要素数・日付・図郭情報は含まない。フィールド位置は国土地理院公開の
数値地形図データファイル仕様に従う。データを変更するときは本スクリプトを編集して
再生成し、スクリプトとデータを一緒にコミットする。

    python3 tests/scripts/generate_test_data.py          # tests/data に生成（上書き）
    python3 tests/scripts/generate_test_data.py --check  # 既存ファイルと生成結果の一致を検証

生成ファイルと主なカバー範囲:
    synthetic_cs06_1000_cp932.dm       cp932, 修正1回, E1-E7, 2レコード注記, 各種年月
    synthetic_cs09_1000_utf8_bom.dm    UTF-8 BOM, Iレコード, G/Tレコード, 3D座標
    synthetic_cs12_2500_cp932_rev3.dm  cp932, 修正3回・コース2, 円・円弧, 中庭線
    synthetic_cs08_2500_oldjis.dm      旧型式 7bit JIS
    synthetic_cs01_500_utf8_lf.dm      UTF-8 BOM無し, LF改行, 座標単位 m
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

RECORD_LENGTH = 84
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BOM = b"\xef\xbb\xbf"

Coord = Sequence[int]  # (x, y) または (x, y, z)。X は北方向、Y は東方向


def encode_text(text: str, codec: str) -> bytes:
    """old_jis は EUC-JP の各バイト - 0x80（parser._decode_old_jis_text の逆変換）。"""
    if codec == "old_jis":
        euc = text.encode("euc_jp")
        if any(b < 0xA1 for b in euc):
            raise ValueError(f"7bit JIS には全角文字のみ使用できます: {text!r}")
        return bytes(b - 0x80 for b in euc)
    return text.encode(codec)


class Record:
    """84 バイト固定長レコード。未設定の位置は空白。"""

    def __init__(self) -> None:
        self._buf = bytearray(b" " * RECORD_LENGTH)

    def put(self, pos: int, data: bytes) -> Record:
        if pos < 0 or pos + len(data) > RECORD_LENGTH:
            raise ValueError(f"レコード範囲外: pos={pos} len={len(data)}")
        self._buf[pos : pos + len(data)] = data
        return self

    def num(self, pos: int, value: int, width: int) -> Record:
        text = str(value)
        if len(text) > width:
            raise ValueError(f"数値 {value} が幅 {width} に収まりません")
        return self.put(pos, text.rjust(width).encode("ascii"))

    def text(self, pos: int, value: str, width: int, codec: str) -> Record:
        raw = encode_text(value, codec)
        if len(raw) > width:
            raise ValueError(
                f"文字列 {value!r} ({len(raw)} bytes) が幅 {width} を超えます"
            )
        return self.put(pos, raw.ljust(width, b" "))

    def bytes(self) -> bytes:
        return bytes(self._buf)


@dataclass
class Element:
    etype: int  # 1=面 2=線 3=円 4=円弧 5=点 6=方向 7=注記
    code: str  # 4桁分類コード
    coords: Sequence[Coord]  # E5/E7 は代表点1点
    zukei: int = 0  # 図形区分（31=中庭線）
    data_kubun: int = 2  # 実データ区分（3=3D）
    seido: int = 35
    hierarchy: int = 2
    attribute_value: int = 0  # E5。3D では Z と同じ位置
    zokusei: int = 0
    # E7 注記
    text: str = ""
    orientation: int = 0
    angle: int = 0
    size: int = 30
    spacing: int = 0
    line_weight: int = 5
    # 取得・更新・消去年月（YYMM）
    acquired: str = "2003"
    updated: str = "0000"
    deleted: str = "0000"

    @property
    def is_3d(self) -> bool:
        return self.data_kubun in (3, 6)


@dataclass
class Group:
    code: str
    elements: Sequence[Element]
    skip_records: bool = False  # H 直後に G/T レコードを挟む


@dataclass
class Sheet:
    filename: str
    codec: str  # cp932 / utf-8 / old_jis
    expected_encoding: str  # reader.detect_encoding の期待値
    sheet_id: str
    map_name: str
    level: int
    origin: tuple[int, int]
    upper: tuple[int, int]
    coord_unit: int  # 1=mm 10=cm 999=m
    revision_count: int
    course_count: int
    groups: Sequence[Group]
    bom: bool = False
    newline: bytes = b"\r\n"
    index_record_cs: Optional[int] = None  # I レコードで与える座標系番号


def _mesh_records(sheet: Sheet) -> list[bytes]:
    rows: list[bytes] = []

    map_name = sheet.map_name
    if sheet.codec == "old_jis":
        # 7bit JIS では ASCII 空白が復号できないため全角空白で埋める
        map_name = map_name.ljust(10, "　")
    row_a = Record().put(0, b"M ").put(2, sheet.sheet_id.encode("ascii").ljust(8))
    row_a.text(10, map_name, 20, sheet.codec)
    row_a.num(30, sheet.level, 5)
    row_a.num(65, sheet.revision_count, 2)
    rows.append(row_a.bytes())

    row_b = Record()
    row_b.num(0, sheet.origin[0], 7).num(7, sheet.origin[1], 7)
    row_b.num(14, sheet.upper[0], 7).num(21, sheet.upper[1], 7)
    row_b.num(44, sheet.coord_unit, 3)
    rows.append(row_b.bytes())

    rows.append(Record().bytes())  # (c)

    for _ in range(sheet.revision_count + 1):
        rows.append(Record().num(9, sheet.course_count, 1).bytes())  # (d)
        rows.append(Record().bytes())  # (e)
        rows.extend(Record().bytes() for _ in range(sheet.course_count))  # (f)
    return rows


def _header_record(group: Group) -> bytes:
    counts = Counter(e.etype for e in group.elements)
    rec = Record().put(0, b"H ").put(2, group.code.encode("ascii"))
    rec.num(6, 0, 2).num(8, 0, 4).num(12, 0, 4).num(16, 1, 2)
    rec.num(18, len(group.elements), 5)
    for etype in range(1, 8):
        rec.num(23 + (etype - 1) * 5, counts.get(etype, 0), 5)
    rec.put(65, b"2003").put(69, b"0000").put(73, b"0000")
    return rec.bytes()


def _coord_lines(coords: Sequence[Coord], is_3d: bool) -> list[bytes]:
    """2D は 6組(x,y)/行、3D は 4組(x,y,z)/行。余りは 0 で埋める。"""
    per_line = 4 if is_3d else 6
    stride = 21 if is_3d else 14
    lines: list[bytes] = []
    for start in range(0, len(coords), per_line):
        rec = Record()
        chunk = coords[start : start + per_line]
        for slot in range(per_line):
            base = slot * stride
            if slot < len(chunk):
                c = chunk[slot]
                if c[0] == 0 and c[1] == 0:
                    raise ValueError(
                        "(0, 0) はパーサが余白と解釈するため使用できません"
                    )
                rec.num(base, c[0], 7).num(base + 7, c[1], 7)
                if is_3d:
                    rec.num(base + 14, c[2] if len(c) > 2 else 0, 7)
            else:
                rec.num(base, 0, 7).num(base + 7, 0, 7)
                if is_3d:
                    rec.num(base + 14, 0, 7)
        lines.append(rec.bytes())
    return lines


def _split_annotation(text: str, codec: str, width: int = 64) -> list[str]:
    """注記を 1 レコード 64 バイトずつに分割する。

    パーサは各レコードの 20-83 バイトをそのまま連結するため、
    最終レコード以外は 64 バイトちょうどでないと途中に空白が混入する。
    """
    chunks: list[str] = []
    current = ""
    for ch in text:
        if len(encode_text(current + ch, codec)) > width:
            chunks.append(current)
            current = ch
        else:
            current += ch
    chunks.append(current)
    for chunk in chunks[:-1]:
        if len(encode_text(chunk, codec)) != width:
            raise ValueError(
                "複数レコードにまたがる注記は、先行レコードが 64 バイトちょうどに"
                f"なる文字列にしてください: {text!r}"
            )
    return chunks


def _annotation_lines(elem: Element, codec: str) -> list[bytes]:
    lines: list[bytes] = []
    for idx, chunk in enumerate(_split_annotation(elem.text, codec)):
        rec = Record()
        if idx == 0:
            rec.num(0, elem.orientation, 1).num(1, elem.angle, 7)
            rec.num(8, elem.size, 5).num(13, elem.spacing, 5)
            rec.num(18, elem.line_weight, 2)
        rec.text(20, chunk, 64, codec)
        lines.append(rec.bytes())
    return lines


def _element_records(elem: Element, element_id: int, codec: str) -> list[bytes]:
    """E レコード + 後続レコード。フィールド位置は parser._extract_common_fields に対応。"""
    rec = Record().put(0, f"E{elem.etype}".encode("ascii"))
    rec.put(2, elem.code.encode("ascii"))
    rec.num(6, 0, 2).num(8, 0, 4).num(12, element_id, 4).num(16, elem.hierarchy, 2)
    rec.num(18, elem.zukei, 2).num(20, elem.data_kubun, 1).num(21, elem.seido, 2)
    rec.num(23, 1 if elem.etype == 7 else 0, 1).num(24, 0, 2).num(26, 0, 1)

    followers: list[bytes] = []
    if elem.etype == 5:
        (point,) = elem.coords
        z = point[2] if elem.is_3d and len(point) > 2 else 0
        rec.num(27, 0, 4).num(31, 0, 4)
        rec.num(35, point[0], 7).num(42, point[1], 7)
        rec.num(49, z if elem.is_3d else elem.attribute_value, 7)
        rec.num(56, elem.zokusei, 2)
    elif elem.etype == 7:
        (point,) = elem.coords
        z = point[2] if elem.is_3d and len(point) > 2 else 0
        followers = _annotation_lines(elem, codec)
        rec.num(27, len(elem.text), 4).num(31, len(followers), 4)
        rec.num(35, point[0], 7).num(42, point[1], 7).num(49, z, 7).num(56, 0, 2)
    else:
        followers = _coord_lines(elem.coords, elem.is_3d)
        rec.num(27, len(elem.coords), 4).num(31, len(followers), 4)
        rec.num(35, 0, 7).num(42, 0, 7).num(49, 0, 7).num(56, 0, 2)

    rec.put(65, elem.acquired.encode("ascii"))
    rec.put(69, elem.updated.encode("ascii"))
    rec.put(73, elem.deleted.encode("ascii"))
    return [rec.bytes()] + followers


def _detect_encoding(raw: bytes) -> str:
    """reader.detect_encoding と同じ判定。"""
    if raw.startswith(BOM):
        return "utf-8"
    if all(b <= 0x7F for b in raw):
        return "old_jis"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    raw.decode("cp932")
    return "cp932"


def render_sheet(sheet: Sheet) -> bytes:
    records: list[bytes] = []
    if sheet.index_record_cs is not None:
        records.append(Record().put(0, b"I ").num(2, sheet.index_record_cs, 2).bytes())
    records.extend(_mesh_records(sheet))

    element_id = 0
    for group in sheet.groups:
        records.append(_header_record(group))
        if group.skip_records:
            records.append(Record().put(0, b"G ").bytes())
            records.append(Record().put(0, b"T ").bytes())
        for elem in group.elements:
            element_id += 1
            records.extend(_element_records(elem, element_id, sheet.codec))

    for rec in records:
        if len(rec) != RECORD_LENGTH:
            raise AssertionError(f"レコード長が {len(rec)} bytes: {rec!r}")

    body = b"".join(rec + sheet.newline for rec in records)
    if sheet.bom:
        body = BOM + body

    detected = _detect_encoding(body)
    if detected != sheet.expected_encoding:
        raise AssertionError(
            f"{sheet.filename}: 文字コード判定が {detected}（期待 {sheet.expected_encoding}）"
        )
    return body


def _rect(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    return [(x0, y0), (x0, y1), (x1, y1), (x1, y0), (x0, y0)]


def _circle3(cx: int, cy: int, r: int) -> list[tuple[int, int]]:
    """円周上の3点（0°, 120°, 240°）。"""
    h = round(r * 0.866)
    return [(cx + r, cy), (cx - r // 2, cy + h), (cx - r // 2, cy - h)]


# 2レコードにまたがる注記（cp932 で 32 文字 = 64 バイト + 8 文字）
LONG_ANNOTATION = (
    "この注記は二つのレコードにまたがる長い合成テキストであり分割結合の検証に用いる。"
)


def build_sheets() -> list[Sheet]:
    sheet_a = Sheet(
        filename="synthetic_cs06_1000_cp932.dm",
        codec="cp932",
        expected_encoding="cp932",
        sheet_id="06SYN001",
        map_name="合成図郭Ａ",
        level=1000,
        origin=(12000, 8000),
        upper=(12600, 8800),
        coord_unit=1,
        revision_count=1,
        course_count=1,
        groups=[
            Group(
                "2100",
                [
                    Element(
                        2,
                        "2101",
                        [
                            (50000, 40000),
                            (50000, 120000),
                            (52000, 200000),
                            (55000, 280000),
                            (60000, 360000),
                            (62000, 440000),
                            (63000, 520000),
                            (63000, 600000),
                        ],
                    ),
                    Element(
                        2,
                        "2101",
                        [(90000, 40000 + 100000 * i) for i in range(6)],
                    ),
                    Element(
                        2,
                        "2102",
                        [(150000, 100000), (200000, 105000), (250000, 110000)],
                        acquired="9906",
                    ),
                ],
            ),
            Group(
                "3000",
                [
                    Element(1, "3001", _rect(200000, 200000, 240000, 260000)),
                    Element(
                        1,
                        "3001",
                        _rect(300000, 200000, 340000, 250000),
                        updated="2104",
                    ),
                    Element(
                        1,
                        "3002",
                        [
                            (400000, 300000),
                            (400000, 380000),
                            (430000, 380000),
                            (430000, 340000),
                            (460000, 340000),
                            (460000, 300000),
                            (400000, 300000),
                        ],
                    ),
                    Element(
                        1,
                        "3001",
                        _rect(500000, 600000, 540000, 640000),
                        deleted="2205",
                    ),
                ],
            ),
            Group(
                "4200",
                [
                    Element(5, "4215", [(120000, 700000)], acquired="0000"),
                    Element(5, "4221", [(130000, 720000)], zokusei=1),
                ],
            ),
            Group(
                "5100",
                [
                    Element(
                        2,
                        "5101",
                        [
                            (20000 + 43000 * i, 700000 + 5000 * (i % 3))
                            for i in range(14)
                        ],
                    ),
                ],
            ),
            Group(
                "5200",
                [
                    Element(6, "5241", [(300000, 650000), (320000, 690000)]),
                    Element(
                        6,
                        "5241",
                        [
                            (350000, 650000),
                            (350000, 690000),
                            (380000, 650000),
                            (400000, 690000),
                        ],
                    ),
                ],
            ),
            Group(
                "7300",
                [
                    Element(
                        5, "7311", [(250000, 500000)], attribute_value=12345, zokusei=1
                    ),
                    Element(5, "7312", [(270000, 520000)], attribute_value=23456),
                ],
            ),
            Group(
                "8100",
                [
                    Element(7, "8131", [(220000, 230000)], text="合成ビル", size=35),
                    Element(
                        7,
                        "8121",
                        [(56000, 300000)],
                        text="合成通り",
                        orientation=1,
                        angle=-45,
                        spacing=10,
                        line_weight=4,
                    ),
                    Element(7, "8181", [(450000, 450000)], text=LONG_ANNOTATION),
                ],
            ),
        ],
    )

    sheet_b = Sheet(
        filename="synthetic_cs09_1000_utf8_bom.dm",
        codec="utf-8",
        expected_encoding="utf-8",
        bom=True,
        sheet_id="ZZSYN002",  # 先頭2文字が数字でない → 座標系は I レコードから
        index_record_cs=9,
        map_name="合成図郭Ｂ",
        level=1000,
        origin=(-24000, 36000),
        upper=(-23400, 36800),
        coord_unit=1,
        revision_count=0,
        course_count=0,
        groups=[
            Group(
                "2100",
                [
                    Element(
                        2,
                        "2101",
                        [
                            (100000, 100000, 12500),
                            (150000, 120000, 12600),
                            (200000, 140000, 12700),
                            (250000, 160000, 12800),
                            (300000, 180000, 12900),
                        ],
                        data_kubun=3,
                    ),
                    Element(
                        2,
                        "2101",
                        [
                            (100000, 300000),
                            (200000, 310000),
                            (300000, 320000),
                            (400000, 330000),
                        ],
                    ),
                ],
                skip_records=True,
            ),
            Group(
                "3000",
                [
                    Element(1, "3001", _rect(200000, 400000, 250000, 460000)),
                    Element(
                        1,
                        "3003",
                        [
                            (400000, 500000),
                            (450000, 560000),
                            (500000, 500000),
                            (400000, 500000),
                        ],
                    ),
                ],
            ),
            Group(
                "4100",
                [
                    Element(5, "4142", [(330000, 440000, 15200)], data_kubun=3),
                    Element(5, "4101", [(340000, 450000)]),
                ],
            ),
            Group(
                "8100",
                [
                    Element(7, "8110", [(300000, 400000)], text="合成市", size=50),
                    Element(7, "8173", [(330000, 445000)], text="１２３．４", size=20),
                ],
            ),
        ],
    )

    sheet_c = Sheet(
        filename="synthetic_cs12_2500_cp932_rev3.dm",
        codec="cp932",
        expected_encoding="cp932",
        sheet_id="12SYN003",
        map_name="合成図郭Ｃ",
        level=2500,
        origin=(-96000, -36000),
        upper=(-94500, -34000),
        coord_unit=10,
        revision_count=3,
        course_count=2,
        groups=[
            Group(
                "2100",
                [
                    Element(
                        2,
                        "2101",
                        [
                            (10000, 10000),
                            (10000, 60000),
                            (12000, 110000),
                            (15000, 160000),
                        ],
                    ),
                ],
            ),
            Group(
                "3000",
                [
                    # 外輪 + 内包される内輪（中庭線）、どの外輪にも内包されない内輪
                    Element(1, "3001", _rect(40000, 40000, 80000, 80000)),
                    Element(1, "3001", _rect(50000, 50000, 60000, 60000), zukei=31),
                    Element(1, "3001", _rect(100000, 150000, 110000, 160000), zukei=31),
                    Element(1, "3002", _rect(120000, 20000, 130000, 30000)),
                ],
            ),
            Group(
                "4200",
                [
                    Element(3, "4221", _circle3(30000, 120000, 500)),
                    Element(3, "4221", _circle3(30000, 140000, 800)),
                    Element(3, "4221", _circle3(30000, 160000, 300)),
                    Element(5, "4215", [(20000, 100000)]),
                ],
            ),
            Group(
                "5100",
                [
                    Element(1, "5105", _rect(90000, 90000, 110000, 120000)),
                ],
            ),
            Group(
                "6100",
                [
                    Element(
                        4, "6130", [(70000, 120000), (72000, 122000), (74000, 120000)]
                    ),
                    Element(
                        4, "6130", [(70000, 150000), (73000, 153000), (76000, 150000)]
                    ),
                    Element(2, "6141", [(85000, 120000), (85000, 160000)]),
                ],
            ),
            Group(
                "8100",
                [
                    Element(7, "8163", [(30000, 121000)], text="合成樹", size=25),
                    Element(7, "8131", [(60000, 60000)], text="合成倉庫", size=35),
                ],
            ),
        ],
    )

    sheet_d = Sheet(
        filename="synthetic_cs08_2500_oldjis.dm",
        codec="old_jis",
        expected_encoding="old_jis",
        sheet_id="08SYN004",
        map_name="合成図郭Ｄ",
        level=2500,
        origin=(48000, 16000),
        upper=(49500, 18000),
        coord_unit=10,
        revision_count=0,
        course_count=0,
        groups=[
            Group(
                "2100",
                [
                    Element(
                        2,
                        "2101",
                        [
                            (10000, 10000),
                            (10000, 60000),
                            (12000, 110000),
                            (15000, 160000),
                        ],
                    ),
                ],
            ),
            Group("3000", [Element(1, "3001", _rect(40000, 40000, 60000, 70000))]),
            Group("4200", [Element(5, "4215", [(20000, 100000)])]),
            Group(
                "8100",
                [
                    Element(7, "8131", [(50000, 55000)], text="合成工場", size=35),
                    Element(7, "8121", [(11000, 80000)], text="合成街道", angle=90),
                ],
            ),
        ],
    )

    sheet_e = Sheet(
        filename="synthetic_cs01_500_utf8_lf.dm",
        codec="utf-8",
        expected_encoding="utf-8",
        newline=b"\n",
        sheet_id="01SYN005",
        map_name="合成図郭Ｅ",
        level=500,
        origin=(200000, 60000),
        upper=(200300, 60400),
        coord_unit=999,
        revision_count=0,
        course_count=1,
        groups=[
            Group(
                "2100",
                [Element(2, "2101", [(10, 20), (10, 120), (20, 220), (30, 320)])],
            ),
            Group("3000", [Element(1, "3001", _rect(100, 100, 140, 150))]),
            Group("4200", [Element(5, "4215", [(200, 300)])]),
            Group("8100", [Element(7, "8131", [(150, 120)], text="合成小屋", size=35)]),
        ],
    )

    return [sheet_a, sheet_b, sheet_c, sheet_d, sheet_e]


def expected_outputs() -> dict[str, bytes]:
    return {sheet.filename: render_sheet(sheet) for sheet in build_sheets()}


def generate(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in expected_outputs().items():
        (out_dir / name).write_bytes(data)
        print(f"生成: {out_dir / name} ({len(data)} bytes)")


def check(out_dir: Path) -> int:
    """既存ファイルが生成結果と一致するか検証する。0=OK, 1=不一致。"""
    expected = expected_outputs()
    problems: list[str] = []
    for name, data in expected.items():
        path = out_dir / name
        if not path.exists():
            problems.append(f"存在しません: {path}")
        elif path.read_bytes() != data:
            problems.append(
                f"生成結果と一致しません（スクリプトを編集して再生成してください）: {path}"
            )

    extras = sorted(
        p.name
        for p in out_dir.iterdir()
        if p.suffix.lower() == ".dm" and p.name not in expected
    )
    if extras:
        print("注意: 生成器由来でないファイル: " + ", ".join(extras))

    if problems:
        for p in problems:
            print(f"NG: {p}", file=sys.stderr)
        return 1
    print(f"OK: {len(expected)} ファイルが生成結果と一致")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="tests/data の合成 DM データを生成・検証する"
    )
    parser.add_argument(
        "--check", action="store_true", help="生成せず、既存ファイルとの一致を検証する"
    )
    parser.add_argument("--out", type=Path, default=DATA_DIR, help="出力先ディレクトリ")
    args = parser.parse_args(argv)

    if args.check:
        return check(args.out)
    generate(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
