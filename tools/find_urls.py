#!/usr/bin/env python3
"""在 iPhone Duo 购买页里找各型号对应的商品链接，用来让推送直接打开那一款。"""

import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitor import BUY_URL, DEFAULT_PARTS, HEADERS  # noqa: E402

req = urllib.request.Request(BUY_URL, headers={**HEADERS, "Accept": "text/html"})
page = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
print("页面长度", len(page))
links = sorted(set(re.findall(r'(/shop/buy-iphone/iphone-duo/[a-z0-9\-]+)', page)))
print("购买页里的 iphone-duo 子链接：", links[:40])
for part in DEFAULT_PARTS.split(","):
    for m in list(re.finditer(re.escape(part), page))[:3]:
        print(f"--- {part} @ {m.start()}:", page[max(0, m.start() - 300):m.start() + 300].replace("\n", " "))
for url in ["https://www.apple.com/shop/product/MK1H4LL/A",
            "https://www.apple.com/shop/buy-iphone/iphone-duo/512gb-night-sky"]:
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={**HEADERS, "Accept": "text/html"}), timeout=20)
        print("试链接", url, "->", r.status, r.geturl())
    except Exception as exc:
        print("试链接", url, "->", exc)
