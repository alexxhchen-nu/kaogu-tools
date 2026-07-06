#!/usr/bin/env python3
"""
墓葬GIS生成器 — 单文件、零依赖、自适应CSV输入
任意考古CSV → 交互式Canvas地图

用法:
  python nsbd_gis.py <csv_files...> [--overview] [--outdir output]
  python nsbd_gis.py data/                  # 扫描目录,生成所有站点
  python nsbd_gis.py data/ --overview       # 扫描 + 总览地图
  python nsbd_gis.py data/nsbd-11.csv       # 单站点地图
  python nsbd_gis.py data/nsbd-11.csv --name 滏阳营 --lat 36.37 --lon 114.30
  python nsbd_gis.py data/ --discover       # 仅扫描,不生成
  python nsbd_gis.py new.csv --coord-mode exact  # 使用CSV中的精确坐标

编程式API:
  from nsbd_gis import generate_gis
  result = generate_gis(["data/site.csv"], outdir="output", coord_mode="auto")
"""
import argparse
import csv
import html
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path


__version__ = "1.0.0"

# ═══════════════════════════════════════════════════════════
# 1. 常量 & 预设
# ═══════════════════════════════════════════════════════════

ERA_COLORS = {
    "商": "#7c3aed", "先商": "#7c3aed", "夏": "#7c3aed",
    "西周": "#6d28d9", "东周": "#6d28d9",
    "战国": "#dc2626", "秦": "#b91c1c",
    "西汉": "#d97706", "东汉": "#b45309", "汉": "#d97706",
    "晋": "#92400e", "西晋": "#92400e",
    "东魏": "#78350f", "北齐": "#78350f", "北朝": "#78350f",
    "隋": "#059669", "唐": "#059669",
    "北宋": "#2563eb", "宋": "#2563eb", "金": "#1e40af",
    "元": "#ea580c", "明": "#be185d", "清": "#9f1239",
    "近现代": "#6b7280",
}
ERA_ORDER_LIST = [
    "商", "西周", "战国", "秦", "西汉", "东汉", "晋", "北朝", "隋", "唐",
    "宋", "金", "元", "明", "清",
]
ERA_CHRONO = {
    "商": 0, "先商": 0, "夏": 0,
    "西周": 1, "东周": 1,
    "战国": 2, "秦": 3,
    "西汉": 4, "东汉": 5, "汉": 4,
    "晋": 6, "西晋": 6,
    "东魏": 7, "北齐": 7, "北朝": 7,
    "隋": 8, "唐": 9,
    "北宋": 10, "宋": 10, "金": 11,
    "元": 12, "明": 13, "清": 14,
    "近现代": 15,
}

# 遗址预设 (文件前缀 → 元数据)
SITE_PRESETS = {
    "nsbd-2": {
        "name": "nsbd-2遗址(网格Ⅰ/Ⅱ区)",
        "county": "待确认",
        "lat": 37.50,
        "lon": 114.80,
        "geo": [],
    },
    "nsbd-3": {
        "name": "张夺遗址",
        "county": "临城县",
        "lat": 37.44,
        "lon": 114.50,
        "geo": [
            {"type": "river", "name": "沙河", "color": "rgba(100,160,200,0.35)", "width": 2.5,
             "points": [[114.492, 37.445], [114.496, 37.443], [114.500, 37.442],
                        [114.504, 37.441], [114.508, 37.440]]},
            {"type": "road", "name": "328省道", "color": "rgba(160,150,130,0.25)", "width": 2.2,
             "dash": [8, 4],
             "points": [[114.490, 37.445], [114.492, 37.442], [114.495, 37.438]]},
            {"type": "text", "name": "临城县城 ↙", "lon": 114.488, "lat": 37.448,
             "size": 10, "color": "rgba(120,110,100,0.45)"},
            {"type": "text", "name": "沙河", "lon": 114.510, "lat": 37.441,
             "size": 10, "color": "rgba(100,160,200,0.45)", "italic": True},
        ],
    },
    "nsbd-5": {
        "name": "徐水东黑山遗址",
        "county": "徐水区",
        "lat": 39.02,
        "lon": 115.65,
        "geo": [
            {"type": "river", "name": "漕河", "color": "rgba(100,160,200,0.35)", "width": 2.5,
             "points": [[115.642, 39.026], [115.646, 39.025], [115.650, 39.025],
                        [115.654, 39.024], [115.658, 39.023]]},
            {"type": "river", "name": "漕河支流", "color": "rgba(100,160,200,0.2)", "width": 1.5,
             "points": [[115.644, 39.027], [115.647, 39.025], [115.649, 39.022]]},
            {"type": "road", "name": "乡道", "color": "rgba(160,150,130,0.2)", "width": 1.5,
             "points": [[115.645, 39.027], [115.650, 39.027], [115.655, 39.027]]},
            {"type": "text", "name": "东黑山村", "lon": 115.645, "lat": 39.027,
             "size": 10, "color": "rgba(120,110,100,0.45)"},
            {"type": "text", "name": "漕河", "lon": 115.660, "lat": 39.024,
             "size": 10, "color": "rgba(100,160,200,0.45)", "italic": True},
            {"type": "text", "name": "徐水区 ↗", "lon": 115.642, "lat": 39.028,
             "size": 11, "color": "rgba(120,110,100,0.5)"},
        ],
    },
    "nsbd-6": {
        "name": "南吴会墓地",
        "county": "磁县(推测)",
        "lat": 36.38,
        "lon": 114.32,
        "geo": [],
    },
    "nsbd-8": {
        "name": "双庙村墓地",
        "county": "双庙砖厂东侧",
        "lat": 36.35,
        "lon": 114.28,
        "geo": [],
    },
    "nsbd-10": {
        "name": "nsbd-10遗址(网格T4-T96)",
        "county": "待确认",
        "lat": 37.20,
        "lon": 114.60,
        "geo": [],
    },
    "nsbd-11": {
        "name": "滏阳营/湾漳营墓区",
        "county": "磁县",
        "lat": 36.37,
        "lon": 114.30,
        "geo": [
            {"type": "river", "name": "滏阳河", "color": "rgba(100,160,200,0.35)", "width": 2.5,
             "points": [[114.306, 36.375], [114.305, 36.373], [114.304, 36.371],
                        [114.303, 36.369], [114.302, 36.367], [114.301, 36.365]]},
            {"type": "road", "name": "107国道", "color": "rgba(160,150,130,0.25)", "width": 2.2,
             "dash": [8, 4],
             "points": [[114.292, 36.375], [114.292, 36.371], [114.292, 36.367],
                        [114.292, 36.363]]},
            {"type": "road", "name": "乡道", "color": "rgba(160,150,130,0.2)", "width": 1.5,
             "points": [[114.294, 36.374], [114.298, 36.374], [114.302, 36.374],
                        [114.306, 36.374]]},
            {"type": "road", "name": "田间路", "color": "rgba(170,160,140,0.18)", "width": 1,
             "dash": [4, 4],
             "points": [[114.296, 36.373], [114.298, 36.370], [114.300, 36.367]]},
            {"type": "road", "name": "田间路", "color": "rgba(170,160,140,0.18)", "width": 1,
             "dash": [4, 4],
             "points": [[114.302, 36.373], [114.303, 36.370], [114.304, 36.367]]},
            {"type": "river", "name": "灌溉渠", "color": "rgba(100,160,200,0.15)", "width": 1,
             "points": [[114.293, 36.366], [114.297, 36.366], [114.301, 36.366],
                        [114.305, 36.366]]},
            {"type": "text", "name": "磁县县城 ↗", "lon": 114.293, "lat": 36.375,
             "size": 11, "color": "rgba(120,110,100,0.5)"},
            {"type": "text", "name": "滏阳河", "lon": 114.306, "lat": 36.371,
             "size": 10, "color": "rgba(100,160,200,0.45)", "italic": True},
            {"type": "text", "name": "邯郸 ↙", "lon": 114.293, "lat": 36.363,
             "size": 10, "color": "rgba(140,130,110,0.4)"},
            {"type": "text", "name": "湾漳营", "lon": 114.289, "lat": 36.370,
             "size": 10, "color": "rgba(120,110,100,0.45)"},
            {"type": "text", "name": "滏阳营", "lon": 114.307, "lat": 36.375,
             "size": 10, "color": "rgba(120,110,100,0.45)"},
        ],
    },
}

# 河北省界轮廓 (用于总览地图)
HEBEI_OUTLINE = [
    (114.0, 36.05), (114.5, 36.05), (115.0, 36.1), (115.3, 36.1),
    (115.5, 36.2), (116.0, 36.1), (116.3, 36.1), (116.5, 36.2),
    (116.8, 36.3), (117.0, 36.4), (117.4, 36.6), (117.5, 36.8),
    (117.6, 37.0), (117.5, 37.3), (117.6, 37.5), (117.8, 37.7),
    (117.8, 38.0), (117.7, 38.2), (117.6, 38.4), (117.5, 38.5),
    (117.4, 38.6), (117.3, 38.7), (117.4, 38.9), (117.5, 39.0),
    (117.5, 39.2), (117.4, 39.4), (117.2, 39.5), (117.0, 39.6),
    (116.8, 39.7), (116.6, 39.8), (116.4, 39.9), (116.2, 40.0),
    (116.0, 40.1), (115.8, 40.2), (115.5, 40.3), (115.2, 40.5),
    (115.0, 40.6), (114.8, 40.8), (114.6, 41.0), (114.4, 41.1),
    (114.3, 41.2), (114.2, 41.4), (114.3, 41.5), (114.5, 41.6),
    (114.8, 41.7), (115.0, 41.8), (115.3, 41.9), (115.5, 42.0),
    (115.8, 42.0), (116.0, 42.0), (116.3, 41.9), (116.5, 41.8),
    (116.8, 41.7), (117.0, 41.6), (117.2, 41.5), (117.4, 41.4),
    (117.5, 41.3), (117.5, 41.1), (117.3, 41.0), (117.0, 40.8),
    (116.8, 40.6), (116.5, 40.4), (116.3, 40.2), (116.2, 40.0),
    (116.8, 39.7), (117.0, 39.6), (117.2, 39.5), (117.2, 39.0),
    (117.0, 38.5), (116.8, 38.2), (116.5, 38.0), (116.3, 37.8),
    (116.2, 37.5), (116.1, 37.2), (116.0, 36.9), (116.1, 36.5),
    (116.2, 36.3), (116.0, 36.1), (115.5, 36.2), (115.0, 36.1),
    (114.5, 36.05), (114.0, 36.05),
]


# ═══════════════════════════════════════════════════════════
# 2. 遗址元数据自动检测
# ═══════════════════════════════════════════════════════════

def detect_site_metadata(csv_path, rows, site_presets_override=None):
    """从CSV自动检测遗址元数据。

    参数:
        csv_path: CSV文件路径
        rows: CSV行数据列表 (list of dicts)
        site_presets_override: 可选的预设覆盖 {name, lat, lon, county, geo}

    返回:
        {name, county, lat, lon, geo} 遗址元数据
    """
    overrides = site_presets_override or {}

    # 检测遗址名称: CSV列 → 文件名
    name = None
    for col in ("遗址名称", "site_name"):
        for row in rows:
            val = (row.get(col) or "").strip()
            if val:
                name = val
                break
        if name:
            break
    if not name:
        name = overrides.get("name") or Path(csv_path).stem

    # 检测县: CSV列 → 预设 → "未知"
    county = None
    for col in ("county", "县"):
        for row in rows:
            val = (row.get(col) or "").strip()
            if val:
                county = val
                break
        if county:
            break
    if not county:
        county = overrides.get("county", "未知")

    # 坐标: 预设 → 默认
    lat = overrides.get("lat", 37.0)
    lon = overrides.get("lon", 115.0)
    geo = overrides.get("geo", [])

    return {
        "name": name,
        "county": county,
        "lat": lat,
        "lon": lon,
        "geo": geo,
    }


def detect_coord_columns(fieldnames):
    """检测CSV中的坐标列。

    返回:
        (lat_col, lon_col) 或 (None, None)
    """
    if not fieldnames:
        return None, None
    fields = set(fieldnames)
    if "纬度" in fields and "经度" in fields:
        return "纬度", "经度"
    if "lat" in fields and "lon" in fields:
        return "lat", "lon"
    return None, None


def _safe_json(obj):
    """json.dumps + 转义 < 以防止 </script> 注入。"""
    s = json.dumps(obj, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e")


# ═══════════════════════════════════════════════════════════
# 3. 工具函数
# ═══════════════════════════════════════════════════════════

def get_era_color(era):
    """根据年代字符串返回对应颜色。"""
    for k, v in ERA_COLORS.items():
        if k in era:
            return v
    return "#94a3b8"


def era_range_str(era_set):
    """从年代集合生成 '西汉至清代' 格式的跨度字符串。"""
    mapped = sorted(
        ERA_CHRONO[e] for e in era_set if e in ERA_CHRONO
    )
    if not mapped:
        return "未知"
    ordered_keys = [
        "商", "西周", "战国", "秦", "西汉", "东汉", "晋", "北朝",
        "隋", "唐", "宋", "金", "元", "明", "清",
    ]
    if mapped[0] == mapped[-1]:
        return ordered_keys[mapped[0]] if mapped[0] < len(ordered_keys) else "未知"
    first = ordered_keys[mapped[0]] if mapped[0] < len(ordered_keys) else "?"
    last = ordered_keys[mapped[-1]] if mapped[-1] < len(ordered_keys) else "?"
    return f"{first}至{last}"


def csv_key(fname):
    """从文件名提取 'nsbd-11' 前缀。"""
    return Path(fname).stem


# ═══════════════════════════════════════════════════════════
# 3. CSV 解析
# ═══════════════════════════════════════════════════════════

def parse_tombs(files, site_metas_map, coord_mode="auto", random_seed=42):
    """
    解析CSV文件,返回墓葬列表和元数据。

    参数:
        files: CSV文件路径列表
        site_metas_map: {文件前缀: {name, county, lat, lon, geo}} 遗址元数据
        coord_mode: "auto" | "exact" | "jitter" | "none"
        random_seed: 随机种子

    返回:
        tomb_data: [{id, lat, lon, era, color, shape, arts, note, dir, length, width, depth, coord_source}]
        site_tombs: {site_key: [tomb_data子集]}
        site_metas: {site_key: {eras, shapes, arts, all_arts, all_shapes}}
    """
    tomb_data = []
    site_tombs = {}
    site_metas = {}
    rng = random.Random(random_seed)

    for fpath in files:
        fname = Path(fpath).name
        key = csv_key(fname)

        meta = site_metas_map.get(key)
        if not meta:
            print(f"  ⚠️  {fname}: 无元数据,跳过 (用 --lat/--lon 指定,或添加预设)")
            continue

        lat0 = meta.get("lat", 37.0)
        lon0 = meta.get("lon", 115.0)
        tomb_arts = {}
        tomb_shapes = {}
        tomb_notes = {}
        tomb_dirs = {}
        site_tombs[key] = []
        site_metas[key] = {"eras": set(), "shapes": Counter(), "all_arts": Counter()}

        with open(fpath, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            # 检测CSV中的坐标列
            lat_col, lon_col = detect_coord_columns(reader.fieldnames)
            has_exact = lat_col is not None

            # 根据coord_mode决定实际坐标策略
            if coord_mode == "auto":
                use_exact = has_exact
            elif coord_mode == "exact":
                if not has_exact:
                    print(f"  ⚠️  {fname}: 未找到坐标列(纬度/经度 或 lat/lon),回退到jitter")
                use_exact = has_exact
            else:
                use_exact = False

            seen = set()
            for row in reader:
                tid = (row.get("墓葬编号") or "").strip()
                if not tid:
                    continue

                # 收集每墓的器物、形制、备注、墓向
                art_name = (row.get("器物名称") or "").strip()
                if art_name:
                    tomb_arts.setdefault(tid, [])
                    if len(tomb_arts[tid]) < 3:
                        tomb_arts[tid].append(art_name)
                    site_metas[key]["all_arts"][art_name] += 1

                shape = (row.get("墓葬形制") or "").strip()
                if shape:
                    tomb_shapes.setdefault(tid, shape)
                    site_metas[key]["shapes"][shape] += 1

                note = (row.get("备注") or "").strip()
                if note and tid not in tomb_notes:
                    tomb_notes[tid] = note[:100]

                direction = (row.get("墓向") or "").strip()
                if direction and tid not in tomb_dirs:
                    tomb_dirs[tid] = direction

                if tid in seen:
                    continue
                seen.add(tid)

                era = (row.get("年代") or "").strip()
                if era:
                    site_metas[key]["eras"].add(era)

                def safe_float(val):
                    try:
                        return float(val.strip() or 0)
                    except (ValueError, AttributeError):
                        return 0

                length = safe_float(row.get("墓口长"))
                width = safe_float(row.get("墓口宽"))
                depth = safe_float(row.get("墓深"))

                # 坐标分配
                coord_source = "jitter"
                if use_exact:
                    try:
                        lat = float(row.get(lat_col, "").strip() or 0)
                        lon = float(row.get(lon_col, "").strip() or 0)
                        if lat == 0 and lon == 0:
                            raise ValueError("零坐标")
                        coord_source = "exact"
                    except (ValueError, TypeError):
                        lat = lat0 + rng.uniform(-0.005, 0.005)
                        lon = lon0 + rng.uniform(-0.007, 0.007)
                        coord_source = "jitter-fallback"
                elif coord_mode == "none":
                    lat, lon = lat0, lon0
                    coord_source = "center"
                else:
                    lat = lat0 + rng.uniform(-0.005, 0.005)
                    lon = lon0 + rng.uniform(-0.007, 0.007)

                entry = {
                    "id": tid,
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "era": era or "未知",
                    "color": get_era_color(era),
                    "shape": "",
                    "arts": [],
                    "note": "",
                    "dir": "",
                    "length": length,
                    "width": width,
                    "depth": depth,
                    "coord_source": coord_source,
                }
                tomb_data.append(entry)
                site_tombs[key].append(entry)

        # 回填每墓元数据
        for t in site_tombs[key]:
            t["shape"] = tomb_shapes.get(t["id"], "")
            t["arts"] = tomb_arts.get(t["id"], [])
            t["note"] = tomb_notes.get(t["id"], "")
            t["dir"] = tomb_dirs.get(t["id"], "")

        cnt = len(site_tombs[key])
        mode_label = {"exact": "精确坐标", "jitter": "模拟偏移",
                       "jitter-fallback": "模拟偏移", "center": "遗址中心"}
        top_arts = [a for a, _ in site_metas[key]["all_arts"].most_common(5)]
        arts_str = "、".join(top_arts) if top_arts else "无"
        coord_label = mode_label.get(
            site_tombs[key][0]["coord_source"] if site_tombs[key] else "jitter", "模拟偏移")
        print(f"  ✅ {fname} → {cnt} 座墓 | 器物: {arts_str} | 坐标: {coord_label}")

    return tomb_data, site_tombs, site_metas


# ═══════════════════════════════════════════════════════════
# 4. 单站点HTML模板
# ═══════════════════════════════════════════════════════════

def _geo_js(features):
    """为站点地图生成地理参考线的JavaScript代码。"""
    if not features:
        return "  // 无地理参考数据\n"
    parts = []
    for feat in features:
        if feat["type"] in ("river", "road"):
            pts = feat["points"]
            pts_js = ",".join(f"[{p[0]},{p[1]}]" for p in pts)
            dash = feat.get("dash")
            dash_js = f", {json.dumps(dash)}" if dash else ""
            parts.append(
                f'  drawGeoLine([{pts_js}], '
                f'\'{feat["color"]}\', {feat["width"]}{dash_js});'
            )
        elif feat["type"] == "text":
            name_js = json.dumps(feat["name"], ensure_ascii=False)
            parts.append(
                f'  geoLabels.push({{text:{name_js}, '
                f'lon:{feat["lon"]}, lat:{feat["lat"]}, '
                f'size:{feat["size"]}, color:{json.dumps(feat["color"])}, '
                f'italic:{"true" if feat.get("italic") else "false"}}});'
            )
    return "\n".join(parts) + "\n"


def render_site_map(site_name, county, era_span, tomb_type, top_arts_str,
                    fname, tombs_json, base_lat, base_lon, geo_features,
                    era_colors_js, era_order_js):
    """生成单站点的完整HTML。"""
    tomb_count = str(len(json.loads(tombs_json)))
    geo_block = _geo_js(geo_features)

    return (
        '<!DOCTYPE html>\n'
        '<html lang="zh-CN">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<title>{html.escape(site_name)} — 墓葬分布图</title>\n'
        '<style>\n'
        '*{margin:0;padding:0;box-sizing:border-box}\n'
        'body{font-family:-apple-system,"PingFang SC","Noto Sans SC",sans-serif;'
        'background:#f7f6f2;color:#333;font-size:14px;overflow:hidden}\n'
        '.layout{display:flex;height:100vh}\n'
        '.sidebar{width:320px;min-width:320px;height:100vh;overflow-y:auto;'
        'background:#fff;border-right:1px solid #e5e5e0;display:flex;'
        'flex-direction:column;z-index:10;transition:margin-left 0.3s ease}\n'
        '.sidebar.collapsed{margin-left:-320px}\n'
        '.sidebar::-webkit-scrollbar{width:4px}\n'
        '.sidebar::-webkit-scrollbar-thumb{background:#ddd;border-radius:2px}\n'
        '.toggle-btn{position:absolute;top:12px;z-index:11;width:36px;height:36px;'
        'border-radius:0 8px 8px 0;background:rgba(255,255,255,0.92);'
        'border:1px solid rgba(0,0,0,0.08);font-size:18px;color:#555;cursor:pointer;'
        'display:flex;align-items:center;justify-content:center;'
        'box-shadow:1px 1px 6px rgba(0,0,0,0.08);transition:left 0.3s ease}\n'
        '.toggle-btn.open{left:320px}\n'
        '.toggle-btn.closed{left:0}\n'
        '.sidebar-header{padding:20px 20px 16px;border-bottom:1px solid #eee}\n'
        '.sidebar-header h1{font-size:18px;font-weight:700;color:#1a1a1a}\n'
        '.sidebar-header .sub{font-size:13px;color:#999;margin-top:4px}\n'
        '.sidebar-stats{display:flex;gap:24px;padding:14px 20px;border-bottom:1px solid #eee}\n'
        '.stat{text-align:center}\n'
        '.stat .num{font-size:20px;font-weight:700;color:#1a1a1a}\n'
        '.stat .lbl{font-size:12px;color:#aaa;margin-top:2px}\n'
        '.site-meta{padding:12px 20px;border-bottom:1px solid #eee;font-size:13px;'
        'color:#666;line-height:1.8}\n'
        '.legend-bar{display:flex;flex-wrap:wrap;gap:6px 12px;padding:12px 20px;'
        'border-bottom:1px solid #eee}\n'
        '.legend-chip{display:flex;align-items:center;gap:5px;font-size:13px;'
        'color:#666;cursor:pointer;transition:opacity 0.2s}\n'
        '.legend-chip:hover{opacity:0.7}\n'
        '.legend-chip .dot{width:10px;height:10px;border-radius:50%;'
        'border:1.5px solid rgba(0,0,0,0.08)}\n'
        '.tomb-list{flex:1;overflow-y:auto;padding:8px 10px}\n'
        '.tomb-item{display:flex;align-items:flex-start;gap:10px;padding:8px 12px;'
        'border-radius:8px;cursor:pointer;transition:background 0.15s;font-size:13px}\n'
        '.tomb-item:hover{background:#f5f5f0}\n'
        '.tomb-item.active{background:#eef2ff}\n'
        '.tomb-dot{width:8px;height:8px;border-radius:50%;margin-top:5px;flex-shrink:0}\n'
        '.tomb-info{flex:1;min-width:0}\n'
        '.tid{font-size:13px;font-weight:500;color:#1a1a1a}\n'
        '.tmeta{font-size:11px;color:#aaa;margin-top:1px}\n'
        '.detail-panel{padding:18px 20px;border-top:1px solid #eee;background:#fafaf8;'
        'min-height:180px}\n'
        '.detail-panel h2{font-size:15px;font-weight:600;color:#1a1a1a;margin-bottom:6px}\n'
        '.detail-panel .tag{display:inline-block;padding:2px 9px;border-radius:10px;'
        'font-size:12px;color:#fff;margin-bottom:8px}\n'
        '.detail-panel dl{display:grid;grid-template-columns:auto 1fr;gap:3px 10px;'
        'font-size:13px}\n'
        '.detail-panel dt{color:#aaa}\n'
        '.detail-panel dd{color:#333}\n'
        '.detail-panel .empty{color:#ccc;font-size:13px;font-style:italic;padding:20px 0}\n'
        '.map-area{flex:1;position:relative;background:#efece4;overflow:hidden}\n'
        'canvas{display:block}\n'
        '.zoom-controls{position:absolute;bottom:20px;right:20px;z-index:10;'
        'display:flex;flex-direction:column;gap:4px}\n'
        '.zoom-btn{width:36px;height:36px;border-radius:8px;'
        'background:rgba(255,255,255,0.92);border:1px solid rgba(0,0,0,0.08);'
        'font-size:18px;color:#555;cursor:pointer;display:flex;align-items:center;'
        'justify-content:center;box-shadow:0 1px 4px rgba(0,0,0,0.06);'
        'transition:background 0.15s}\n'
        '.zoom-btn:hover{background:#fff}\n'
        '.zoom-hint{position:absolute;bottom:20px;left:50%;transform:translateX(-50%);'
        'font-size:11px;color:#bbb;pointer-events:none}\n'
        '.tooltip{position:fixed;z-index:100;background:rgba(255,255,255,0.95);'
        'border:1px solid rgba(0,0,0,0.08);border-radius:6px;padding:5px 10px;'
        'font-size:13px;box-shadow:0 2px 8px rgba(0,0,0,0.08);pointer-events:none;'
        'opacity:0;transition:opacity 0.15s;white-space:nowrap}\n'
        '.tooltip.show{opacity:1}\n'
        '.search-box{padding:8px 20px;border-bottom:1px solid #eee}\n'
        '.search-box input{width:100%;padding:6px 10px;border:1px solid #e0e0e0;'
        'border-radius:6px;font-size:13px;outline:none;background:#fafafa}\n'
        '.search-box input:focus{border-color:#bbb;background:#fff}\n'
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '\n'
        '<div class="layout">\n'
        '  <div class="sidebar" id="sidebar">\n'
        '    <div class="sidebar-header">\n'
        f'      <h1>{html.escape(site_name)}</h1>\n'
        f'      <div class="sub">{html.escape(fname)} · {html.escape(era_span)}</div>\n'
        '    </div>\n'
        '    <div class="sidebar-stats">\n'
        f'      <div class="stat"><div class="num">{tomb_count}</div>'
        '<div class="lbl">墓葬</div></div>\n'
        f'      <div class="stat"><div class="num">{html.escape(county)}</div>'
        '<div class="lbl">位置</div></div>\n'
        '    </div>\n'
        '    <div class="site-meta">\n'
        f'      <b>墓葬类型：</b>{html.escape(tomb_type)}<br>\n'
        f'      <b>主要器物：</b>{html.escape(top_arts_str)}\n'
        '    </div>\n'
        '    <div class="legend-bar" id="legend"></div>\n'
        '    <div class="search-box"><input type="text" id="searchInput" '
        'placeholder="搜索墓葬编号…" oninput="filterTombs(this.value)"></div>\n'
        '    <div class="tomb-list" id="tombList"></div>\n'
        '    <div class="detail-panel" id="detailPanel">\n'
        '      <div class="empty">← 点击墓葬查看详情</div>\n'
        '    </div>\n'
        '  </div>\n'
        '\n'
        '  <button class="toggle-btn open" id="toggleBtn" '
        'onclick="toggleSidebar()">◀</button>\n'
        '\n'
        '  <div class="map-area" id="mapArea">\n'
        '    <canvas id="map"></canvas>\n'
        '    <div class="zoom-controls">\n'
        '      <div class="zoom-btn" id="zoomIn">+</div>\n'
        '      <div class="zoom-btn" id="zoomOut">−</div>\n'
        '    </div>\n'
        '    <div class="zoom-hint">滚轮缩放 · 拖拽平移</div>\n'
        '  </div>\n'
        '</div>\n'
        '\n'
        '<div class="tooltip" id="tooltip"></div>\n'
        '\n'
        '<script>\n'
        f'const tombs = {tombs_json};\n'
        '\n'
        f'const ERA_COLORS = {era_colors_js};\n'
        f'const ERA_ORDER = {era_order_js};\n'
        '\n'
        f'const SITE_NAME_JS = {json.dumps(site_name, ensure_ascii=False)};\n'
        f'const BASE_LON = {base_lon};\n'
        f'const BASE_LAT = {base_lat};\n'
        '\n'
        'function getColor(era) {\n'
        '  for (const [k, v] of Object.entries(ERA_COLORS)) '
        '{ if (era.includes(k)) return v; }\n'
        "  return '#94a3b8';\n"
        '}\n'
        '\n'
        '// ── Canvas ──\n'
        'const canvas = document.getElementById("map");\n'
        'const ctx = canvas.getContext("2d");\n'
        'const tooltip = document.getElementById("tooltip");\n'
        'const mapArea = document.getElementById("mapArea");\n'
        '\n'
        'let W, H, dpr;\n'
        'let viewScale = 1, viewOffX = 0, viewOffY = 0;\n'
        'let plotPoints = [], hoveredIdx = -1, selectedIdx = -1;\n'
        'let dragging = false, dragStartX, dragStartY, dragOffX, dragOffY;\n'
        'let activeFilter = null;\n'
        'let searchQuery = "";\n'
        '\n'
        '// 坐标范围\n'
        'const allLats = tombs.map(t => t.lat);\n'
        'const allLons = tombs.map(t => t.lon);\n'
        'const PAD = 0.004;\n'
        'const D_S = Math.min(...allLats) - PAD;\n'
        'const D_N = Math.max(...allLats) + PAD;\n'
        'const D_W = Math.min(...allLons) - PAD;\n'
        'const D_E = Math.max(...allLons) + PAD;\n'
        'const D_RLON = D_E - D_W;\n'
        'const D_RLAT = D_N - D_S;\n'
        '\n'
        'let baseScale, baseOX, baseOY;\n'
        '\n'
        'function computeBase() {\n'
        '  const margin = 60;\n'
        '  const usableW = W - margin * 2;\n'
        '  const usableH = H - margin * 2;\n'
        '  baseScale = Math.min(usableW / D_RLON, usableH / D_RLAT);\n'
        '  baseOX = margin + (usableW - D_RLON * baseScale) / 2 - D_W * baseScale;\n'
        '  baseOY = margin + (usableH - D_RLAT * baseScale) / 2 + D_N * baseScale;\n'
        '}\n'
        '\n'
        'function dataToScreen(lon, lat) {\n'
        '  const sx = lon * baseScale + baseOX;\n'
        '  const sy = -lat * baseScale + baseOY;\n'
        '  const cx = W / 2, cy = H / 2;\n'
        '  return [\n'
        '    cx + (sx - cx + viewOffX) * viewScale,\n'
        '    cy + (sy - cy + viewOffY) * viewScale\n'
        '  ];\n'
        '}\n'
        '\n'
        '// ── 绘制 ──\n'
        'function draw() {\n'
        '  ctx.clearRect(0, 0, W, H);\n'
        '\n'
        '  // 背景\n'
        '  const [bx1, by1] = dataToScreen(D_W, D_N);\n'
        '  const [bx2, by2] = dataToScreen(D_E, D_S);\n'
        "  ctx.fillStyle = '#f0ede5';\n"
        '  ctx.fillRect(bx1, by1, bx2 - bx1, by2 - by1);\n'
        '\n'
        '  // 网格\n'
        "  ctx.strokeStyle = 'rgba(0,0,0,0.06)';\n"
        '  ctx.lineWidth = 0.5;\n'
        '  const lonStep = 0.005;\n'
        '  const latStep = 0.005;\n'
        '  for (let lon = Math.floor(D_W / lonStep) * lonStep; lon <= D_E; lon += lonStep) {\n'
        '    const [x1, y1] = dataToScreen(lon, D_S);\n'
        '    const [x2, y2] = dataToScreen(lon, D_N);\n'
        '    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();\n'
        '  }\n'
        '  for (let lat = Math.floor(D_S / latStep) * latStep; lat <= D_N; lat += latStep) {\n'
        '    const [x1, y1] = dataToScreen(D_W, lat);\n'
        '    const [x2, y2] = dataToScreen(D_E, lat);\n'
        '    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();\n'
        '  }\n'
        '\n'
        '  // ── 地理参考 ──\n'
        '  const geoLabels = [];\n'
        '  function drawGeoLine(pts, color, width, dash) {\n'
        '    ctx.beginPath();\n'
        '    const sp = pts.map(p => dataToScreen(p[0], p[1]));\n'
        '    ctx.moveTo(sp[0][0], sp[0][1]);\n'
        '    for (let i = 1; i < sp.length - 1; i++) {\n'
        '      const xc = (sp[i][0]+sp[i+1][0])/2, yc = (sp[i][1]+sp[i+1][1])/2;\n'
        '      ctx.quadraticCurveTo(sp[i][0], sp[i][1], xc, yc);\n'
        '    }\n'
        '    ctx.lineTo(sp[sp.length-1][0], sp[sp.length-1][1]);\n'
        '    ctx.strokeStyle = color;\n'
        '    ctx.lineWidth = width * Math.min(viewScale, 2);\n'
        '    if (dash) ctx.setLineDash(dash);\n'
        '    ctx.stroke();\n'
        '    ctx.setLineDash([]);\n'
        '  }\n'
        '\n'
        f'{geo_block}'
        '\n'
        '  // 地名标注\n'
        '  geoLabels.forEach(l => {\n'
        '    const [lx, ly] = dataToScreen(l.lon, l.lat);\n'
        '    ctx.save();\n'
        '    ctx.font = (l.italic ? "italic " : "") + l.size + "px sans-serif";\n'
        '    ctx.fillStyle = l.color;\n'
        '    ctx.textAlign = "center";\n'
        '    ctx.fillText(l.text, lx, ly);\n'
        '    ctx.restore();\n'
        '  });\n'
        '\n'
        '  // 遗址区域圆\n'
        '  const [sx, sy] = dataToScreen(BASE_LON, BASE_LAT);\n'
        '  const rad = 35 * viewScale;\n'
        '  ctx.save();\n'
        '  ctx.beginPath();\n'
        '  ctx.arc(sx, sy, rad, 0, Math.PI * 2);\n'
        "  ctx.fillStyle = 'rgba(185,28,28,0.06)';\n"
        '  ctx.fill();\n'
        "  ctx.strokeStyle = 'rgba(185,28,28,0.2)';\n"
        '  ctx.lineWidth = 1.5;\n'
        '  ctx.setLineDash([5, 4]);\n'
        '  ctx.stroke();\n'
        '  ctx.setLineDash([]);\n'
        '  ctx.restore();\n'
        '\n'
        '  // 墓葬点\n'
        '  plotPoints = [];\n'
        '  tombs.forEach((t, i) => {\n'
        '    const [cx, cy] = dataToScreen(t.lon, t.lat);\n'
        '    const r = Math.max(3, 5 * Math.min(viewScale, 3));\n'
        '    const color = t.color;\n'
        '    const isHovered = i === hoveredIdx;\n'
        '    const isSelected = i === selectedIdx;\n'
        '    const dimmedByFilter = activeFilter && !t.era.includes(activeFilter) '
        '&& !activeFilter.includes(t.era);\n'
        '    const dimmedBySearch = searchQuery && '
        '!t.id.toLowerCase().includes(searchQuery.toLowerCase());\n'
        '    const dimmed = dimmedByFilter || dimmedBySearch;\n'
        '\n'
        '    ctx.save();\n'
        '    ctx.globalAlpha = dimmed ? 0.08 : 1;\n'
        '\n'
        '    if (isHovered || isSelected) {\n'
        '      ctx.beginPath();\n'
        '      ctx.arc(cx, cy, r + 6, 0, Math.PI * 2);\n'
        '      ctx.fillStyle = color + "30";\n'
        '      ctx.fill();\n'
        '      if (isSelected) {\n'
        '        ctx.strokeStyle = color;\n'
        '        ctx.lineWidth = 2;\n'
        '        ctx.stroke();\n'
        '      }\n'
        '    }\n'
        '\n'
        '    // 墓葬标记 — 用小方块表示墓葬朝向\n'
        '    const dirAngle = parseDirection(t.dir);\n'
        '    ctx.save();\n'
        '    ctx.translate(cx, cy);\n'
        '    if (dirAngle !== null) ctx.rotate(dirAngle);\n'
        '    ctx.fillStyle = color;\n'
        '    ctx.globalAlpha = dimmed ? 0.08 : 0.85;\n'
        '    const mLen = r * 1.6;\n'
        '    const mWid = r * 0.8;\n'
        '    ctx.fillRect(-mWid/2, -mLen/2, mWid, mLen);\n'
        "    ctx.strokeStyle = 'rgba(255,255,255,0.6)';\n"
        '    ctx.lineWidth = 0.6;\n'
        '    ctx.strokeRect(-mWid/2, -mLen/2, mWid, mLen);\n'
        '    ctx.restore();\n'
        '\n'
        '    ctx.restore();\n'
        '    plotPoints.push({ cx, cy, r: r + 3, idx: i });\n'
        '  });\n'
        '\n'
        '  // 标题标注\n'
        '  ctx.save();\n'
        "  ctx.font = 'bold 14px sans-serif';\n"
        "  ctx.fillStyle = '#999';\n"
        "  ctx.textAlign = 'center';\n"
        '  const [tx, ty] = dataToScreen(BASE_LON, BASE_LAT);\n'
        '  ctx.fillText(SITE_NAME_JS, tx, ty - rad - 8);\n'
        '  ctx.restore();\n'
        '}\n'
        '\n'
        'function parseDirection(dir) {\n'
        '  if (!dir) return null;\n'
        '  const m = dir.match(/(\\d+)/);\n'
        '  if (m) {\n'
        '    let deg = parseInt(m[1]);\n'
        '    return (deg - 90) * Math.PI / 180;\n'
        '  }\n'
        '  return null;\n'
        '}\n'
        '\n'
        'function resize() {\n'
        '  const rect = mapArea.getBoundingClientRect();\n'
        '  dpr = window.devicePixelRatio || 1;\n'
        '  W = rect.width;\n'
        '  H = rect.height;\n'
        '  canvas.width = W * dpr;\n'
        '  canvas.height = H * dpr;\n'
        '  canvas.style.width = W + "px";\n'
        '  canvas.style.height = H + "px";\n'
        '  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);\n'
        '  computeBase();\n'
        '  draw();\n'
        '}\n'
        '\n'
        'function applyZoom(factor, cx, cy) {\n'
        '  const newScale = Math.max(0.5, Math.min(12, viewScale * factor));\n'
        '  if (newScale === viewScale) return;\n'
        '  const dx = (cx - W/2) / viewScale;\n'
        '  const dy = (cy - H/2) / viewScale;\n'
        '  viewOffX = viewOffX + dx * (1 - viewScale / newScale);\n'
        '  viewOffY = viewOffY + dy * (1 - viewScale / newScale);\n'
        '  viewScale = newScale;\n'
        '  draw();\n'
        '}\n'
        '\n'
        'canvas.addEventListener("wheel", (e) => {\n'
        '  e.preventDefault();\n'
        '  const rect = canvas.getBoundingClientRect();\n'
        '  applyZoom(e.deltaY < 0 ? 1.12 : 1/1.12, '
        'e.clientX - rect.left, e.clientY - rect.top);\n'
        '}, { passive: false });\n'
        '\n'
        'canvas.addEventListener("mousedown", (e) => {\n'
        '  if (e.button !== 0) return;\n'
        '  dragging = true;\n'
        '  dragStartX = e.clientX; dragStartY = e.clientY;\n'
        '  dragOffX = viewOffX; dragOffY = viewOffY;\n'
        "  canvas.style.cursor = 'grabbing';\n"
        '});\n'
        '\n'
        'window.addEventListener("mousemove", (e) => {\n'
        '  if (dragging) {\n'
        '    viewOffX = dragOffX + (e.clientX - dragStartX) / viewScale;\n'
        '    viewOffY = dragOffY + (e.clientY - dragStartY) / viewScale;\n'
        '    draw();\n'
        "    tooltip.classList.remove('show');\n"
        '    return;\n'
        '  }\n'
        '  const rect = canvas.getBoundingClientRect();\n'
        '  const mx = e.clientX - rect.left, my = e.clientY - rect.top;\n'
        '  let found = -1;\n'
        '  for (const p of plotPoints) {\n'
        '    const dx = mx - p.cx, dy = my - p.cy;\n'
        '    if (dx*dx + dy*dy <= p.r * p.r) { found = p.idx; break; }\n'
        '  }\n'
        '  if (found !== hoveredIdx) {\n'
        '    hoveredIdx = found;\n'
        "    canvas.style.cursor = found >= 0 ? 'pointer' : 'grab';\n"
        '    draw();\n'
        '  }\n'
        '  if (found >= 0) {\n'
        '    const t = tombs[found];\n'
        "    tooltip.innerHTML = '<b>' + t.id + '</b> · ' + t.era"
        ' + (t.shape ? " · " + t.shape : "");\n'
        "    tooltip.style.left = (e.clientX + 12) + 'px';\n"
        "    tooltip.style.top = (e.clientY - 8) + 'px';\n"
        "    tooltip.classList.add('show');\n"
        '  } else {\n'
        "    tooltip.classList.remove('show');\n"
        '  }\n'
        '});\n'
        '\n'
        'window.addEventListener("mouseup", () => '
        "{ if (dragging) { dragging = false; canvas.style.cursor = 'grab'; } });\n"
        'canvas.addEventListener("mouseleave", () => '
        "{ hoveredIdx = -1; tooltip.classList.remove('show'); draw(); });\n"
        '\n'
        'canvas.addEventListener("click", (e) => {\n'
        '  if (Math.abs(e.clientX - dragStartX) > 3 '
        '|| Math.abs(e.clientY - dragStartY) > 3) return;\n'
        '  const rect = canvas.getBoundingClientRect();\n'
        '  const mx = e.clientX - rect.left, my = e.clientY - rect.top;\n'
        '  for (const p of plotPoints) {\n'
        '    const dx = mx - p.cx, dy = my - p.cy;\n'
        '    if (dx*dx + dy*dy <= p.r * p.r) { selectTomb(p.idx); return; }\n'
        '  }\n'
        '});\n'
        '\n'
        'document.getElementById("zoomIn").addEventListener("click", '
        '() => applyZoom(1.3, W/2, H/2));\n'
        'document.getElementById("zoomOut").addEventListener("click", '
        '() => applyZoom(1/1.3, W/2, H/2));\n'
        '\n'
        '// ── 侧边栏 ──\n'
        'const sidebar = document.getElementById("sidebar");\n'
        'const toggleBtn = document.getElementById("toggleBtn");\n'
        'let sidebarOpen = true;\n'
        '\n'
        'function toggleSidebar() {\n'
        '  sidebarOpen = !sidebarOpen;\n'
        "  sidebar.classList.toggle('collapsed', !sidebarOpen);\n"
        "  toggleBtn.classList.toggle('open', sidebarOpen);\n"
        "  toggleBtn.classList.toggle('closed', !sidebarOpen);\n"
        '  toggleBtn.textContent = sidebarOpen ? "◀" : "▶";\n'
        '  setTimeout(resize, 310);\n'
        '}\n'
        '\n'
        'function buildLegend() {\n'
        '  const container = document.getElementById("legend");\n'
        '  ERA_ORDER.forEach(era => {\n'
        '    const chip = document.createElement("div");\n'
        "    chip.className = 'legend-chip';\n"
        '    chip.dataset.era = era;\n'
        '    chip.innerHTML = `<div class="dot" style="background:'
        '${ERA_COLORS[era]}"></div>${era}`;\n'
        '    chip.addEventListener("click", () => toggleFilter(era));\n'
        '    container.appendChild(chip);\n'
        '  });\n'
        '}\n'
        '\n'
        'function toggleFilter(era) {\n'
        '  activeFilter = activeFilter === era ? null : era;\n'
        "  document.querySelectorAll('.legend-chip').forEach(c => {\n"
        '    c.style.opacity = !activeFilter '
        '|| c.dataset.era === activeFilter ? "1" : "0.3";\n'
        '  });\n'
        '  draw();\n'
        '}\n'
        '\n'
        'function buildTombList() {\n'
        '  const container = document.getElementById("tombList");\n'
        '  tombs.forEach((t, i) => {\n'
        '    const div = document.createElement("div");\n'
        "    div.className = 'tomb-item';\n"
        '    div.dataset.idx = i;\n'
        '    div.innerHTML = `\n'
        '      <div class="tomb-dot" style="background:${t.color}"></div>\n'
        '      <div class="tomb-info">\n'
        '        <div class="tid">${t.id}</div>\n'
        "        <div class=\"tmeta\">${t.era}${t.shape ? ' · ' + t.shape : ''}</div>\n"
        "      </div>`;\n"
        '    div.addEventListener("click", () => selectTomb(i));\n'
        '    container.appendChild(div);\n'
        '  });\n'
        '}\n'
        '\n'
        'function filterTombs(q) {\n'
        '  searchQuery = q;\n'
        "  document.querySelectorAll('.tomb-item').forEach((el, i) => {\n"
        '    const match = !q || tombs[i].id.toLowerCase().includes(q.toLowerCase());\n'
        "    el.style.display = match ? '' : 'none';\n"
        '  });\n'
        '  draw();\n'
        '}\n'
        '\n'
        'function selectTomb(idx) {\n'
        '  selectedIdx = idx;\n'
        '  const t = tombs[idx];\n'
        '\n'
        "  document.querySelectorAll('.tomb-item').forEach((el, i) => {\n"
        "    el.classList.toggle('active', i === idx);\n"
        '  });\n'
        '  const el = document.querySelector(`.tomb-item[data-idx="${idx}"]`);\n'
        "  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });\n"
        '\n'
        '  const arts = t.arts && t.arts.length ? t.arts.join("、") : "—";\n'
        '  const shape = t.shape || "—";\n'
        '  const note = t.note || "";\n'
        '\n'
        '  document.getElementById("detailPanel").innerHTML = `\n'
        '    <h2>${t.id}</h2>\n'
        '    <span class="tag" style="background:${t.color}">${t.era}</span>\n'
        '    <dl>\n'
        '      <dt>形制</dt><dd>${shape}</dd>\n'
        "      ${t.dir ? '<dt>墓向</dt><dd>' + t.dir + '</dd>' : ''}\n"
        "      ${t.length ? '<dt>墓口</dt><dd>' + t.length + '×' + t.width + 'm</dd>' : ''}\n"
        "      ${t.depth ? '<dt>墓深</dt><dd>' + t.depth + 'm</dd>' : ''}\n"
        '      <dt>器物</dt><dd>${arts}</dd>\n'
        "      ${note ? '<dt>备注</dt><dd>' + note + '</dd>' : ''}\n"
        '    </dl>`;\n'
        '\n'
        '  // 平移到墓葬\n'
        '  const [sx, sy] = dataToScreen(t.lon, t.lat);\n'
        '  viewOffX += (W/2 - sx) / viewScale;\n'
        '  viewOffY += (H/2 - sy) / viewScale;\n'
        '  draw();\n'
        '}\n'
        '\n'
        '// ── 初始化 ──\n'
        'buildLegend();\n'
        'buildTombList();\n'
        'resize();\n'
        'window.addEventListener("resize", resize);\n'
        '</script>\n'
        '</body>\n'
        '</html>'
    )


# ═══════════════════════════════════════════════════════════
# 5. 总览地图HTML模板
# ═══════════════════════════════════════════════════════════

def render_overview_map(tombs_json, sites_json, total_count, site_count,
                        era_colors_js, era_order_js):
    """生成多遗址总览地图的完整HTML。"""
    # 河北省界坐标JS
    hebei_pts = ",".join(f"[{p[0]},{p[1]}]" for p in HEBEI_OUTLINE)

    # 河流数据
    rivers_data = [
        ("滦河", 1.8,
         [[117.0, 41.2], [117.3, 40.8], [117.5, 40.3], [117.5, 39.8],
          [117.3, 39.4], [117.1, 39.0], [117.0, 38.6]]),
        ("永定河", 1.5,
         [[114.6, 40.3], [115.0, 40.0], [115.3, 39.8], [115.6, 39.6],
          [116.0, 39.5], [116.5, 39.4], [116.8, 39.3]]),
        ("大清河", 1.3,
         [[114.3, 39.4], [114.6, 39.2], [115.0, 39.0], [115.5, 38.8],
          [116.0, 38.8], [116.5, 38.8], [116.8, 38.8]]),
        ("滹沱河", 1.4,
         [[114.0, 38.4], [114.3, 38.2], [114.6, 38.0], [115.0, 37.9],
          [115.5, 38.0], [116.0, 38.1], [116.5, 38.2]]),
        ("漳河", 1.2,
         [[114.0, 36.5], [114.3, 36.4], [114.8, 36.3], [115.2, 36.3],
          [115.6, 36.3], [116.0, 36.3]]),
        ("海河", 2.0,
         [[116.8, 39.3], [117.0, 39.1], [117.2, 38.9], [117.4, 38.8]]),
    ]
    rivers_js_items = []
    for name, width, points in rivers_data:
        pts = ",".join(f"[{p[0]},{p[1]}]" for p in points)
        rivers_js_items.append(
            f'{{name:"{name}",color:"#8bbdd0",width:{width},points:[{pts}]}}'
        )
    rivers_js = "[" + ",".join(rivers_js_items) + "]"

    # 山脉数据
    taihang = [[113.9, 41.5], [114.0, 41.2], [114.1, 40.8], [114.1, 40.5],
               [114.0, 40.2], [114.0, 39.8], [114.0, 39.4], [114.1, 39.0],
               [114.0, 38.6], [114.0, 38.2], [114.1, 37.8], [114.1, 37.4],
               [114.0, 37.0], [113.9, 36.6], [113.8, 36.3], [113.7, 36.1]]
    yanshan = [[114.3, 41.2], [114.6, 41.4], [115.0, 41.7], [115.5, 41.9],
               [116.0, 41.9], [116.5, 41.7], [117.0, 41.5], [117.3, 41.3],
               [117.5, 41.1]]
    taihang_js = ",".join(f"[{p[0]},{p[1]}]" for p in taihang)
    yanshan_js = ",".join(f"[{p[0]},{p[1]}]" for p in yanshan)

    return (
        '<!DOCTYPE html>\n'
        '<html lang="zh-CN">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>NSBD墓葬分布图 — 总览</title>\n'
        '<style>\n'
        '*{margin:0;padding:0;box-sizing:border-box}\n'
        'body{font-family:-apple-system,"PingFang SC","Noto Sans SC",sans-serif;'
        'background:#f7f6f2;color:#333;font-size:14px;overflow:hidden}\n'
        '.layout{display:flex;height:100vh}\n'
        '.sidebar{width:320px;min-width:320px;height:100vh;overflow-y:auto;'
        'background:#fff;border-right:1px solid #e5e5e0;display:flex;'
        'flex-direction:column;z-index:10;transition:margin-left 0.3s ease}\n'
        '.sidebar.collapsed{margin-left:-320px}\n'
        '.sidebar::-webkit-scrollbar{width:4px}\n'
        '.sidebar::-webkit-scrollbar-thumb{background:#ddd;border-radius:2px}\n'
        '.toggle-btn{position:absolute;top:12px;z-index:11;width:36px;height:36px;'
        'border-radius:0 8px 8px 0;background:rgba(255,255,255,0.92);'
        'border:1px solid rgba(0,0,0,0.08);font-size:18px;color:#555;cursor:pointer;'
        'display:flex;align-items:center;justify-content:center;'
        'box-shadow:1px 1px 6px rgba(0,0,0,0.08);transition:left 0.3s ease}\n'
        '.toggle-btn.open{left:320px}\n'
        '.toggle-btn.closed{left:0}\n'
        '.sidebar-header{padding:20px 20px 16px;border-bottom:1px solid #eee}\n'
        '.sidebar-header h1{font-size:18px;font-weight:700;color:#1a1a1a}\n'
        '.sidebar-header .sub{font-size:13px;color:#999;margin-top:4px}\n'
        '.sidebar-stats{display:flex;gap:24px;padding:14px 20px;border-bottom:1px solid #eee}\n'
        '.stat{text-align:center}\n'
        '.stat .num{font-size:20px;font-weight:700;color:#1a1a1a}\n'
        '.stat .lbl{font-size:12px;color:#aaa;margin-top:2px}\n'
        '.legend-bar{display:flex;flex-wrap:wrap;gap:6px 12px;padding:12px 20px;'
        'border-bottom:1px solid #eee}\n'
        '.legend-chip{display:flex;align-items:center;gap:5px;font-size:13px;'
        'color:#666;cursor:pointer;transition:opacity 0.2s}\n'
        '.legend-chip:hover{opacity:0.7}\n'
        '.legend-chip .dot{width:10px;height:10px;border-radius:50%;'
        'border:1.5px solid rgba(0,0,0,0.08)}\n'
        '.site-list{flex:1;overflow-y:auto;padding:8px 10px}\n'
        '.site-item{display:flex;align-items:flex-start;gap:10px;padding:10px 12px;'
        'border-radius:8px;cursor:pointer;transition:background 0.15s}\n'
        '.site-item:hover{background:#f5f5f0}\n'
        '.site-item.active{background:#eef2ff}\n'
        '.site-dot{width:10px;height:10px;border-radius:50%;margin-top:5px;'
        'flex-shrink:0;border:1.5px solid rgba(0,0,0,0.08)}\n'
        '.site-info{flex:1;min-width:0}\n'
        '.sname{font-size:14px;font-weight:500;color:#1a1a1a}\n'
        '.smeta{font-size:12px;color:#aaa;margin-top:2px}\n'
        '.detail-panel{padding:16px 20px;border-top:1px solid #eee;background:#fafaf8;'
        'min-height:120px}\n'
        '.detail-panel h2{font-size:15px;font-weight:600;color:#1a1a1a;margin-bottom:6px}\n'
        '.detail-panel .tag{display:inline-block;padding:2px 9px;border-radius:10px;'
        'font-size:12px;color:#fff;margin-bottom:8px}\n'
        '.detail-panel dl{display:grid;grid-template-columns:auto 1fr;gap:3px 10px;'
        'font-size:13px}\n'
        '.detail-panel dt{color:#aaa}\n'
        '.detail-panel dd{color:#333}\n'
        '.detail-panel .empty{color:#ccc;font-size:13px;font-style:italic;padding:20px 0}\n'
        '.map-area{flex:1;position:relative;background:#efece4;overflow:hidden}\n'
        'canvas{display:block}\n'
        '.zoom-controls{position:absolute;bottom:20px;right:20px;z-index:10;'
        'display:flex;flex-direction:column;gap:4px}\n'
        '.zoom-btn{width:36px;height:36px;border-radius:8px;'
        'background:rgba(255,255,255,0.92);border:1px solid rgba(0,0,0,0.08);'
        'font-size:18px;color:#555;cursor:pointer;display:flex;align-items:center;'
        'justify-content:center;box-shadow:0 1px 4px rgba(0,0,0,0.06);'
        'transition:background 0.15s}\n'
        '.zoom-btn:hover{background:#fff}\n'
        '.zoom-hint{position:absolute;bottom:20px;left:50%;transform:translateX(-50%);'
        'font-size:11px;color:#bbb;pointer-events:none}\n'
        '.tooltip{position:fixed;z-index:100;background:rgba(255,255,255,0.95);'
        'border:1px solid rgba(0,0,0,0.08);border-radius:6px;padding:5px 10px;'
        'font-size:13px;box-shadow:0 2px 8px rgba(0,0,0,0.08);pointer-events:none;'
        'opacity:0;transition:opacity 0.15s;white-space:nowrap}\n'
        '.tooltip.show{opacity:1}\n'
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '\n'
        '<div class="layout">\n'
        '  <div class="sidebar" id="sidebar">\n'
        '    <div class="sidebar-header">\n'
        '      <h1>NSBD墓葬分布</h1>\n'
        '      <div class="sub">南水北调工程 · 总览地图</div>\n'
        '    </div>\n'
        '    <div class="sidebar-stats">\n'
        f'      <div class="stat"><div class="num">{total_count}</div>'
        '<div class="lbl">墓葬</div></div>\n'
        f'      <div class="stat"><div class="num">{site_count}</div>'
        '<div class="lbl">遗址</div></div>\n'
        '    </div>\n'
        '    <div class="legend-bar" id="legend"></div>\n'
        '    <div class="site-list" id="siteList"></div>\n'
        '    <div class="detail-panel" id="detailPanel">\n'
        '      <div class="empty">← 点击遗址或墓葬查看详情</div>\n'
        '    </div>\n'
        '  </div>\n'
        '\n'
        '  <button class="toggle-btn open" id="toggleBtn" '
        'onclick="toggleSidebar()">◀</button>\n'
        '\n'
        '  <div class="map-area" id="mapArea">\n'
        '    <canvas id="map"></canvas>\n'
        '    <div class="zoom-controls">\n'
        '      <div class="zoom-btn" id="zoomIn">+</div>\n'
        '      <div class="zoom-btn" id="zoomOut">−</div>\n'
        '    </div>\n'
        '    <div class="zoom-hint">滚轮缩放 · 拖拽平移 · 点击查看</div>\n'
        '  </div>\n'
        '</div>\n'
        '\n'
        '<div class="tooltip" id="tooltip"></div>\n'
        '\n'
        '<script>\n'
        f'const tombs = {tombs_json};\n'
        f'const sites = {sites_json};\n'
        '\n'
        f'const ERA_COLORS = {era_colors_js};\n'
        f'const ERA_ORDER = {era_order_js};\n'
        '\n'
        'function getColor(era) {\n'
        '  for (const [k, v] of Object.entries(ERA_COLORS)) '
        '{ if (era.includes(k)) return v; }\n'
        "  return '#94a3b8';\n"
        '}\n'
        '\n'
        '// ── 河北省界 ──\n'
        f'const hebeiOutline = [{hebei_pts}];\n'
        '\n'
        '// ── 地形 ──\n'
        f'const taihangPoints = [{taihang_js}];\n'
        f'const yanshanPoints = [{yanshan_js}];\n'
        f'const rivers = {rivers_js};\n'
        '\n'
        'const terrainLabels = [\n'
        '  {text:"太 行 山",lon:113.6,lat:38.5,rotate:-75,size:13,color:"#a09070"},\n'
        '  {text:"燕 山",lon:115.8,lat:41.8,rotate:10,size:13,color:"#a09070"},\n'
        '  {text:"华北平原",lon:116.0,lat:37.5,rotate:0,size:14,color:"#c0b8a8"},\n'
        '];\n'
        '\n'
        '// ── Canvas + viewport ──\n'
        'const canvas = document.getElementById("map");\n'
        'const ctx = canvas.getContext("2d");\n'
        'const tooltip = document.getElementById("tooltip");\n'
        'const mapArea = document.getElementById("mapArea");\n'
        '\n'
        'let W, H, dpr;\n'
        'let viewScale = 1, viewOffX = 0, viewOffY = 0;\n'
        'let plotPoints = [], hoveredIdx = -1, selectedIdx = -1;\n'
        'let dragging = false, dragStartX, dragStartY, dragOffX, dragOffY;\n'
        'let activeFilter = null;\n'
        '\n'
        '// 坐标范围\n'
        'const allLats = tombs.map(t => t.lat);\n'
        'const allLons = tombs.map(t => t.lon);\n'
        'const PAD = 0.8;\n'
        'const D_S = Math.min(...allLats) - PAD;\n'
        'const D_N = Math.max(...allLats) + PAD;\n'
        'const D_W = Math.min(...allLons) - PAD;\n'
        'const D_E = Math.max(...allLons) + PAD;\n'
        'const D_RLON = D_E - D_W;\n'
        'const D_RLAT = D_N - D_S;\n'
        '\n'
        'let baseScale, baseOX, baseOY;\n'
        '\n'
        'function computeBase() {\n'
        '  const margin = 50;\n'
        '  const usableW = W - margin * 2;\n'
        '  const usableH = H - margin * 2;\n'
        '  baseScale = Math.min(usableW / D_RLON, usableH / D_RLAT);\n'
        '  baseOX = margin + (usableW - D_RLON * baseScale) / 2 - D_W * baseScale;\n'
        '  baseOY = margin + (usableH - D_RLAT * baseScale) / 2 + D_N * baseScale;\n'
        '}\n'
        '\n'
        'function dataToScreen(lon, lat) {\n'
        '  const sx = lon * baseScale + baseOX;\n'
        '  const sy = -lat * baseScale + baseOY;\n'
        '  const cx = W / 2, cy = H / 2;\n'
        '  return [\n'
        '    cx + (sx - cx + viewOffX) * viewScale,\n'
        '    cy + (sy - cy + viewOffY) * viewScale\n'
        '  ];\n'
        '}\n'
        '\n'
        '// ── 绘制辅助 ──\n'
        'function drawSmoothLine(points, opts) {\n'
        '  opts = opts || {};\n'
        "  const color = opts.color || '#8bbdd0';\n"
        '  const width = opts.width || 1.5;\n'
        '  if (points.length < 2) return;\n'
        '  ctx.beginPath();\n'
        '  const pts = points.map(p => dataToScreen(p[0], p[1]));\n'
        '  ctx.moveTo(pts[0][0], pts[0][1]);\n'
        '  for (let i = 1; i < pts.length - 1; i++) {\n'
        '    const xc = (pts[i][0] + pts[i+1][0]) / 2;\n'
        '    const yc = (pts[i][1] + pts[i+1][1]) / 2;\n'
        '    ctx.quadraticCurveTo(pts[i][0], pts[i][1], xc, yc);\n'
        '  }\n'
        '  const last = pts[pts.length - 1];\n'
        '  ctx.lineTo(last[0], last[1]);\n'
        '  ctx.strokeStyle = color;\n'
        '  ctx.lineWidth = width * Math.min(viewScale, 2);\n'
        '  ctx.stroke();\n'
        '}\n'
        '\n'
        'function drawMountainRange(points, color) {\n'
        '  if (points.length < 2) return;\n'
        '  const peakSpacing = Math.max(8, 14 / viewScale);\n'
        '  for (let i = 0; i < points.length - 1; i++) {\n'
        '    const [x1, y1] = dataToScreen(points[i][0], points[i][1]);\n'
        '    const [x2, y2] = dataToScreen(points[i+1][0], points[i+1][1]);\n'
        '    const dx = x2 - x1, dy = y2 - y1;\n'
        '    const len = Math.sqrt(dx*dx + dy*dy);\n'
        '    if (len < 1) continue;\n'
        '    const steps = Math.max(1, Math.floor(len / peakSpacing));\n'
        '    const nx = -dy / len, ny = dx / len;\n'
        '    for (let j = 0; j <= steps; j++) {\n'
        '      const t = j / steps;\n'
        '      const bx = x1 + dx * t;\n'
        '      const by = y1 + dy * t;\n'
        '      const peakH = (6 + Math.sin(i * 3 + j * 7) * 3) '
        '* Math.min(viewScale, 2);\n'
        '      const peakW = (4 + Math.cos(i * 5 + j * 3) * 2) '
        '* Math.min(viewScale, 2);\n'
        '      ctx.beginPath();\n'
        '      ctx.moveTo(bx - nx * peakW, by - ny * peakW);\n'
        '      ctx.lineTo(bx + nx * peakH, by + ny * peakH);\n'
        '      ctx.lineTo(bx + nx * peakW, by + ny * peakW);\n'
        '      ctx.closePath();\n'
        '      ctx.fillStyle = color;\n'
        '      ctx.fill();\n'
        '    }\n'
        '  }\n'
        '}\n'
        '\n'
        '// ── 主绘制 ──\n'
        'function draw() {\n'
        '  ctx.clearRect(0, 0, W, H);\n'
        '\n'
        '  // 省界填充\n'
        '  ctx.beginPath();\n'
        '  hebeiOutline.forEach(([lon, lat], i) => {\n'
        '    const [x, y] = dataToScreen(lon, lat);\n'
        "    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);\n"
        '  });\n'
        '  ctx.closePath();\n'
        "  ctx.fillStyle = '#f0ede5';\n"
        '  ctx.fill();\n'
        '\n'
        '  // 地形梯度\n'
        '  const [x1] = dataToScreen(D_W, 0);\n'
        '  const [x2] = dataToScreen(D_E, 0);\n'
        '  const grad = ctx.createLinearGradient(x1, 0, x2, 0);\n'
        '  grad.addColorStop(0, "rgba(180,170,145,0.18)");\n'
        '  grad.addColorStop(0.35, "rgba(180,170,145,0.08)");\n'
        '  grad.addColorStop(0.6, "rgba(200,210,190,0.06)");\n'
        '  grad.addColorStop(1, "rgba(200,210,190,0.02)");\n'
        '  ctx.save();\n'
        '  ctx.beginPath();\n'
        '  hebeiOutline.forEach(([lon, lat], i) => {\n'
        '    const [x, y] = dataToScreen(lon, lat);\n'
        "    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);\n"
        '  });\n'
        '  ctx.closePath();\n'
        '  ctx.fillStyle = grad;\n'
        '  ctx.fill();\n'
        '  ctx.restore();\n'
        '\n'
        '  // 省界描边\n'
        '  ctx.beginPath();\n'
        '  hebeiOutline.forEach(([lon, lat], i) => {\n'
        '    const [x, y] = dataToScreen(lon, lat);\n'
        "    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);\n"
        '  });\n'
        '  ctx.closePath();\n'
        "  ctx.strokeStyle = '#c5c0b5';\n"
        '  ctx.lineWidth = 1.2;\n'
        '  ctx.stroke();\n'
        '\n'
        '  // 经纬网格\n'
        "  ctx.strokeStyle = 'rgba(0,0,0,0.035)';\n"
        '  ctx.lineWidth = 0.5;\n'
        '  const lonStep = viewScale > 2 ? 0.5 : 1;\n'
        '  const latStep = viewScale > 2 ? 0.5 : 1;\n'
        '  for (let lon = 113; lon <= 118; lon += lonStep) {\n'
        '    const [gx1, gy1] = dataToScreen(lon, D_S);\n'
        '    const [gx2, gy2] = dataToScreen(lon, D_N);\n'
        '    ctx.beginPath(); ctx.moveTo(gx1, gy1); ctx.lineTo(gx2, gy2); ctx.stroke();\n'
        '  }\n'
        '  for (let lat = 36; lat <= 42; lat += latStep) {\n'
        '    const [gx1, gy1] = dataToScreen(D_W, lat);\n'
        '    const [gx2, gy2] = dataToScreen(D_E, lat);\n'
        '    ctx.beginPath(); ctx.moveTo(gx1, gy1); ctx.lineTo(gx2, gy2); ctx.stroke();\n'
        '  }\n'
        '\n'
        '  // 坐标标注\n'
        '  if (viewScale >= 0.8) {\n'
        "    ctx.fillStyle = '#ccc';\n"
        '    ctx.font = (10 * Math.min(viewScale, 1.5)) + "px sans-serif";\n'
        "    ctx.textAlign = 'center';\n"
        '    for (let lon = 113; lon <= 118; lon += lonStep) {\n'
        '      const [lx, ly] = dataToScreen(lon, D_S);\n'
        '      ctx.fillText(lon + "°E", lx, Math.min(ly + 14, H - 4));\n'
        '    }\n'
        "    ctx.textAlign = 'right';\n"
        '    for (let lat = 36; lat <= 42; lat += latStep) {\n'
        '      const [lx, ly] = dataToScreen(D_W, lat);\n'
        '      ctx.fillText(lat + "°N", Math.max(lx - 6, 36), ly + 4);\n'
        '    }\n'
        '  }\n'
        '\n'
        '  // 山脉\n'
        "  drawMountainRange(taihangPoints, 'rgba(160,145,115,0.45)');\n"
        "  drawMountainRange(yanshanPoints, 'rgba(160,145,115,0.45)');\n"
        '\n'
        '  // 河流\n'
        '  rivers.forEach(r => drawSmoothLine(r.points, '
        '{color: r.color, width: r.width}));\n'
        '\n'
        '  // 河流标注\n'
        '  if (viewScale >= 1.2) {\n'
        '    ctx.font = "italic " + (11 * Math.min(viewScale, 1.5)) + "px sans-serif";\n'
        '    rivers.forEach(r => {\n'
        '      const mid = Math.floor(r.points.length / 2);\n'
        '      const [rlx, rly] = dataToScreen(r.points[mid][0], r.points[mid][1]);\n'
        '      const next = r.points[Math.min(mid + 1, r.points.length - 1)];\n'
        '      const [nx, ny] = dataToScreen(next[0], next[1]);\n'
        '      const angle = Math.atan2(ny - rly, nx - rlx);\n'
        '      ctx.save();\n'
        '      ctx.translate(rlx, rly);\n'
        '      ctx.rotate(angle);\n'
        "      ctx.fillStyle = '#9ac0d4';\n"
        "      ctx.textAlign = 'center';\n"
        '      ctx.fillText(r.name, 0, -6);\n'
        '      ctx.restore();\n'
        '    });\n'
        '  }\n'
        '\n'
        '  // 地形标注\n'
        "  ctx.textAlign = 'center';\n"
        '  terrainLabels.forEach(t => {\n'
        '    const [tlx, tly] = dataToScreen(t.lon, t.lat);\n'
        '    ctx.save();\n'
        '    ctx.translate(tlx, tly);\n'
        '    if (t.rotate) ctx.rotate(t.rotate * Math.PI / 180);\n'
        '    ctx.font = (t.size * Math.min(viewScale, 1.5)) + "px sans-serif";\n'
        '    ctx.fillStyle = t.color;\n'
        '    ctx.globalAlpha = 0.6;\n'
        '    ctx.fillText(t.text, 0, 0);\n'
        '    ctx.globalAlpha = 1;\n'
        '    ctx.restore();\n'
        '  });\n'
        '\n'
        '  // ── 遗址区域圈 ──\n'
        '  sites.forEach((s, si) => {\n'
        '    const [ssx, ssy] = dataToScreen(s.lon, s.lat);\n'
        '    const rad = 25 * Math.min(viewScale, 2);\n'
        '    ctx.save();\n'
        '    ctx.beginPath();\n'
        '    ctx.arc(ssx, ssy, rad, 0, Math.PI * 2);\n'
        "    ctx.fillStyle = getColor(s.eras[0] || '') + '15';\n"
        '    ctx.fill();\n'
        "    ctx.strokeStyle = getColor(s.eras[0] || '') + '40';\n"
        '    ctx.lineWidth = 1.5;\n'
        '    ctx.setLineDash([4, 3]);\n'
        '    ctx.stroke();\n'
        '    ctx.setLineDash([]);\n'
        '\n'
        '    if (viewScale >= 1.2) {\n'
        '      ctx.font = "bold " + (12 * Math.min(viewScale, 1.5)) + "px sans-serif";\n'
        "      ctx.fillStyle = '#555';\n"
        '      ctx.globalAlpha = 0.7;\n'
        "      ctx.textAlign = 'center';\n"
        '      ctx.fillText(s.name, ssx, ssy - rad - 6);\n'
        '      ctx.globalAlpha = 1;\n'
        '    }\n'
        '    ctx.restore();\n'
        '  });\n'
        '\n'
        '  // ── 墓葬点 ──\n'
        '  plotPoints = [];\n'
        '  tombs.forEach((t, i) => {\n'
        '    const [cx, cy] = dataToScreen(t.lon, t.lat);\n'
        '    const r = 3 * Math.min(viewScale, 2);\n'
        '    const color = t.color;\n'
        '    const isHovered = i === hoveredIdx;\n'
        '    const isSelected = i === selectedIdx;\n'
        '    const dimmed = activeFilter && !t.era.includes(activeFilter) '
        '&& !activeFilter.includes(t.era);\n'
        '\n'
        '    ctx.save();\n'
        '    ctx.globalAlpha = dimmed ? 0.08 : 1;\n'
        '\n'
        '    if (isHovered || isSelected) {\n'
        '      ctx.beginPath();\n'
        '      ctx.arc(cx, cy, r + 4, 0, Math.PI * 2);\n'
        '      ctx.fillStyle = color + "30";\n'
        '      ctx.fill();\n'
        '    }\n'
        '\n'
        '    ctx.beginPath();\n'
        '    ctx.arc(cx, cy, r, 0, Math.PI * 2);\n'
        '    ctx.fillStyle = color;\n'
        '    ctx.fill();\n'
        "    ctx.strokeStyle = 'rgba(255,255,255,0.7)';\n"
        '    ctx.lineWidth = 0.8;\n'
        '    ctx.stroke();\n'
        '\n'
        '    ctx.restore();\n'
        '    plotPoints.push({ cx, cy, r, idx: i });\n'
        '  });\n'
        '}\n'
        '\n'
        'function resize() {\n'
        '  const rect = mapArea.getBoundingClientRect();\n'
        '  dpr = window.devicePixelRatio || 1;\n'
        '  W = rect.width;\n'
        '  H = rect.height;\n'
        '  canvas.width = W * dpr;\n'
        '  canvas.height = H * dpr;\n'
        '  canvas.style.width = W + "px";\n'
        '  canvas.style.height = H + "px";\n'
        '  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);\n'
        '  computeBase();\n'
        '  draw();\n'
        '}\n'
        '\n'
        'function applyZoom(factor, cx, cy) {\n'
        '  const newScale = Math.max(0.5, Math.min(8, viewScale * factor));\n'
        '  if (newScale === viewScale) return;\n'
        '  const dx = (cx - W/2) / viewScale;\n'
        '  const dy = (cy - H/2) / viewScale;\n'
        '  viewOffX = viewOffX + dx * (1 - viewScale / newScale);\n'
        '  viewOffY = viewOffY + dy * (1 - viewScale / newScale);\n'
        '  viewScale = newScale;\n'
        '  draw();\n'
        '}\n'
        '\n'
        'canvas.addEventListener("wheel", (e) => {\n'
        '  e.preventDefault();\n'
        '  const rect = canvas.getBoundingClientRect();\n'
        '  const mx = e.clientX - rect.left;\n'
        '  const my = e.clientY - rect.top;\n'
        '  const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;\n'
        '  applyZoom(factor, mx, my);\n'
        '}, { passive: false });\n'
        '\n'
        'canvas.addEventListener("mousedown", (e) => {\n'
        '  if (e.button !== 0) return;\n'
        '  dragging = true;\n'
        '  dragStartX = e.clientX;\n'
        '  dragStartY = e.clientY;\n'
        '  dragOffX = viewOffX;\n'
        '  dragOffY = viewOffY;\n'
        "  canvas.style.cursor = 'grabbing';\n"
        '});\n'
        '\n'
        'window.addEventListener("mousemove", (e) => {\n'
        '  if (dragging) {\n'
        '    viewOffX = dragOffX + (e.clientX - dragStartX) / viewScale;\n'
        '    viewOffY = dragOffY + (e.clientY - dragStartY) / viewScale;\n'
        '    draw();\n'
        "    tooltip.classList.remove('show');\n"
        '    return;\n'
        '  }\n'
        '  const rect = canvas.getBoundingClientRect();\n'
        '  const mx = e.clientX - rect.left;\n'
        '  const my = e.clientY - rect.top;\n'
        '  let found = -1;\n'
        '  for (const p of plotPoints) {\n'
        '    const dx = mx - p.cx, dy = my - p.cy;\n'
        '    if (dx*dx + dy*dy <= (p.r + 5) * (p.r + 5)) { found = p.idx; break; }\n'
        '  }\n'
        '  if (found !== hoveredIdx) {\n'
        '    hoveredIdx = found;\n'
        "    canvas.style.cursor = found >= 0 ? 'pointer' : 'grab';\n"
        '    draw();\n'
        '  }\n'
        '  if (found >= 0 && !dragging) {\n'
        '    const t = tombs[found];\n'
        '    tooltip.textContent = t.id + " · " + t.era;\n'
        "    tooltip.style.left = (e.clientX + 12) + 'px';\n"
        "    tooltip.style.top = (e.clientY - 8) + 'px';\n"
        "    tooltip.classList.add('show');\n"
        '  } else {\n'
        "    tooltip.classList.remove('show');\n"
        '  }\n'
        '});\n'
        '\n'
        'window.addEventListener("mouseup", () => {\n'
        '  if (dragging) {\n'
        '    dragging = false;\n'
        "    canvas.style.cursor = 'grab';\n"
        '  }\n'
        '});\n'
        '\n'
        'canvas.addEventListener("mouseleave", () => {\n'
        '  hoveredIdx = -1;\n'
        "  tooltip.classList.remove('show');\n"
        '  draw();\n'
        '});\n'
        '\n'
        'canvas.addEventListener("click", (e) => {\n'
        '  if (Math.abs(e.clientX - dragStartX) > 3 '
        '|| Math.abs(e.clientY - dragStartY) > 3) return;\n'
        '  const rect = canvas.getBoundingClientRect();\n'
        '  const mx = e.clientX - rect.left;\n'
        '  const my = e.clientY - rect.top;\n'
        '  for (const p of plotPoints) {\n'
        '    const dx = mx - p.cx, dy = my - p.cy;\n'
        '    if (dx*dx + dy*dy <= (p.r + 5) * (p.r + 5)) {\n'
        '      selectTomb(p.idx);\n'
        '      return;\n'
        '    }\n'
        '  }\n'
        '});\n'
        '\n'
        'document.getElementById("zoomIn").addEventListener("click", '
        '() => applyZoom(1.3, W/2, H/2));\n'
        'document.getElementById("zoomOut").addEventListener("click", '
        '() => applyZoom(1/1.3, W/2, H/2));\n'
        '\n'
        '// ── 侧边栏 ──\n'
        'const sidebar = document.getElementById("sidebar");\n'
        'const toggleBtn = document.getElementById("toggleBtn");\n'
        'let sidebarOpen = true;\n'
        '\n'
        'function toggleSidebar() {\n'
        '  sidebarOpen = !sidebarOpen;\n'
        "  sidebar.classList.toggle('collapsed', !sidebarOpen);\n"
        "  toggleBtn.classList.toggle('open', sidebarOpen);\n"
        "  toggleBtn.classList.toggle('closed', !sidebarOpen);\n"
        '  toggleBtn.textContent = sidebarOpen ? "◀" : "▶";\n'
        '  setTimeout(resize, 310);\n'
        '}\n'
        '\n'
        'function buildLegend() {\n'
        '  const container = document.getElementById("legend");\n'
        '  ERA_ORDER.forEach(era => {\n'
        '    const chip = document.createElement("div");\n'
        "    chip.className = 'legend-chip';\n"
        '    chip.dataset.era = era;\n'
        '    chip.innerHTML = `<div class="dot" style="background:'
        '${ERA_COLORS[era]}"></div>${era}`;\n'
        '    chip.addEventListener("click", () => toggleFilter(era));\n'
        '    container.appendChild(chip);\n'
        '  });\n'
        '}\n'
        '\n'
        'function toggleFilter(era) {\n'
        '  activeFilter = activeFilter === era ? null : era;\n'
        "  document.querySelectorAll('.legend-chip').forEach(c => {\n"
        '    c.style.opacity = !activeFilter '
        '|| c.dataset.era === activeFilter ? "1" : "0.3";\n'
        '  });\n'
        '  draw();\n'
        '}\n'
        '\n'
        'function buildSiteList() {\n'
        '  const container = document.getElementById("siteList");\n'
        '  sites.forEach((s, i) => {\n'
        '    const div = document.createElement("div");\n'
        "    div.className = 'site-item';\n"
        '    div.dataset.idx = i;\n'
        "    const color = getColor(s.eras[0] || '');\n"
        '    div.innerHTML = `\n'
        '      <div class="site-dot" style="background:${color}"></div>\n'
        '      <div class="site-info">\n'
        '        <div class="sname">${s.name}</div>\n'
        '        <div class="smeta">${s.era_span} · ${s.count}座 · ${s.county}</div>\n'
        '      </div>`;\n'
        '    div.addEventListener("click", () => selectSite(i));\n'
        '    container.appendChild(div);\n'
        '  });\n'
        '}\n'
        '\n'
        'function selectSite(idx) {\n'
        '  const s = sites[idx];\n'
        "  document.querySelectorAll('.site-item').forEach((el, i) => {\n"
        "    el.classList.toggle('active', i === idx);\n"
        '  });\n'
        "  const color = getColor(s.eras[0] || '');\n"
        '  document.getElementById("detailPanel").innerHTML = `\n'
        '    <h2>${s.name}</h2>\n'
        '    <span class="tag" style="background:${color}">${s.era_span}</span>\n'
        '    <dl>\n'
        '      <dt>位置</dt><dd>${s.county}</dd>\n'
        '      <dt>墓葬</dt><dd>${s.count} 座 · ${s.tomb_type}</dd>\n'
        "      <dt>代表器物</dt><dd>${s.arts.length ? s.arts.join('、') : '—'}</dd>\n"
        '    </dl>`;\n'
        '  const [ssx, ssy] = dataToScreen(s.lon, s.lat);\n'
        '  viewOffX += (W/2 - ssx) / viewScale;\n'
        '  viewOffY += (H/2 - ssy) / viewScale;\n'
        '  draw();\n'
        '}\n'
        '\n'
        'function selectTomb(idx) {\n'
        '  selectedIdx = idx;\n'
        '  const t = tombs[idx];\n'
        "  document.querySelectorAll('.site-item').forEach(el => el.classList.remove('active'));\n"
        '\n'
        '  const arts = t.arts && t.arts.length ? t.arts.join("、") : "—";\n'
        '  const shape = t.shape || "—";\n'
        '  const note = t.note || "";\n'
        '\n'
        '  document.getElementById("detailPanel").innerHTML = `\n'
        '    <h2>${t.id}</h2>\n'
        '    <span class="tag" style="background:${t.color}">${t.era}</span>\n'
        '    <dl>\n'
        '      <dt>遗址</dt><dd>${t.loc}</dd>\n'
        '      <dt>形制</dt><dd>${shape}</dd>\n'
        "      ${t.dir ? '<dt>墓向</dt><dd>' + t.dir + '</dd>' : ''}\n"
        "      ${t.length ? '<dt>尺寸</dt><dd>' + t.length + '×' + t.width + 'm</dd>' : ''}\n"
        '      <dt>器物</dt><dd>${arts}</dd>\n'
        "      ${note ? '<dt>备注</dt><dd>' + note + '</dd>' : ''}\n"
        '    </dl>`;\n'
        '\n'
        '  const [tsx, tsy] = dataToScreen(t.lon, t.lat);\n'
        '  viewOffX += (W/2 - tsx) / viewScale;\n'
        '  viewOffY += (H/2 - tsy) / viewScale;\n'
        '  draw();\n'
        '}\n'
        '\n'
        '// ── 初始化 ──\n'
        'buildLegend();\n'
        'buildSiteList();\n'
        'resize();\n'
        'window.addEventListener("resize", resize);\n'
        '</script>\n'
        '</body>\n'
        '</html>'
    )


# ═══════════════════════════════════════════════════════════
# 6. 编程式API
# ═══════════════════════════════════════════════════════════

def generate_gis(
    inputs,                     # list of CSV paths or Path objects
    *,                          # keyword-only below
    outdir=None,                # None = don't write files
    overview=False,
    site_presets=None,          # {site_key: {name, lat, lon, county, geo}}
    write_files=True,
    return_html=False,          # True → return dict of HTML strings
    random_seed=42,
    coord_mode="auto",          # "auto" | "exact" | "jitter" | "none"
):
    """主API — 接受任意考古CSV,生成交互式GIS地图。

    参数:
        inputs: CSV文件路径列表或包含CSV的目录
        outdir: 输出目录 (None则不写文件)
        overview: 是否生成总览地图
        site_presets: 遗址预设 {site_key: {name, lat, lon, county, geo}}
        write_files: 是否写入HTML文件
        return_html: 是否在返回值中包含HTML字符串
        random_seed: 随机种子
        coord_mode: "auto" | "exact" | "jitter" | "none"

    返回:
        {
            "sites": {site_key: html_str} 或 {},
            "overview": html_str 或 None,
            "stats": {total_tombs, site_count, coord_mode, ...}
        }
    """
    presets = dict(SITE_PRESETS)  # 以NSBD预设为默认基底
    if site_presets:
        presets.update(site_presets)

    # 收集CSV文件
    csv_files = []
    for inp in inputs:
        p = Path(inp)
        if p.is_dir():
            csv_files.extend(sorted(p.glob("*.csv")))
        elif p.is_file() and p.suffix == ".csv":
            csv_files.append(p)

    if not csv_files:
        return {"sites": {}, "overview": None, "stats": {"error": "未找到CSV文件"}}

    # 为每个CSV检测元数据
    site_metas_map = {}
    for fpath in csv_files:
        key = csv_key(fpath.name)
        with open(fpath, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        preset = presets.get(key)
        meta = detect_site_metadata(fpath, rows, preset)
        site_metas_map[key] = meta

    # 解析墓葬
    random.seed(random_seed)
    tomb_data, site_tombs, site_metas = parse_tombs(
        csv_files, site_metas_map, coord_mode=coord_mode, random_seed=random_seed,
    )

    if not tomb_data:
        return {"sites": {}, "overview": None, "stats": {"error": "未提取到墓葬数据"}}

    # JS常量
    era_colors_js = _safe_json(ERA_COLORS)
    present_eras = set()
    for t in tomb_data:
        for k in ERA_COLORS:
            if k in t["era"]:
                present_eras.add(k)
    ordered = [e for e in ERA_ORDER_LIST if e in present_eras]
    for e in sorted(present_eras):
        if e not in ordered:
            ordered.append(e)
    era_order_js = _safe_json(ordered)

    result_sites = {}
    outdir_path = Path(outdir) if outdir else None

    # 生成站点地图
    for key, tombs in site_tombs.items():
        meta = site_metas_map.get(key, {})
        site_name = meta.get("name", key)
        county = meta.get("county", "未知")
        lat = meta.get("lat", 37.0)
        lon = meta.get("lon", 115.0)
        geo = meta.get("geo", [])

        smeta = site_metas.get(key, {})
        eras = smeta.get("eras", set())
        shapes = smeta.get("shapes", Counter())
        all_arts = smeta.get("all_arts", Counter())

        era_span = era_range_str(eras)
        tomb_type = "、".join(t for t, _ in shapes.most_common(2)) or "未知"
        top_arts = [a for a, _ in all_arts.most_common(5)]
        top_arts_str = "、".join(top_arts) if top_arts else "无"

        tombs_json = _safe_json(tombs)

        html_str = render_site_map(
            site_name=site_name,
            county=county,
            era_span=era_span,
            tomb_type=tomb_type,
            top_arts_str=top_arts_str,
            fname=f"{key}.csv",
            tombs_json=tombs_json,
            base_lat=lat,
            base_lon=lon,
            geo_features=geo,
            era_colors_js=era_colors_js,
            era_order_js=era_order_js,
        )

        if return_html:
            result_sites[key] = html_str

        if write_files and outdir_path:
            sites_dir = outdir_path / "sites"
            sites_dir.mkdir(parents=True, exist_ok=True)
            outfile = sites_dir / f"{key}.html"
            with open(outfile, "w", encoding="utf-8") as f:
                f.write(html_str)
            print(f"  ✅ {outfile} ({len(tombs)} 座墓)")

    # 生成总览地图
    overview_html = None
    if overview and len(site_tombs) > 1:
        overview_sites = []
        for key, tombs in site_tombs.items():
            meta = site_metas_map.get(key, {})
            smeta = site_metas.get(key, {})
            eras = smeta.get("eras", set())
            all_arts = smeta.get("all_arts", Counter())
            shapes = smeta.get("shapes", Counter())

            top_eras = [e for e, _ in Counter(
                e for t in tombs for e in [t["era"]] if e != "未知"
            ).most_common(3)]
            top_arts_list = [a for a, _ in all_arts.most_common(6)]

            overview_sites.append({
                "name": meta.get("name", key),
                "key": key,
                "lat": meta.get("lat", 37.0),
                "lon": meta.get("lon", 115.0),
                "county": meta.get("county", "未知"),
                "era_span": era_range_str(eras),
                "tomb_type": "、".join(t for t, _ in shapes.most_common(2)) or "未知",
                "count": len(tombs),
                "eras": top_eras,
                "arts": top_arts_list,
            })

        overview_tombs = []
        for t in tomb_data:
            entry = dict(t)
            entry["loc"] = "未知"
            for key2, tombs2 in site_tombs.items():
                if any(tt["id"] == t["id"] for tt in tombs2):
                    entry["loc"] = site_metas_map.get(key2, {}).get("name", key2)
                    break
            overview_tombs.append(entry)

        overview_json = _safe_json(overview_tombs)
        sites_json = _safe_json(overview_sites)

        overview_html = render_overview_map(
            tombs_json=overview_json,
            sites_json=sites_json,
            total_count=len(tomb_data),
            site_count=len(site_tombs),
            era_colors_js=era_colors_js,
            era_order_js=era_order_js,
        )

        if write_files and outdir_path:
            outfile = outdir_path / "overview.html"
            with open(outfile, "w", encoding="utf-8") as f:
                f.write(overview_html)
            print(f"  ✅ {outfile} (全部 {len(tomb_data)} 座墓)")

        if return_html:
            pass  # overview_html already set

    stats = {
        "total_tombs": len(tomb_data),
        "site_count": len(site_tombs),
        "sites": {k: len(v) for k, v in site_tombs.items()},
        "coord_mode": coord_mode,
    }

    return {
        "sites": result_sites,
        "overview": overview_html if return_html else None,
        "stats": stats,
    }


# ═══════════════════════════════════════════════════════════
# 7. CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="墓葬GIS生成器 — 任意CSV → 交互式Canvas地图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python nsbd_gis.py data/                      # 扫描目录,生成所有站点\n"
            "  python nsbd_gis.py data/ --overview           # + 总览地图\n"
            "  python nsbd_gis.py data/nsbd-11.csv           # 单站点\n"
            "  python nsbd_gis.py data/nsbd-11.csv --name 滏阳营 --lat 36.37 --lon 114.30\n"
            "  python nsbd_gis.py data/ --discover            # 仅扫描,不生成\n"
            "  python nsbd_gis.py new_site.csv --coord-mode exact  # 使用CSV中的精确坐标\n"
        ),
    )
    parser.add_argument(
        "inputs", nargs="+",
        help="CSV文件路径,或包含CSV的目录",
    )
    parser.add_argument("--outdir", default="output", help="输出目录 (默认: output)")
    parser.add_argument("--overview", action="store_true", help="同时生成总览地图")
    parser.add_argument("--discover", action="store_true", help="仅扫描CSV,不生成地图")
    parser.add_argument("--name", help="覆盖站点名称 (仅单站点模式)")
    parser.add_argument("--lat", type=float, help="覆盖纬度 (仅单站点模式)")
    parser.add_argument("--lon", type=float, help="覆盖经度 (仅单站点模式)")
    parser.add_argument(
        "--coord-mode", default="auto",
        choices=["auto", "exact", "jitter", "none"],
        help="坐标模式: auto=自动检测, exact=CSV精确坐标, jitter=遗址中心+偏移, none=遗址中心",
    )
    args = parser.parse_args()

    # 收集CSV文件
    csv_files = []
    for inp in args.inputs:
        p = Path(inp)
        if p.is_dir():
            csv_files.extend(sorted(p.glob("*.csv")))
        elif p.is_file() and p.suffix == ".csv":
            csv_files.append(p)
        else:
            print(f"⚠️  跳过: {inp} (不是CSV文件或目录)")

    if not csv_files:
        print("❌ 未找到CSV文件")
        sys.exit(1)

    print(f"📁 找到 {len(csv_files)} 个CSV文件:")
    for f in csv_files:
        print(f"    {f}")

    # discover模式
    if args.discover:
        print("\n--- 扫描模式 (不生成地图) ---")
        for f in csv_files:
            key = csv_key(f.name)
            preset = SITE_PRESETS.get(key)
            with open(f, encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
            eras = set()
            lat_col, lon_col = detect_coord_columns(
                list(rows[0].keys()) if rows else []
            )
            for r in rows:
                e = (r.get("年代") or "").strip()
                if e:
                    eras.add(e)
            era_str = ", ".join(sorted(eras)) if eras else "无"
            coord_info = ""
            if lat_col:
                coord_info = f" | 坐标列: {lat_col}/{lon_col}"
            status = "✅ 有预设" if preset else "⚠️  无预设 (将自动检测或用 --lat/--lon)"
            print(f"  {f.name}: {len(rows)}行 | 年代: {era_str}{coord_info} | {status}")
        return

    # CLI覆盖: 单站点模式下构建site_presets
    site_presets_override = None
    if args.lat is not None and args.lon is not None:
        if len(csv_files) == 1:
            key = csv_key(csv_files[0].name)
            site_presets_override = {
                key: {
                    "name": args.name or key,
                    "lat": args.lat,
                    "lon": args.lon,
                    "county": "自定义",
                    "geo": [],
                }
            }
        else:
            print("⚠️  --lat/--lon 仅在单站点模式下有效")

    # 调用API
    print(f"\n🔍 解析中... (坐标模式: {args.coord_mode})")
    result = generate_gis(
        csv_files,
        outdir=args.outdir,
        overview=args.overview,
        site_presets=site_presets_override,
        write_files=True,
        return_html=False,
        random_seed=42,
        coord_mode=args.coord_mode,
    )

    stats = result["stats"]
    if "error" in stats:
        print(f"❌ {stats['error']}")
        sys.exit(1)

    print(f"\n✨ 完成! 共 {stats['total_tombs']} 座墓, {stats['site_count']} 个遗址")
    print(f"   输出目录: {args.outdir}/")


if __name__ == "__main__":
    main()
