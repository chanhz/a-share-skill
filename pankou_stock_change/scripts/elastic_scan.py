#!/usr/bin/env python3
"""弹性板离线扫描入口 — 等价于 buy_signal_elastic.py --no-monitor"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from buy_signal_elastic import main as _main

if __name__ == "__main__":
    sys.argv.insert(1, "--no-monitor")
    _main()
