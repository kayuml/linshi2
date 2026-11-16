"""MR 新游戏启动器 v39.0 —— 模块化包结构。

由单文件 MRNewGameLauncher39.0.py 重构而来，所有功能与逻辑保持不变：
- config         全局常量与更新日志
- ui             配色、流式日志 UI、视觉宽度排版、头部/列表渲染
- logging_sys    异常退出日志与 excepthook
- storage        盘符选择、数据目录定位、游戏列表读写、隐藏属性
- security       TOTP 密钥/二维码、安全配置、Windows Hello、隐藏游戏切换
- games          游戏增删改、排序、打开目录、管理菜单、启动游戏
- about          关于页面与完整更新日志
- crypto         PBKDF2 密钥派生 + AES-GCM 加解密
- webdav         WebDAV 配置、备份、完整性校验与恢复
- settings_menu  设置子菜单（安全设置 / WebDAV / 备份管理）
- main           主菜单循环
"""

VERSION = "39.0"
