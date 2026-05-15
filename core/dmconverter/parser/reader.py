"""84バイトレコード読み取り

DMファイルを84バイト単位で読み取り、1レコードずつ返す。
"""

from __future__ import annotations

from typing import Iterator


def detect_encoding(path: str) -> str:
    """ファイルのエンコーディングを判定する。

    判定順序:
        1. UTF-8 BOM があれば utf-8（BOMはread_recordsで除去される）
        2. 全バイトが ASCII 範囲（0x7F以下）なら old_jis（旧型式DM の7-bit JISエンコード）
        3. BOM なしで UTF-8 としてデコードできれば utf-8
        4. cp932 としてデコードできれば cp932
        5. いずれも失敗した場合は ValueError

    Returns:
        "utf-8", "old_jis", "cp932" のいずれか。
        "old_jis" は Python の codec 名ではなく、旧型式DM専用の識別子。

    Raises:
        ValueError: エンコーディングを判定できない場合
    """
    with open(path, "rb") as f:
        raw = f.read()

    # BOM あり → UTF-8（BOMはread_recordsで除去される）
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8"

    # 全バイトが ASCII 範囲 → 旧型式JIS
    if all(b <= 0x7F for b in raw):
        return "old_jis"

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
