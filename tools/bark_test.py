#!/usr/bin/env python3
"""发几条不同设置的 Bark 测试推送，看哪种在手机解锁使用时会在屏幕顶部弹出。"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitor import bark  # noqa: E402

tests = [
    ("测试 A：时效性 + 连响 30 秒（现在的有货推送）", {"level": "timeSensitive", "call": True}),
    ("测试 B：时效性，不连响", {"level": "timeSensitive"}),
    ("测试 C：普通（现在的已售罄推送）", {"level": "active"}),
]
for i, (title, kwargs) in enumerate(tests):
    if i:
        time.sleep(45)  # 等上一条的铃声响完
    bark(title, "看到这条在屏幕顶部弹出了吗？", **kwargs)
