"""City search for the weather app: Open-Meteo geocoding online, a built-in list offline.

The clock's weather app takes a city name or coordinates (coordinates win), so a pick
from here sets `city`, `lat` and `lon` together.
"""

import json
import urllib.parse
import urllib.request

GEOCODER = "https://geocoding-api.open-meteo.com/v1/search"

# name_en, name_zh, region, lat, lon — major cities, used when the geocoder is unreachable.
OFFLINE = [
    ("Beijing", "北京", "China", 39.9042, 116.4074),
    ("Shanghai", "上海", "China", 31.2304, 121.4737),
    ("Guangzhou", "广州", "China", 23.1291, 113.2644),
    ("Shenzhen", "深圳", "China", 22.5431, 114.0579),
    ("Hangzhou", "杭州", "China", 30.2741, 120.1551),
    ("Chengdu", "成都", "China", 30.5728, 104.0668),
    ("Chongqing", "重庆", "China", 29.5630, 106.5516),
    ("Wuhan", "武汉", "China", 30.5928, 114.3055),
    ("Nanjing", "南京", "China", 32.0603, 118.7969),
    ("Xi'an", "西安", "China", 34.3416, 108.9398),
    ("Tianjin", "天津", "China", 39.3434, 117.3616),
    ("Suzhou", "苏州", "China", 31.2990, 120.5853),
    ("Hong Kong", "香港", "China", 22.3193, 114.1694),
    ("Macau", "澳门", "China", 22.1987, 113.5439),
    ("Taipei", "台北", "Taiwan", 25.0330, 121.5654),
    ("Singapore", "新加坡", "Singapore", 1.3521, 103.8198),
    ("Tokyo", "东京", "Japan", 35.6762, 139.6503),
    ("Osaka", "大阪", "Japan", 34.6937, 135.5023),
    ("Seoul", "首尔", "South Korea", 37.5665, 126.9780),
    ("Bangkok", "曼谷", "Thailand", 13.7563, 100.5018),
    ("Sydney", "悉尼", "Australia", -33.8688, 151.2093),
    ("Melbourne", "墨尔本", "Australia", -37.8136, 144.9631),
    ("Brisbane", "布里斯班", "Australia", -27.4698, 153.0251),
    ("Perth", "珀斯", "Australia", -31.9505, 115.8605),
    ("Adelaide", "阿德莱德", "Australia", -34.9285, 138.6007),
    ("Canberra", "堪培拉", "Australia", -35.2809, 149.1300),
    ("Auckland", "奥克兰", "New Zealand", -36.8485, 174.7633),
    ("London", "伦敦", "United Kingdom", 51.5072, -0.1276),
    ("Paris", "巴黎", "France", 48.8566, 2.3522),
    ("Berlin", "柏林", "Germany", 52.5200, 13.4050),
    ("Amsterdam", "阿姆斯特丹", "Netherlands", 52.3676, 4.9041),
    ("New York", "纽约", "United States", 40.7128, -74.0060),
    ("Los Angeles", "洛杉矶", "United States", 34.0522, -118.2437),
    ("San Francisco", "旧金山", "United States", 37.7749, -122.4194),
    ("Seattle", "西雅图", "United States", 47.6062, -122.3321),
    ("Chicago", "芝加哥", "United States", 41.8781, -87.6298),
    ("Toronto", "多伦多", "Canada", 43.6532, -79.3832),
    ("Vancouver", "温哥华", "Canada", 49.2827, -123.1207),
    ("Dubai", "迪拜", "United Arab Emirates", 25.2048, 55.2708),
]


COUNTRY_ZH = {
    "China": "中国",
    "Taiwan": "台湾",
    "Singapore": "新加坡",
    "Japan": "日本",
    "South Korea": "韩国",
    "Thailand": "泰国",
    "Australia": "澳大利亚",
    "New Zealand": "新西兰",
    "United Kingdom": "英国",
    "France": "法国",
    "Germany": "德国",
    "Netherlands": "荷兰",
    "United States": "美国",
    "Canada": "加拿大",
    "United Arab Emirates": "阿联酋",
}


def _offline(query, lang):
    q = query.casefold()
    zh_ui = lang == "zh"
    return [
        {
            "name": zh if zh_ui else en,
            "region": COUNTRY_ZH.get(region, region) if zh_ui else region,
            "lat": lat,
            "lon": lon,
        }
        for en, zh, region, lat, lon in OFFLINE
        if not q or q in en.casefold() or q in zh
    ][:8]


def search(query, lang="en", fetch=None):
    """Up to 8 matches: {"name", "region", "lat", "lon"}, plus which source answered."""
    query = query.strip()[:60]
    if not query:
        return {"source": "offline", "results": _offline("", lang)}
    url = (
        GEOCODER
        + "?"
        + urllib.parse.urlencode(
            {
                "name": query,
                "count": 8,
                "language": "zh" if lang == "zh" else "en",
                "format": "json",
            }
        )
    )
    try:
        # Internet, not the LAN: the default opener honours HTTP(S)_PROXY on purpose.
        body = (fetch or _fetch)(url)
        results = [
            {
                "name": r["name"],
                "region": ", ".join(x for x in (r.get("admin1"), r.get("country")) if x),
                "lat": round(float(r["latitude"]), 4),
                "lon": round(float(r["longitude"]), 4),
            }
            for r in json.loads(body).get("results") or []
        ]
    except OSError, ValueError, KeyError, TypeError:
        return {"source": "offline", "results": _offline(query, lang)}
    # The geocoder needs whole words ("墨尔本", not "墨尔"); the built-in list matches
    # prefixes, so its hits go first and duplicates from the geocoder are dropped.
    local = _offline(query, lang)
    online = [r for r in results if not any(_near(r, x) for x in local)]
    return {"source": "open-meteo", "results": (local + online)[:8]}


def _near(a, b):
    return abs(a["lat"] - b["lat"]) < 0.3 and abs(a["lon"] - b["lon"]) < 0.3


def _fetch(url):
    with urllib.request.urlopen(url, timeout=4) as resp:
        return resp.read()
