

"""MR 新游戏启动器 v39.0 —— config 模块（由 MRNewGameLauncher39.0.py 模块化重构而来，逻辑保持不变）。"""

# 全局版本号  
VERSION = "39.0"

# 作者名
AUTHOR = "admin"

# 作者博客
BLOG = "https://admin.com"

# 固定盐值
FIXED_SALT = b"MRNewGameLauncherDataBackupSalt"

# 更新日志数据结构
CHANGELOG = [
    ("1.0", "2024.01.01-11:11", [
        ("其他", ["初始版本，使用python重写了原游戏启动器"])
    ]),
]
