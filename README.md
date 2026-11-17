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
├── crypto.py          # v1 PBKDF2(仅旧包恢复) + v2 HKDF种子包裹随机密钥 + AES-GCM 加解密
├── webdav.py          # WebDAV 配置、备份(v2加密/打包/SHA256)、完整性校验、恢复、旧包一键迁移
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

## 备份加密 v2（TOTP 种子包裹随机密钥）

- 每备份独立随机 256 位 DEK 加密包内文件；DEK 由本地 TOTP 种子经 HKDF-SHA256（随机盐）派生的 KEK 以 AES-GCM 包裹，存于包内明文头部 `keyfile.json`（头部作 AAD 防篡改）。文件名时间戳不再承担安全职责。
- **首次运行强制回输 TOTP 密钥确认已保存**：该密钥同时是备份解密密钥，未保存则换机后无法恢复备份。
- 同机备份/恢复零新增交互；异机恢复需输入当初保存的 TOTP 密钥字符串（最多3次），随后沿用现有 TOTP 验证码授权。
- 旧 v1 备份仍可恢复（会警告强度极弱）；可在“管理备份 → 5. 升级加密格式”由用户主动一键迁移为 v2（生成 `_v2.zip`，上传前自校验，是否删旧包由用户决定）。
- 备份设置菜单：1. 配置WebDAV服务器 2. 管理备份 3. 备份到云端 4. 备份到本地。
- 备份到本地：生成与云端备份完全一致的 v2 加密包，直接存入数据目录（无需 WebDAV，可离线）；压缩包不隐藏，便于自行复制保管。
- 管理备份：选中备份后自动下载识别格式并标注 [v2]/[旧格式·等效明文]；v2 包的"升级加密格式"选项置灰保留；识别下载的数据复用于恢复/迁移，避免二次下载。
- 管理备份：统一列出云端与本地备份（[云端]/[本地]），未配置 WebDAV 时仅显示本地；本地备份可直接恢复/删除。
- 移除单独的升级选项：v1 包恢复成功后询问是否原地升级为 v2（现有包被自动覆盖替换，不产生 _v2 新文件）。
