"""Classification code mapping functions for DM files.

This module provides functions and tables for mapping DM classification
codes to human-readable names and categories. The classification codes
follow the Japanese Public Survey Standard Map Format specification.

Category constants:
    - CATEGORY_ADMINISTRATIVE: Administrative boundaries (行政界)
    - CATEGORY_TRANSPORT: Transport facilities (交通施設)
    - CATEGORY_BUILDING: Buildings (建物)
    - CATEGORY_WATER: Water features (水部)
    - CATEGORY_TOPOGRAPHY: Topographic features (地形)
    - CATEGORY_VEGETATION: Vegetation (植生)
    - CATEGORY_OTHER: Other features (その他)

Functions:
    - get_classification_name: Get name for a classification code
    - get_classification_info: Get detailed info for a classification code
    - get_codes_by_category: Get all codes in a category
"""

from __future__ import annotations

# Category constants
CATEGORY_ADMINISTRATIVE = "行政界"
CATEGORY_TRANSPORT = "交通施設"
CATEGORY_BUILDING = "建物"
CATEGORY_WATER = "水部"
CATEGORY_TOPOGRAPHY = "地形"
CATEGORY_VEGETATION = "植生"
CATEGORY_OTHER = "その他"

# Classification code table
# Maps 4-digit main code to (name, category)
CLASSIFICATION_TABLE: dict[str, tuple[str, str]] = {
    # 行政界 (Administrative boundaries)
    "1100": ("境界", CATEGORY_ADMINISTRATIVE),
    "1101": ("都府県界", CATEGORY_ADMINISTRATIVE),
    "1102": ("北海道の支庁界", CATEGORY_ADMINISTRATIVE),
    "1103": ("郡市・東京都区界", CATEGORY_ADMINISTRATIVE),
    "1104": ("町村・指定都市の区界", CATEGORY_ADMINISTRATIVE),
    "1105": ("大字・町・丁目界", CATEGORY_ADMINISTRATIVE),
    "1106": ("小字界", CATEGORY_ADMINISTRATIVE),
    "1110": ("所属界", CATEGORY_ADMINISTRATIVE),
    # 交通施設 (Transport facilities)
    "2100": ("道路縁", CATEGORY_TRANSPORT),
    "2101": ("真幅道路", CATEGORY_TRANSPORT),
    "2102": ("軽車道", CATEGORY_TRANSPORT),
    "2103": ("徒歩道", CATEGORY_TRANSPORT),
    "2104": ("庭園路等", CATEGORY_TRANSPORT),
    "2105": ("トンネル内の道路", CATEGORY_TRANSPORT),
    "2106": ("建設中の道路", CATEGORY_TRANSPORT),
    "2200": ("道路構造物", CATEGORY_TRANSPORT),
    "2201": ("分離帯", CATEGORY_TRANSPORT),
    "2202": ("安全地帯", CATEGORY_TRANSPORT),
    "2203": ("道路橋", CATEGORY_TRANSPORT),
    "2204": ("歩道橋", CATEGORY_TRANSPORT),
    "2205": ("地下街・地下鉄等出入口", CATEGORY_TRANSPORT),
    "2206": ("道路のトンネル", CATEGORY_TRANSPORT),
    "2207": ("道路情報", CATEGORY_TRANSPORT),
    "2300": ("軌道", CATEGORY_TRANSPORT),
    "2301": ("普通鉄道", CATEGORY_TRANSPORT),
    "2302": ("路面電車", CATEGORY_TRANSPORT),
    "2303": ("特殊軌道", CATEGORY_TRANSPORT),
    "2304": ("索道", CATEGORY_TRANSPORT),
    "2310": ("鉄道の側線", CATEGORY_TRANSPORT),
    "2311": ("プラットホーム", CATEGORY_TRANSPORT),
    "2312": ("鉄道橋", CATEGORY_TRANSPORT),
    "2313": ("跨線橋", CATEGORY_TRANSPORT),
    "2314": ("鉄道のトンネル", CATEGORY_TRANSPORT),
    "2315": ("停留所", CATEGORY_TRANSPORT),
    # 建物 (Buildings)
    "3000": ("建物", CATEGORY_BUILDING),
    "3001": ("普通建物", CATEGORY_BUILDING),
    "3002": ("堅ろう建物", CATEGORY_BUILDING),
    "3003": ("普通無壁舎", CATEGORY_BUILDING),
    "3004": ("堅ろう無壁舎", CATEGORY_BUILDING),
    "3100": ("建物の付属物等", CATEGORY_BUILDING),
    "3101": ("建物記号", CATEGORY_BUILDING),
    "3102": ("門", CATEGORY_BUILDING),
    "3103": ("屋門", CATEGORY_BUILDING),
    "3104": ("タンク", CATEGORY_BUILDING),
    "3105": ("給水塔", CATEGORY_BUILDING),
    "3106": ("煙突", CATEGORY_BUILDING),
    "3107": ("高塔", CATEGORY_BUILDING),
    "3108": ("記念碑", CATEGORY_BUILDING),
    "3109": ("墓碑", CATEGORY_BUILDING),
    "3110": ("立像", CATEGORY_BUILDING),
    "3111": ("路傍祠", CATEGORY_BUILDING),
    "3112": ("灯ろう", CATEGORY_BUILDING),
    "3113": ("鳥居", CATEGORY_BUILDING),
    "3200": ("塀", CATEGORY_BUILDING),
    # 水部 (Water features)
    "5100": ("水涯線", CATEGORY_WATER),
    "5101": ("河川", CATEGORY_WATER),
    "5102": ("海岸線", CATEGORY_WATER),
    "5103": ("湖池等", CATEGORY_WATER),
    "5200": ("水部構造物", CATEGORY_WATER),
    "5201": ("桟橋（木・コンクリート）", CATEGORY_WATER),
    "5202": ("防波堤", CATEGORY_WATER),
    "5203": ("ダム", CATEGORY_WATER),
    "5204": ("せき", CATEGORY_WATER),
    "5205": ("水門", CATEGORY_WATER),
    "5206": ("滝", CATEGORY_WATER),
    "5207": ("浮桟橋", CATEGORY_WATER),
    "5208": ("敷石斜坂", CATEGORY_WATER),
    "5209": ("船揚場", CATEGORY_WATER),
    "5210": ("係留施設", CATEGORY_WATER),
    "5211": ("透過水制", CATEGORY_WATER),
    "5300": ("水部等", CATEGORY_WATER),
    "5301": ("人工水路", CATEGORY_WATER),
    # 地形 (Topographic features)
    "6100": ("等高線", CATEGORY_TOPOGRAPHY),
    "6101": ("計曲線", CATEGORY_TOPOGRAPHY),
    "6102": ("主曲線", CATEGORY_TOPOGRAPHY),
    "6103": ("補助曲線", CATEGORY_TOPOGRAPHY),
    "6104": ("特殊補助曲線", CATEGORY_TOPOGRAPHY),
    "6110": ("凹地", CATEGORY_TOPOGRAPHY),
    "6200": ("変形地", CATEGORY_TOPOGRAPHY),
    "6201": ("土がけ", CATEGORY_TOPOGRAPHY),
    "6202": ("雨裂", CATEGORY_TOPOGRAPHY),
    "6203": ("岩がけ", CATEGORY_TOPOGRAPHY),
    "6204": ("露岩", CATEGORY_TOPOGRAPHY),
    "6205": ("散岩", CATEGORY_TOPOGRAPHY),
    "6206": ("さんご礁", CATEGORY_TOPOGRAPHY),
    "6300": ("場地", CATEGORY_TOPOGRAPHY),
    "6301": ("被覆", CATEGORY_TOPOGRAPHY),
    # 植生 (Vegetation)
    "7100": ("植生", CATEGORY_VEGETATION),
    "7101": ("樹木に囲まれた居住地", CATEGORY_VEGETATION),
    "7102": ("広葉樹林", CATEGORY_VEGETATION),
    "7103": ("針葉樹林", CATEGORY_VEGETATION),
    "7104": ("竹林", CATEGORY_VEGETATION),
    "7105": ("荒地", CATEGORY_VEGETATION),
    "7106": ("はい松地", CATEGORY_VEGETATION),
    "7107": ("しの地", CATEGORY_VEGETATION),
    "7108": ("やし科樹林", CATEGORY_VEGETATION),
    "7109": ("湿地", CATEGORY_VEGETATION),
    "7110": ("砂れき地", CATEGORY_VEGETATION),
    "7111": ("芝地", CATEGORY_VEGETATION),
    "7112": ("牧草地", CATEGORY_VEGETATION),
    "7200": ("耕地", CATEGORY_VEGETATION),
    "7201": ("田", CATEGORY_VEGETATION),
    "7202": ("畑", CATEGORY_VEGETATION),
    "7203": ("さとうきび畑", CATEGORY_VEGETATION),
    "7204": ("パイナップル畑", CATEGORY_VEGETATION),
    "7205": ("桑畑", CATEGORY_VEGETATION),
    "7206": ("茶畑", CATEGORY_VEGETATION),
    "7207": ("果樹園", CATEGORY_VEGETATION),
    "7208": ("その他の樹木畑", CATEGORY_VEGETATION),
    "7209": ("芝地", CATEGORY_VEGETATION),
    # その他 (Other)
    "8100": ("注記", CATEGORY_OTHER),
    "8200": ("基準点", CATEGORY_OTHER),
    "8201": ("三角点", CATEGORY_OTHER),
    "8202": ("水準点", CATEGORY_OTHER),
    "8203": ("多角点等", CATEGORY_OTHER),
    "8204": ("公共基準点", CATEGORY_OTHER),
    "8205": ("電子基準点", CATEGORY_OTHER),
    "8300": ("測量の基準", CATEGORY_OTHER),
}


def get_classification_name(code: str) -> str:
    """Get the human-readable name for a classification code.

    Args:
        code: Classification code (4 or 5 digits)

    Returns:
        Name of the classification, or the code itself if unknown
    """
    # Try exact match first
    if code in CLASSIFICATION_TABLE:
        return CLASSIFICATION_TABLE[code][0]

    # Try main code (first 4 digits) for 5-digit codes
    main_code = code[:4]
    if main_code in CLASSIFICATION_TABLE:
        return CLASSIFICATION_TABLE[main_code][0]

    # Return code itself for unknown codes
    return code


def get_classification_info(code: str) -> dict[str, str]:
    """Get detailed information for a classification code.

    Args:
        code: Classification code (4 or 5 digits)

    Returns:
        Dictionary containing:
            - name: Human-readable name
            - category: Category name
    """
    # Try exact match first
    if code in CLASSIFICATION_TABLE:
        name, category = CLASSIFICATION_TABLE[code]
        return {"name": name, "category": category}

    # Try main code (first 4 digits) for 5-digit codes
    main_code = code[:4]
    if main_code in CLASSIFICATION_TABLE:
        name, category = CLASSIFICATION_TABLE[main_code]
        return {"name": name, "category": category}

    # Return code as name with Other category for unknown codes
    return {"name": code, "category": CATEGORY_OTHER}


def get_codes_by_category(category: str) -> list[str]:
    """Get all classification codes in a category.

    Args:
        category: Category name (use CATEGORY_* constants)

    Returns:
        List of classification codes in the category
    """
    codes = []
    for code, (_, cat) in CLASSIFICATION_TABLE.items():
        if cat == category:
            codes.append(code)
    return sorted(codes)
