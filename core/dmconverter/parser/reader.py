"""84バイトレコード読み取り

DMファイルを84バイト単位で読み取り、1レコードずつ返す。
"""

from __future__ import annotations

import glob
import os
from typing import Iterator


def read_dmi_coordinate_system(folder: str) -> int | None:
    """フォルダ内の.dmiファイルからインデックスレコード(a)の座標系番号を読み取る。

    インデックスレコード(a)のbytes 2-4（I2フィールド）が座標系番号。
    .dmiファイルが存在しない、または座標系番号が1-19の範囲外の場合はNoneを返す。
    """
    dmi_files = glob.glob(os.path.join(folder, "*.dmi")) or glob.glob(
        os.path.join(folder, "*.DMI")
    )
    if not dmi_files:
        return None
    with open(dmi_files[0], "rb") as f:
        first_line = f.readline()
    if len(first_line) < 4:
        return None
    raw = first_line[2:4].decode("ascii", errors="replace").strip()
    if raw.isdigit():
        val = int(raw)
        if 1 <= val <= 19:
            return val
    return None


def detect_encoding(path: str) -> str:
    """ファイルのエンコーディングを判定する。

    判定順序:
        1. UTF-8 BOM があれば utf-8（BOMはread_recordsで除去される）
        2. BOM なしで UTF-8 としてデコードできれば utf-8
        3. cp932 としてデコードできれば cp932
        4. いずれも失敗した場合は ValueError

    Raises:
        ValueError: エンコーディングを判定できない場合
    """
    with open(path, "rb") as f:
        raw = f.read()

    # BOM あり → UTF-8（BOMはread_recordsで除去される）
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8"

    # BOM なし → UTF-8 として検証
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    # UTF-8 でなければ cp932 として検証
    try:
        raw.decode("cp932")
        return "cp932"
    except UnicodeDecodeError:
        raise ValueError(f"エンコーディングを判定できません: {path}")


def read_records(path: str) -> Iterator[bytes]:
    """DMファイルを1レコードずつ読み取る。

    バイナリモードで読み取り、84バイトのレコードをそのまま返す。
    固定長フィールドのパースに対応するため、bytes型で返す。
    Args:
        path: DMファイルのパス
    Yields:
        レコード（bytes型、改行除去済み）
    Raises:
        FileNotFoundError: ファイルが存在しない場合
    """
    with open(path, "rb") as f:
        first = True
        for line in f:
            record = line.rstrip(b"\r\n")
            # 先頭行のUTF-8 BOM（EF BB BF）を除去
            if first:
                record = record.removeprefix(b"\xef\xbb\xbf")
                first = False
            if record:
                yield record
