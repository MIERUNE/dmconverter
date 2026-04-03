"""変換ログ出力

変換結果のサマリーをテキストファイルに出力する。
"""

from __future__ import annotations

import os

from ..constants import get_classification_name

# 要素タイプ名マッピング
_TYPE_NAMES = {
    "E1": "面",
    "E2": "線",
    "E3": "円",
    "E4": "弧",
    "E5": "点",
    "E6": "方向",
    "E7": "注記",
    "E8": "属性",
}


def write_log(input_file, output_path, parsed, layers, stats, supported_types):
    """変換結果のサマリーをテキストファイルに出力する。

    Returns:
        ログファイルのパス
    """
    input_name = os.path.splitext(os.path.basename(input_file))[0]
    log_path = os.path.join(os.path.dirname(output_path), f"{input_name}_log.txt")

    code_counter = stats["code_counter"]
    type_counter = stats["type_counter"]
    no_coords_count = stats["no_coords_count"]

    total = sum(type_counter.values())
    converted = sum(
        count for et, count in type_counter.items() if et in supported_types
    )

    lines = [
        "=== DM変換ログ ===",
        f"入力: {os.path.basename(input_file)}",
        f"座標系: {parsed.mesh_info.coordinate_system} (EPSG:{6668 + parsed.mesh_info.coordinate_system})",
        f"図郭名: {parsed.mesh_info.map_name}",
        f"地図情報レベル: {parsed.mesh_info.scale}",
        "",
        "--- 要素タイプ別 ---",
    ]

    for et in sorted(type_counter.keys()):
        count = type_counter[et]
        name = _TYPE_NAMES.get(et, et)
        status = "✓ 変換済み" if et in supported_types else "✗ 未対応"
        lines.append(f"  {et}({name}): {count}件  {status}")

    lines.extend(
        [
            "",
            f"合計: {total}件 (変換: {converted}件, 未対応: {total - converted}件)",
            f"座標なしスキップ: {no_coords_count}件",
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
            undefined_codes.append(
                f"  {et} {dm_code}: {count}件（コード表に未定義）"
            )
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

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return log_path
