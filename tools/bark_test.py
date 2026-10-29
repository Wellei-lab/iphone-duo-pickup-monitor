#!/usr/bin/env python3
"""发一条测试推送，点开应直接进入 Apple Store App 的购物袋。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitor import PRODUCT_URL, bark  # noqa: E402

bark("测试：点我打开购物袋", "点开后应该进入 Apple Store App 的 Bag 页面", url=PRODUCT_URL)
