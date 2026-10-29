#!/usr/bin/env python3
"""测试哪种链接点开推送能直接进入 Apple Store App（最好直接到 Bag 页）。

applestore:// 是 Apple Store App 的打开方式（社区整理的列表里有，Apple 未公开文档），
后面两条试试能不能直接跳到购物袋。
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitor import bark  # noqa: E402

tests = [
    ("测试 A", "applestore://"),
    ("测试 B", "applestore://bag"),
    ("测试 C", "applestore://www.apple.com/shop/bag"),
]
for i, (title, url) in enumerate(tests):
    if i:
        time.sleep(20)
    bark(title, "点我，看看打开了哪里", url=url, level="active")
