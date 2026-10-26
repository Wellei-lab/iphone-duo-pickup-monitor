#!/usr/bin/env python3
"""列出若干邮编附近 Apple 返回的门店（名字、城市、州、坐标、距离），用来决定监控范围。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitor import DEFAULT_PARTS, fetch_availability, store_distance  # noqa: E402

parts = DEFAULT_PARTS.split(",")
for loc in sys.argv[1:]:
    _, stores = fetch_availability(loc, parts)
    print(f"== {loc}: {len(stores)} 家")
    for s in stores:
        print(f"  {s.get('storeNumber')} | {s.get('storeName')} | {s.get('city')}, {s.get('state')} | "
              f"{s.get('storelatitude')},{s.get('storelongitude')} | {store_distance(s)} mi")
