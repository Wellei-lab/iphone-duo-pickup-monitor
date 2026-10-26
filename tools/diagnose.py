#!/usr/bin/env python3
"""诊断 Apple 取货接口：分别试几种请求方式，打印状态码和响应开头，判断是 IP 被拦还是型号不对。"""

import http.cookiejar
import os
import re
import urllib.error
import urllib.parse
import urllib.request

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitor import BUY_URL, HEADERS, DEFAULT_PARTS  # noqa: E402

ZIP = os.environ.get("ZIP", "10001")
PARTS = DEFAULT_PARTS.split(",")
AIRPODS = "MTJV3AM/A"  # AirPods Pro 2 USB-C，长期在售，用来对照

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def get(label, url, use_cookies=False, headers=None):
    req = urllib.request.Request(url, headers=headers or HEADERS)
    try:
        resp = (opener if use_cookies else urllib.request.build_opener()).open(req, timeout=20)
        body = resp.read().decode("utf-8", "replace")
        print(f"[{label}] {resp.status} {len(body)} bytes: {body[:200]!r}")
        return body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        print(f"[{label}] HTTP {exc.code}: {body[:200]!r}")
    except Exception as exc:
        print(f"[{label}] 失败：{exc}")
    return ""


def fulfillment(parts, minimal=False):
    q = {"pl": "true", "location": ZIP} if minimal else {
        "fae": "true", "pl": "true", "mts.0": "regular", "mts.1": "compact",
        "searchNearby": "true", "location": ZIP}
    for i, p in enumerate(parts):
        q[f"parts.{i}"] = p
    return "https://www.apple.com/shop/fulfillment-messages?" + urllib.parse.urlencode(q)


page = get("购买页", BUY_URL, use_cookies=True,
           headers={**HEADERS, "Accept": "text/html,application/xhtml+xml"})
found = sorted(set(re.findall(r"\b(M[A-Z0-9]{4}LL/A)\b", page)))
print(f"购买页里的型号（{len(found)} 个）：{found}")
print("购买页里 MK1G4LL/A 出现：", "MK1G4LL/A" in page, " MK1H4LL/A 出现：", "MK1H4LL/A" in page)

get("当前参数 iPhone Duo", fulfillment(PARTS))
get("精简参数 iPhone Duo", fulfillment(PARTS, minimal=True))
get("带 cookie iPhone Duo", fulfillment(PARTS), use_cookies=True)
get("当前参数 AirPods 对照", fulfillment([AIRPODS]))
get("带 cookie AirPods 对照", fulfillment([AIRPODS]), use_cookies=True)
if found:
    get("购买页第一个型号", fulfillment(found[:1]), use_cookies=True)
raw = get("旧接口 pickup-message", "https://www.apple.com/shop/retail/pickup-message?"
          + urllib.parse.urlencode({"pl": "true", "parts.0": PARTS[0], "parts.1": PARTS[1], "location": ZIP}))
if raw:
    import json
    stores = json.loads(raw)["body"]["stores"]
    first = {k: v for k, v in stores[0].items() if k in (
        "storeName", "storeNumber", "city", "storedistance", "storeDistanceWithUnit", "partsAvailability")}
    print("第一家门店：", json.dumps(first, ensure_ascii=False)[:600])
    for st in stores:
        small = {k: v for k, v in st.items() if not isinstance(v, (dict, list)) and "distance" in k.lower()}
        print("门店：", st.get("storeName"), st.get("city"), small)
    print("门店字段：", sorted(stores[0].keys()))
