"""MR 新游戏启动器 v39.0 —— config 模块。

全局常量集中定义处：版本信息、数据目录与文件名、文件编码、加密参数、
WebDAV 备份参数、安全验证参数与更新日志。
其他模块一律从这里导入常量，不再各自硬编码。
"""

import re

# ==================== 基本信息 ====================

# 全局版本号
VERSION = "40.0"

# 作者名
AUTHOR = "admin"

# 作者博客
BLOG = "https://admin.com"

# ==================== 数据目录与文件名 ====================

# 数据文件夹名（位于所选盘符根目录下）
DATA_FOLDER_NAME = "MRNewGameLauncherData"

# 版本文件名
VERSION_FILE_NAME = "MRNewGameLauncherConfigVersion.txt"

# 游戏列表文件名
GAME_LIST_FILE_NAME = "MRNewGameLauncherGameList.txt"

# 安全配置文件名（TOTP 密钥、验证频率、Windows Hello 选项）
SAFE_CONFIG_FILE_NAME = "MRNewGameLauncherSafeConfig.txt"

# WebDAV 配置文件名
WEBDAV_CONFIG_FILE_NAME = "MRNewGameLauncherWebDAVConfig.txt"

# 崩溃日志文件名
CRASH_LOG_FILE_NAME = "MRNewGameLauncherCrashLog.txt"

# 紧急备用日志文件名（崩溃日志写入失败时使用，位于当前工作目录）
EMERGENCY_LOG_FILE_NAME = "crash_emergency.log"

# ==================== 文件编码与 Windows 文件属性 ====================

# 数据文件统一编码（游戏列表/安全配置/WebDAV 配置/备份内容）
DATA_FILE_ENCODING = "GB18030"

# 日志文件编码
LOG_FILE_ENCODING = "utf-8"

# 版本文件统一编码（使用UTF-8以确保所有文本编辑器自动识别不乱码）
VERSION_FILE_ENCODING = "utf-8"

# Windows 文件属性：隐藏
FILE_ATTRIBUTE_HIDDEN = 0x02

# Windows 文件属性：正常
FILE_ATTRIBUTE_NORMAL = 0x80

# ==================== 加密参数 ====================

# 固定盐值
FIXED_SALT = b"MRNewGameLauncherDataBackupSalt"

# PBKDF2 迭代次数
PBKDF2_ITERATIONS = 100000

# AES 密钥长度（字节），32 字节 = 256 位
AES_KEY_LENGTH = 32

# AES-GCM nonce 长度（字节）
AES_GCM_NONCE_LENGTH = 12

# ==================== WebDAV 与备份 ====================

# WebDAV 客户端编码（确保文件名和路径正确处理）
WEBDAV_ENCODING = "utf-8"

# WebDAV 连接测试最大尝试次数
WEBDAV_MAX_ATTEMPTS = 3

# WebDAV 连接重试间隔（秒）
WEBDAV_RETRY_DELAY = 1

# 远程备份目录名
BACKUP_DIR_NAME = "MRNewGameLauncherDataBackup"

# 备份文件名前缀/后缀
BACKUP_FILE_PREFIX = "backup_"
BACKUP_FILE_SUFFIX = ".zip"

# 备份时间戳格式（用于生成备份文件名并派生加密密钥）
BACKUP_TIMESTAMP_FORMAT = "%Y.%m.%d_%H-%M-%S"

# 备份文件名匹配正则（从文件名中提取时间戳）
BACKUP_FILENAME_PATTERN = (
    re.escape(BACKUP_FILE_PREFIX)
    + r"(\d{4}\.\d{2}\.\d{2}_\d{2}-\d{2}-\d{2})"
    + re.escape(BACKUP_FILE_SUFFIX)
)

# 备份包内映射表文件名（混淆文件名 -> 原始文件名）
MANIFEST_FILE_NAME = "manifest.mrmap"

# 备份包内校验文件名（文件名:SHA256 哈希值）
CHECKSUM_FILE_NAME = "checksum.sha256"

# 混淆文件名随机字符串长度
OBFUSCATED_NAME_LENGTH = 8

# 混淆加密文件后缀
ENCRYPTED_FILE_SUFFIX = ".enc"

# 备份时需要打包的敏感文件列表
SENSITIVE_FILES = [
    VERSION_FILE_NAME,
    GAME_LIST_FILE_NAME,
    SAFE_CONFIG_FILE_NAME,
]

# ==================== 安全验证 ====================

# TOTP 二维码的账户名与发行方
TOTP_ISSUER = "MRNewGameLauncher"

# TOTP 验证最大尝试次数
TOTP_MAX_ATTEMPTS = 3

# 验证时间/崩溃日志使用的时间格式
DATETIME_FORMAT = "%Y/%m/%d-%H:%M:%S"

# ---- 备份加密 v2（TOTP 种子派生包裹密钥）----
BACKUP_KEY_HEADER_NAME = "keyfile.json"
BACKUP_FORMAT_MAGIC = "MRBK"
BACKUP_FORMAT_VERSION = 2
BACKUP_KEK_KDF = "HKDF-SHA256"
BACKUP_KEK_SALT_LENGTH = 16
BACKUP_KEK_INFO = b"MRNewGameLauncher-backup-v2-kek"
BACKUP_DEK_LENGTH = 32
BACKUP_SEED_MAX_ATTEMPTS = 3
MIGRATED_FILE_SUFFIX = "_v2"

# ==================== 更新日志 ====================

# 更新日志数据结构
CHANGELOG = [
    ("40.0", "2026.01.17-17:00", [
        ("增加", [
            "备份加密 v2：每备份独立随机 256 位 DEK 加密，由本地 TOTP 种子经 HKDF-SHA256 派生 KEK 包裹，彻底解决 v1 时间戳派生密钥的安全漏洞",
            "本地备份功能：生成 v2 加密包直接保存到数据目录，无需 WebDAV，可离线使用",
            "管理备份格式识别：选中备份后自动检测并标注 [v1]/[v2]，v1 包恢复成功后询问是否原地升级为 v2",
            "管理备份加载本地备份：统一列出云端与本地备份，未配置 WebDAV 时仅显示本地",
            "首次运行强制回输 TOTP 密钥确认已保存，防止换机后无法恢复备份"
        ]),
        ("改进", [
            "模块化重构：将单文件 MRNewGameLauncher39.0.py 拆分为 mr_launcher 包（11 个模块 + 入口脚本）",
            "常量集中化：迭代次数、文件名、编码等散落在多处的硬编码统一收归 config.py",
            "备份菜单重排：1.配置WebDAV 2.管理备份 3.备份到云端 4.备份到本地",
            "版本文件编码改为 UTF-8 并集中为 VERSION_FILE_ENCODING，避免跨系统编辑器乱码"
        ]),
        ("修复", [
            "修复备份加密强度：v1 使用文件名时间戳+公开盐派生密钥，等同于不加密，现已升级为随机密钥+种子包裹",
            "修复版本文件乱码：Windows-1258 等编码下全角冒号显示为 £º，改用 UTF-8 确保所有编辑器正确识别"
        ]),
        ("其他", [
            "移除单独的升级加密格式选项，改为 v1 恢复成功后自动询问原地升级，简化交互流程"
        ])
    ]),
    ("1.0", "2024.01.01-11:11", [
        ("其他", ["初始版本，使用python重写了原游戏启动器"])
    ]),
]
