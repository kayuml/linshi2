#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MR 新游戏启动器 v39.0 —— 程序入口（模块化重构版）。

原单文件 MRNewGameLauncher39.0.py 已拆分为 mr_launcher 包，
本文件仅作为启动入口保留，运行方式与原程序完全一致：
    python MRNewGameLauncher39_0_main.py
"""

from mr_launcher.main import menu

if __name__ == "__main__":
    menu()  # 运行主菜单
