# MR 新游戏启动器 v39.0（模块化重构版）

原单文件 `MRNewGameLauncher39.0.py`（2810 行）已重构为 `mr_launcher` 包，所有功能与逻辑保持不变。

## 目录结构

```
MRNewGameLauncher39_0_main.py   # 程序入口（等价于原脚本直接运行）
mr_launcher/
├── __init__.py        # 包说明
├── config.py          # 全局常量（版本/文件名/编码/加密与备份参数/验证参数）与更新日志
├── ui.py              # Color、SystemLog、视觉宽度排版、头部与游戏列表渲染、更新日志打印
├── logging_sys.py     # log_exit 异常退出日志 + setup_exit_handler(excepthook)
├── storage.py         # 盘符枚举/选择、数据目录定位、游戏列表读写(GB18030)、隐藏属性
├── security.py        # TOTP 密钥生成/二维码、safe_config 读写、TOTP 验证、Windows Hello、隐藏游戏切换
├── games.py           # 游戏增删改、交互式排序、打开目录、管理菜单、归档显示、启动游戏
├── about.py           # 关于页面与完整更新日志
├── crypto.py          # PBKDF2-HMAC 密钥派生 + AES-GCM 加解密
├── webdav.py          # WebDAV 配置、备份(打包/加密/SHA256)、完整性校验、恢复
├── settings_menu.py   # 安全设置子菜单与设置主菜单
└── main.py            # menu() 主循环
```

## 运行（Windows）

```bash
pip install -r requirements.txt
python MRNewGameLauncher39_0_main.py
```

依赖：pyotp、qrcode、pywin32、psutil、webdavclient3、cryptography、WinRT(winsdk)。
`msvcrt`/`ctypes` 为 Windows 标准库，无需安装。

## 兼容性说明

- 每个函数/类均通过 AST 逐字比对，与原文件 52 个顶层定义完全一致；仅按各函数的实际引用拆分 import。
- 模块间依赖为单向分层：config ← crypto/storage/ui ← security/games/webdav ← settings_menu/main，无循环导入。
- 原单文件仍保留在仓库根目录，可继续独立运行（Linux 下因缺少 win32api/msvcrt 无法运行属预期行为）。
