"""84バイトレコード読み取り

DMファイルを84バイト単位で読み取り、1レコードずつ返す。
"""

from __future__ import annotations

from typing import Iterator


def _detect_encoding(path: str) -> str:
    """ファイルのエンコーディングを判定する。

    判定順序:
        1. UTF-8 BOM があれば utf-8-sig
        2. BOM なしで UTF-8 としてデコードできれば utf-8
        3. cp932 としてデコードできれば cp932
        4. いずれも失敗した場合は ValueError

    Raises:
        ValueError: エンコーディングを判定できない場合
    """
    with open(path, "rb") as f:
        raw = f.read()

    # BOM あり → UTF-8
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"

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


def read_records(path: str) -> Iterator[str]:
    """DMファイルを1レコードずつ読み取る。

    Args:
        path: DMファイルのパス

    Yields:
        レコード文字列（改行除去済み）

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        ValueError: エンコーディングを判定できない場合
    """
    encoding = _detect_encoding(path)

    with open(path, "r", encoding=encoding) as f:
        for line in f:
            record = line.rstrip("\r\n")
            if record:
                yield record
