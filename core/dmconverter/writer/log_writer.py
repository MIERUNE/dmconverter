"""変換ログ出力

変換結果のサマリーをテキストファイルに出力する。
"""

from __future__ import annotations

import os
from collections import Counter

from ..constants import get_classification_name

# 要素タイプ名マッピング
_TYPE_NAMES = {
    "E1": "面",
    "E2": "線",
    "E3": "円",
    "E4": "円弧",
    "E5": "点",
    "E6": "方向",
    "E7": "注記",
    "E8": "属性",
    "G": "グリッド",
    "T": "不整三角網",
}


def write_log(
    dm_files,
    parsed,
    layers,
    stats,
    supported_types,
    geom_fail_counter=None,
    errors=None,
    skipped_files=None,
):
    """変換結果のサマリーをテキストファイルに出力する。

    Args:
        dm_files: 入力DMファイルパスのリスト
        parsed: 最初のParsedDM（座標系情報の取得用）
        geom_fail_counter: Counter of (element_type, dm_code) → ジオメトリ変換失敗件数
        errors: 個別エラーメッセージのリスト
        skipped_files: 座標系不一致でスキップされたファイルの説明リスト

    Returns:
        ログファイルのパス
    """
    if geom_fail_counter is None:
        geom_fail_counter = Counter()
    if errors is None:
        errors = []
    if skipped_files is None:
        skipped_files = []

    first_file = dm_files[0]
    input_dir = os.path.dirname(first_file)
    if len(dm_files) > 1:
        log_name = os.path.basename(input_dir)
    else:
        log_name = os.path.splitext(os.path.basename(first_file))[0]
    log_path = os.path.join(input_dir, f"{log_name}_log.txt")

    code_counter = stats["code_counter"]
    type_counter = stats["type_counter"]
    no_coords_counter = stats["no_coords_counter"]

    total = sum(type_counter.values())
    converted = sum(
        count for et, count in type_counter.items() if et in supported_types
    )
    no_coords_total = sum(no_coords_counter.values())
    geom_fail_total = sum(geom_fail_counter.values())

    lines = ["=== DM変換ログ ==="]

    # 入力ファイル情報
    if len(dm_files) == 1:
        lines.append(f"入力: {os.path.basename(first_file)}")
    else:
        lines.append(f"入力: フォルダ指定 ({len(dm_files)}ファイル)")
        for f in dm_files:
            lines.append(f"  {os.path.basename(f)}")
        if skipped_files:
            lines.append(f"スキップ ({len(skipped_files)}ファイル):")
            for sf in skipped_files:
                lines.append(f"  {sf}")

    lines.extend(
        [
            f"座標系: {parsed.mesh_info.coordinate_system} (EPSG:{6668 + parsed.mesh_info.coordinate_system})",
            f"図郭名: {parsed.mesh_info.map_name}",
            f"地図情報レベル: {parsed.mesh_info.scale}",
            "",
            "--- 要素タイプ別 ---",
        ]
    )

    for et in sorted(type_counter.keys()):
        count = type_counter[et]
        name = _TYPE_NAMES.get(et, et)
        status = "✓ 変換済み" if et in supported_types else "✗ 未対応"
        lines.append(f"  {et}({name}): {count}件  {status}")

    lines.extend(
        [
            "",
            f"合計: {total}件 (変換: {converted}件, 未対応: {total - converted}件)",
            f"座標なしスキップ: {no_coords_total}件",
            f"ジオメトリ変換失敗: {geom_fail_total}件",
            f"出力レイヤ数: {len(layers)}",
        ]
    )

    # 分類コード別変換実績
    converted_codes = []
    undefined_codes = []
    unsupported_codes = []
    for (et, dm_code), count in sorted(code_counter.items()):
        name = get_classification_name(dm_code)
        if et not in supported_types:
            type_name = _TYPE_NAMES.get(et, et)
            unsupported_codes.append(
                f"  {et} {dm_code}({name}): {count}件（要素タイプ{et}({type_name})は未対応）"
            )
        elif name == dm_code:
            undefined_codes.append(f"  {et} {dm_code}: {count}件（コード表に未定義）")
        else:
            converted_codes.append(f"  {et} {dm_code}({name}): {count}件")

    lines.extend(["", "--- 分類コード別変換実績 ---"])
    if converted_codes:
        lines.extend(converted_codes)
    else:
        lines.append("  (なし)")

    if undefined_codes or unsupported_codes:
        lines.extend(["", "--- 未変換の分類コード ---"])
        lines.extend(undefined_codes)
        lines.extend(unsupported_codes)

    # 座標なしスキップ詳細
    if no_coords_counter:
        lines.extend(["", "--- 座標なしスキップ詳細 ---"])
        for (et, dm_code), count in sorted(no_coords_counter.items()):
            name = get_classification_name(dm_code)
            label = f"{name}" if name != dm_code else dm_code
            lines.append(f"  {et} {dm_code}({label}): {count}件")

    # ジオメトリ変換失敗詳細
    if geom_fail_counter:
        lines.extend(["", "--- ジオメトリ変換失敗 ---"])
        for (et, dm_code), count in sorted(geom_fail_counter.items()):
            name = get_classification_name(dm_code)
            label = f"{name}" if name != dm_code else dm_code
            lines.append(f"  {et} {dm_code}({label}): {count}件")

    # エラー詳細
    if errors:
        lines.extend(["", "--- エラー ---"])
        for err in errors:
            lines.append(f"  {err}")

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return log_path
