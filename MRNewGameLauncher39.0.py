import os  
import pyotp  
import qrcode  
import datetime  
import ctypes  
import shutil  
import unicodedata # 用于处理Unicode字符，特别是判断字符的显示宽度  
import win32api  
import win32file  
import subprocess  # 用于创建和管理子进程，解决Godot输出挂起问题  
import psutil # 用于获取内存使用情况
import time  # 用于添加延迟，避免组合启动时的进程冲突  
import re  # 用于正则表达式匹配  
import threading  # 引入多线程模块  
import io  # 用于在内存中处理二进制数据流，避免在磁盘上创建临时文件  
import zipfile  # 用于创建、读取和写入ZIP压缩文件  
from webdav3.client import Client  # 用于与WebDAV服务器进行交互（上传、下载、管理等操作）  
import random  # 用于生成随机字符串  
import string  # 用于提供字母和数字的字符集  
import hashlib  # 用于计算文件的SHA256哈ASH值  
from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # 用于AES-GCM加密  
from cryptography.hazmat.primitives import hashes  # 导入密码学库的哈希函数，用于密钥派生过程中的哈希算法  
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC  # 导入PBKDF2密钥派生函数，用于从时间戳安全地生成加密密钥  
import traceback  # 用于获取详细的异常堆栈信息  
import sys  # 用于获取系统信息和设置异常处理钩子  
import asyncio # 用于处理异步的Windows Hello API调用  
from winrt.windows.security.credentials.ui import UserConsentVerifier, UserConsentVerifierAvailability, UserConsentVerificationResult # 用于调用 Windows Hello 系统验证
import msvcrt  # 用于监听键盘按键，实现直观的排序交互
  
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
    ])
]

# 赛博朋克配色方案  
class Color:  
    CYAN = "\033[38;5;51m"  
    PINK = "\033[38;5;198m"  
    GOLD = "\033[38;5;220m"  
    GRAY = "\033[38;5;244m"  
    GREEN = "\033[38;5;82m"  
    RED = "\033[38;5;196m"  
    BLUE = "\033[38;5;27m"  
    ARCHIVED_HIGHLIGHT = "\033[38;5;117m" # 为已归档游戏提供的亮紫色高亮  
    RESET = "\033[0m"  
    BOLD = "\033[1m"  
    CLEAR_LINE = "\033[K" # 核心：清除当前行残余，确保原地覆盖不留痕迹  
  
class SystemLog:  
    """流式步骤追踪 UI，提供更清晰、不干扰的进度反馈"""  
    @staticmethod  
    def step(message, status="run"):  
        """  
        输出一个任务步骤的日志。  
        参数:  
            message (str): 要显示的任务消息。  
            status (str): 任务状态 ("run", "done", "fail")。  
        """  
        icons = {  
            "run": f"{Color.CYAN}➤{Color.RESET}",  
            "done": f"{Color.GREEN}✓{Color.RESET}",  
            "fail": f"{Color.RED}✗{Color.RESET}"  
        }  
        icon = icons.get(status, " ")  
          
        if status == "run":  
            # 使用 \r 回到行首但不换行，等待后续的 done/fail 状态覆盖  
            print(f"  {icon} {message}...", end="\r", flush=True)  
        else:  
            # 使用 CLEAR_LINE 清除该行之前可能存在的 "..." 残影  
            print(f"{Color.CLEAR_LINE}  {icon} {message}")  
  
    @staticmethod  
    def info(message):  
        """输出一条信息性日志。"""  
        print(f"  {Color.GOLD}i{Color.RESET} {message}")  
  
    @staticmethod  
    def warn(message):  
        """输出一条警告或错误日志。"""  
        print(f"\n  {Color.RED}{Color.BOLD}[!]{Color.RESET} {message}")  
    
    @staticmethod
    def success(message):
        """输出一条最终成功消息，通常用于整个操作结束。"""
        print(f"\n  {Color.GREEN}{Color.BOLD}[+]{Color.RESET} {message}")

def get_v_width(s):  
    """精确计算中英文混合字符串在终端中的视觉宽度，忽略 ANSI 转义码。"""  
    width = 0  
    clean_s = re.sub(r'\033\[.*?m', '', s) # 移除 ANSI 转义码  
    for char in clean_s:  
        if unicodedata.east_asian_width(char) in ('W', 'F'):  
            width += 2  
        else:  
            width += 1  
    return width  
  
def pad_v(s, target_width):  
    """根据视觉宽度在右侧填充空格，确保中英文混合字符串左对齐。"""  
    current_width = get_v_width(s)  
    return s + " " * max(0, target_width - current_width)  
  
def align_right_v(s, target_width):  
    """根据视觉宽度在左侧填充空格，确保中英文混合字符串右对齐。"""  
    current_width = get_v_width(s)  
    return " " * max(0, target_width - current_width) + s  

# --- 用于中央对齐的辅助函数 ---
def align_center_v(s, target_width):
    """根据视觉宽度在左右填充空格，确保中英文混合字符串中央对齐。"""
    current_width = get_v_width(s)
    if current_width >= target_width:
        return s # 如果字符串本身就比目标宽度长，则不进行填充
    padding_needed = target_width - current_width
    left_padding = padding_needed // 2
    right_padding = padding_needed - left_padding
    return " " * left_padding + s + " " * right_padding

def log_exit(exit_type, value, traceback_obj, folder_path=None):    
    """    
    记录程序异常退出信息    
        
    参数:    
        exit_type: 异常类型    
        value: 异常值    
        traceback_obj: 异常的堆栈跟踪对象    
        folder_path: 数据文件夹路径    
    """    
    if folder_path is None:    
        try:    
            folder_path = get_or_create_data_folder()    
        except:    
            # 如果连数据文件夹都无法获取，则使用当前目录    
            folder_path = os.getcwd()    
    
    log_path = os.path.join(folder_path, "MRNewGameLauncherCrashLog.txt")    
    timestamp = datetime.datetime.now().strftime('%Y/%m/%d-%H:%M:%S')    
        
    try:    
        # 确保使用 utf-8 编码写入日志文件，避免特殊字符导致的编码错误    
        with open(log_path, "a", encoding="utf-8") as log_file:    
            log_file.write(f"\n[{timestamp}] 程序异常退出\n")    
            log_file.write(f"异常类型: {exit_type.__name__}\n")    
            log_file.write(f"异常信息: {value}\n")    
            # 获取详细的堆栈跟踪信息    
            if traceback_obj:    
                tb_lines = traceback.format_tb(traceback_obj)    
                log_file.write("堆栈跟踪:\n")    
                for line in tb_lines:    
                    log_file.write(line)    
                
            # 记录系统信息    
            log_file.write("\n系统信息:\n")    
            log_file.write(f"操作系统: {os.name}, {sys.platform}\n")    
            log_file.write(f"Python版本: {sys.version}\n")    
                
            # 记录内存使用情况
            try:
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                log_file.write(f"内存使用: {memory_info.rss / 1024 / 1024:.2f} MB\n")
            except Exception: # 捕获 psutil 相关的任何异常
                log_file.write("获取内存信息时出错\n")
    except Exception as e:    
        # 如果写入日志文件失败，尝试写入备用日志    
        try:    
            # 使用 utf-8 编码写入紧急日志    
            with open("crash_emergency.log", "a", encoding="utf-8") as emergency_log:    
                emergency_log.write(f"[{timestamp}] 写入崩溃日志失败: {str(e)}\n")    
                emergency_log.write(f"原始异常: {exit_type.__name__}: {value}\n")    
        except Exception:    
            # 如果连备用日志都无法写入，那么就无能为力了    
            pass
    
def setup_exit_handler():
    # 保存原始的异常处理器    
    original_excepthook = sys.excepthook    
    # 定义新的异常处理器    
    def exception_handler(exc_type, exc_value, exc_traceback):    
        # 记录异常信息    
        log_exit(exc_type, exc_value, exc_traceback)    
        # 调用原始异常处理器    
        original_excepthook(exc_type, exc_value, exc_traceback)    
        
    # 设置新的异常处理器    
    sys.excepthook = exception_handler    
    
def create_or_update_version_file(folder_path):
    """    
    创建/更新版本文件    
    """    
    version_file = os.path.join(folder_path, "MRNewGameLauncherConfigVersion.txt")    
    try:    
        # 尝试取消隐藏属性（如果存在）    
        if os.path.exists(version_file):    
            unhide_file(version_file)    
                
        # 强制写入最新版本    
        with open(version_file, "w") as f:    
            f.write(f"Ver：{VERSION}")    
                
        # 写入完成后重新隐藏文件    
        hide_file(version_file)    
    except PermissionError:    
        print(f"权限不足，无法更新版本文件: {version_file}")    
        print("请尝试以管理员身份运行程序，或检查文件夹写入权限")    
        exit(1)    
    except Exception as e:    
        print(f"创建版本文件失败: {e}")    
        exit(1)    
            
def get_available_drives():
    """    
    获取当前系统中所有可用的本地磁盘盘符。    
    """    
    drives = []    
    for drive in win32api.GetLogicalDriveStrings().split('\000')[:-1]:    
        drive_type = win32file.GetDriveType(drive)    
        if drive_type == win32file.DRIVE_FIXED:  # 只保留本地磁盘    
            drives.append(drive)    
    return drives    
    
def get_drive_label(drive):
    """    
    获取指定盘符的卷标。    
    """    
    try:    
        vol_name = win32api.GetVolumeInformation(drive)[0]    
        return vol_name    
    except Exception as e:    
        print(f"获取卷标时出错: {e}")    
        return "未知卷标"    
    
def select_drive():
    """    
    让用户选择一个盘符。    
    """    
    drives = get_available_drives()    
    if not drives:    
        print("没有可用的本地磁盘。")    
        return None    
        
    while True:    
        print("请选择一个盘符来保存配置文件:")    
        for i, drive in enumerate(drives, start=1):    
            label = get_drive_label(drive)    
            print(f"{i}. {drive} ({label})")    
        choice = input("请输入序号: ")    
        if choice.isdigit() and 1 <= int(choice) <= len(drives):    
            return drives[int(choice) - 1]    
        else:    
            print("无效的选择，请重新输入。")    
    
def create_data_folder(drive):
    """    
    在指定盘符的根目录下创建名为 MRNewGameLauncherData 的文件夹。    
    """    
    folder_path = os.path.join(drive, "MRNewGameLauncherData")    
    if not os.path.exists(folder_path):    
        os.makedirs(folder_path)    
    return folder_path    
    
def get_or_create_data_folder():
    """    
    获取或创建 MRNewGameLauncherData 文件夹。    
    如果文件夹已经存在，直接返回路径；否则让用户选择盘符并创建文件夹。    
    如果发现多个文件夹，提示用户选择一个文件夹，并警告用户将删除选择之外的其他文件夹。    
    """    
    drives = get_available_drives()    
    existing_folders = []    
    for drive in drives:    
        folder_path = os.path.join(drive, "MRNewGameLauncherData")    
        if os.path.exists(folder_path):    
            existing_folders.append(folder_path)    
        
    if len(existing_folders) == 1:    
        return existing_folders[0]    
    elif len(existing_folders) > 1:    
        print("发现多个 MRNewGameLauncherData 文件夹，请选择一个:")    
        print("警告：选择之外的其他文件夹将被删除。")    
        for i, folder in enumerate(existing_folders, start=1):    
            print(f"{i}. {folder}")    
        while True:    
            choice = input("请输入序号: ")    
            if choice.isdigit() and 1 <= int(choice) <= len(existing_folders):    
                selected_folder = existing_folders[int(choice) - 1]    
                # 删除其他文件夹    
                for folder in existing_folders:    
                    if folder != selected_folder:    
                        try:    
                            shutil.rmtree(folder)    
                            print(f"已删除文件夹: {folder}")    
                        except OSError as e:    
                            print(f"删除文件夹 {folder} 时出错: {e}")    
                return selected_folder    
            else:    
                print("无效的选择，请重新输入。")    
    else:    
        # 如果文件夹不存在，让用户选择盘符并创建文件夹    
        drive = select_drive()    
        return create_data_folder(drive)    
    
def generate_totp_key():
    # 生成一个随机的TOTP密钥，使用base32编码    
    return pyotp.random_base32()    
    
def display_qr_code(key):
    # 使用TOTP密钥生成URI，用于QR码    
    totp_uri = pyotp.totp.TOTP(key).provisioning_uri(name='MRNewGameLauncher', issuer_name='MRNewGameLauncher')    
        
    # 生成并在终端显示QR码    
    qr = qrcode.QRCode()  # 引入QRCode类用于生成二维码    
    qr.add_data(totp_uri)  # 将TOTP URI数据添加到二维码中    
    qr.print_ascii(invert=True)  # 以ASCII字符的方式打印二维码，使用反色（背景黑，前景白）    
        
    return key  # 返回生成的TOTP密钥    
    
def save_safe_config(key, frequency, last_verified, win_hello_enabled, folder_path=None):
    """    
    保存安全配置到文件中。    
    如果文件存在，确保文件写入时是可见的。    
    写入TOTP密钥、验证频率、上次验证时间和Windows Hello选项状态。    
    写入完成后隐藏文件以保护数据。    
    """    
    if folder_path is None:    
        folder_path = get_or_create_data_folder()    
        
    file_path = os.path.join(folder_path, "MRNewGameLauncherSafeConfig.txt")    
        
    # 检查是否存在存储安全配置的文件    
    if os.path.exists(file_path):    
        unhide_file(file_path)  # 确保文件是可见的    
        
    # 以写入模式打开文件    
    with open(file_path, "w", encoding="GB18030") as file: # 明确指定GB18030编码    
        # 将TOTP密钥写入文件    
        file.write(f"TOTP密钥：{key}\n")    
        # 检查频率参数是否被提供    
        if frequency is not None:    
            # 如果提供频率，写入文件    
            file.write(f"验证频率（单位：小时）：{frequency}\n")    
        else:    
            # 如果未提供频率，记录为“每次验证”    
            file.write("验证频率（单位：小时）：每次验证\n")    
            
        # 根据频率的值写入上次验证时间    
        if frequency == "每次验证":    
            # 如果频率为“每次验证”，则不记录具体时间    
            file.write("上次验证的时间：\n")    
        elif frequency == "无需验证":    
            # 如果频率为“无需验证”，则不记录具体时间    
            file.write("上次验证的时间：\n")    
        elif last_verified is not None:    
            # 如果提供了上次验证的时间，则写入文件    
            file.write(f"上次验证的时间：{last_verified}\n")    
        else:    
            # 如果未提供时间，保持文件句柄，仍然写入说明信息    
            file.write("上次验证的时间：\n")    
            
        # 保存 Windows Hello 选项状态    
        status_str = "启用" if win_hello_enabled else "禁用"    
        file.write(f"提供 Windows Hello 选项以激活隐藏游戏：{status_str}\n")    
        
    # 写入完成后隐藏文件以保护数据    
    hide_file(file_path)  # 保存后隐藏文件    
    
def load_safe_config(folder_path=None):
    """    
    从文件中加载安全配置。    
    如果文件不存在，返回默认值。    
    如果文件存在，读取内容并返回TOTP数据和Windows Hello选项状态。    
    """    
    if folder_path is None:    
        folder_path = get_or_create_data_folder()    
        
    file_path = os.path.join(folder_path, "MRNewGameLauncherSafeConfig.txt")    
        
    # 检查存储安全配置的文件是否存在    
    if not os.path.exists(file_path):    
        return None, None, None, False # 默认禁用    
    
    # 以读取模式打开文件，明确指定GB18030编码    
    with open(file_path, "r", encoding="GB18030") as file:    
        # 读取文件的所有行    
        lines = file.readlines()    
        # 如果文件中的行数少于3，则返回默认值    
        if len(lines) < 3:    
            return None, None, None, False    
            
        # 提取TOTP密钥，去除多余的空格和标识字符串    
        key = lines[0].strip().replace("TOTP密钥：", "").strip()    
        # 读取频率行    
        frequency_line = lines[1].strip()    
        # 提取上次验证的时间，去除标识字符串    
        last_verified = lines[2].strip().replace("上次验证的时间：", "").strip()    
    
        # 检查是否为“每次验证”频率    
        if "验证频率（单位：小时）：每次验证" in frequency_line:    
            frequency = "每次验证"    
        # 检查是否为“无需验证”频率    
        elif "验证频率（单位：小时）：无需验证" in frequency_line:    
            frequency = "无需验证"    
        else:    
            # 从频率行中提取频率值    
            frequency = frequency_line.replace("验证频率（单位：小时）：", "").strip()    
    
        # 加载 Windows Hello 选项状态    
        win_hello_enabled = False    
        if len(lines) >= 4:    
            config_line = lines[3]    
            if "提供 Windows Hello 选项以激活隐藏游戏：" in config_line:    
                if "启用" in config_line:    
                    win_hello_enabled = True    
    
        # 返回加载的TOTP密钥、验证频率、上次验证时间和Windows Hello选项状态    
        return key, frequency, last_verified, win_hello_enabled    
    
def verify_totp(key, frequency, last_verified):    
    """    
    验证TOTP码。    
    如果频率设置为“无需验证”，则直接返回验证成功。    
    否则，根据频率和上次验证时间判断是否需要验证。    
    如果需要验证，则提示用户输入TOTP码，并进行验证。    
    """    
    # 检查是否提供了TOTP密钥    
    if not key:    
        SystemLog.warn("未找到TOTP密钥，请联系管理员。")  # 提示用户密钥未找到    
        input("按任意键退出脚本...")  # 等待用户操作    
        return False  # 返回验证失败，不进行后续验证    
          
    if frequency == "无需验证":    
        return True  # 如果频率设置为“无需验证”，则直接返回验证成功    
          
    # 创建一个TOTP对象，使用提供的密钥    
    totp = pyotp.TOTP(key)    
    # 获取当前时间    
    now = datetime.datetime.now()    
          
    # 检查验证频率是否不是“每次验证”且上次验证时间存在    
    if frequency != "每次验证" and last_verified:    
        try:    
            # 将上次验证的时间字符串转换为datetime对象    
            last_verified_dt = datetime.datetime.strptime(last_verified, "%Y/%m/%d-%H:%M:%S")    
            # 计算上次验证以来经过的小时数    
            elapsed_hours = (now - last_verified_dt).total_seconds() / 3600    
            # 如果经过的小时数小于设定频率，认为验证通过    
            if elapsed_hours < float(frequency):    
                return True  # 返回验证成功    
        except (ValueError, TypeError):    
             pass # 如果格式或类型错误，则忽略并继续要求验证    
    
    # 初始化尝试次数    
    attempts = 3    
    # 循环，直到尝试次数用完    
    while attempts > 0:    
        code = input(f"\n  {Color.GOLD}请输入TOTP码: {Color.RESET}").strip()    
        if not code: # 用户直接回车，视为取消  
            SystemLog.warn("TOTP 验证已取消。")  
            return False  
          
        SystemLog.step("正在验证身份凭证", "run")  
        # 验证用户输入的TOTP码    
        if totp.verify(code):    
            SystemLog.step("身份凭证验证", "done")  
            # 如果输入正确，保存当前成功验证的信息    
            # 需要先加载一次配置以获取当前的 win_hello_enabled 状态    
            _, _, _, win_hello_enabled = load_safe_config()    
            save_safe_config(key, frequency, now.strftime("%Y/%m/%d-%H:%M:%S"), win_hello_enabled)    
            return True  # 返回验证成功    
        else:    
            SystemLog.step("身份凭证验证", "fail")  
            # 如果输入错误，减少尝试次数    
            attempts -= 1    
            # 提示用户还有多少次尝试机会    
            SystemLog.warn(f"验证码错误，您还有 {attempts} 次机会。")  
    return False  # 达到最大尝试次数后，返回验证失败    
    
def load_game_list(folder_path=None):
    """    
    加载游戏列表从 'MRNewGameLauncherGameList.txt' 文件。    
    如果文件存在，读取内容并返回一个游戏列表。    
    检查路径是否包含引号，如果包含则去除引号。    
    如果游戏项只有3个字段（旧格式），则添加隐藏状态字段为默认的 "visible"。    
    如果隐藏状态字段的值不是 "visible" 或 "hidden"，则将其改为默认的 "visible"。    
    自动将旧格式（3或4字段）升级为新的5字段格式，增加归档状态。  
    如果需要更新配置文件，则调用 save_game_list 函数保存规范化后的游戏列表。    
    否则返回一个空列表。    
    """    
    if folder_path is None:    
        folder_path = get_or_create_data_folder()    
        
    file_path = os.path.join(folder_path, "MRNewGameLauncherGameList.txt")    
        
    if os.path.exists(file_path):  # 检查游戏列表文件是否存在    
        # 使用 GB18030 编码读取文件，以支持特殊字符并与备份功能保持一致  
        with open(file_path, "r", encoding="GB18030") as file:  
            # 逐行读取文件，并根据'|'分隔符拆分每行内容    
            game_list = [line.strip().split('|') for line in file]    
            
        modified = False  # 用于标记是否需要更新配置文件    
        for game in game_list:    
            if len(game) > 0 and game[0].startswith('"') and game[0].endswith('"'):    
                game[0] = game[0].strip('"')  # 去除路径中的引号    
                modified = True  # 标记为需要更新配置文件    
                
            # 如果游戏项只有3个字段（旧格式），则添加可见性状态和归档状态  
            if len(game) == 3:    
                game.append("visible")  # 添加默认可见状态  
                game.append("active")   # 添加默认激活（未归档）状态  
                modified = True  # 标记为需要更新配置文件  
            # 如果游戏项只有4个字段（旧格式），则添加归档状态  
            elif len(game) == 4:  
                game.append("active")   # 添加默认激活（未归档）状态  
                modified = True  
              
            # 如果第4字段不为 "visible" 或 "hidden"，则将其改为默认的 "visible"    
            if len(game) > 3 and game[3] not in ["visible", "hidden"]:    
                game[3] = "visible"  # 规范化可见性状态字段    
                modified = True  # 标记为需要更新配置文件  
              
            # 如果第5字段不为 "active" 或 "archived"，则将其改为默认的 "active"  
            if len(game) > 4 and game[4] not in ["active", "archived"]:  
                game[4] = "active" # 规范化归档状态字段  
                modified = True  
            
        # 如果路径被修改，调用 save_game_list 函数保存规范化后的游戏列表    
        if modified:    
            save_game_list(game_list, folder_path)    
            
        return game_list  # 返回加载的游戏列表    
    return []  # 如果文件不存在，返回空列表  
        
def save_game_list(game_list, folder_path=None):
    """    
    保存游戏列表到 'MRNewGameLauncherGameList.txt' 文件。    
    如果 MRNewGameLauncherGameList.txt 文件存在，每次写入文件前都会取消隐藏属性，写入完成后再重新设置隐藏属性，从而避免权限问题    
    """    
    if folder_path is None:    
        folder_path = get_or_create_data_folder()    
        
    file_path = os.path.join(folder_path, "MRNewGameLauncherGameList.txt")    
        
    if os.path.exists(file_path):    
        unhide_file(file_path)  # 确保文件是可见的    
    # 使用 GB18030 编码写入文件，以支持特殊字符并与备份功能保持一致  
    with open(file_path, "w", encoding="GB18030") as file:  
        # 将每个游戏的信息以'|'连接并写入文件    
        for game in game_list:    
            file.write('|'.join(game) + "\n")    
    hide_file(file_path)  # 保存后隐藏文件    
    
def hide_file(filepath):
    """    
    将指定文件设置为隐藏属性（Windows系统）。    
    """    
    if os.name == 'nt':  # 检查是否为Windows操作系统    
        FILE_ATTRIBUTE_HIDDEN = 0x02  # 隐藏属性    
        ctypes.windll.kernel32.SetFileAttributesW(filepath, FILE_ATTRIBUTE_HIDDEN)    
    
def unhide_file(filepath):
    if os.name == 'nt':  # 检查是否为Windows操作系统    
        FILE_ATTRIBUTE_NORMAL = 0x80  # 正常属性    
        ctypes.windll.kernel32.SetFileAttributesW(filepath, FILE_ATTRIBUTE_NORMAL)    
    
def draw_header(game_list):  
    os.system('cls' if os.name == 'nt' else 'clear')  
    
    # 获取终端宽度  
    try:  
        terminal_width = shutil.get_terminal_size().columns  
    except OSError:  
        terminal_width = 80 # 默认宽度  
  
    # 计算游戏数量  
    active_count = len([g for g in game_list if g[4] == 'active'])  
    total_count = len(game_list)  
  
    # 构造上段文本: "MR 新游戏启动器"  
    title_text = f"{Color.BOLD}{Color.CYAN}MR 新游戏启动器{Color.RESET}"  
    
    # 构造下段文本: "激活游戏: 11 | 总计: 28"  
    stats_text = f"{Color.CYAN}激活游戏: {active_count} | 总计: {total_count}{Color.RESET}"  
  
    # 计算最宽的文本的视觉宽度，以决定边框的长度  
    # 为了让边框看起来更对称，可以固定一个内容区域宽度，或者取两者最大值  
    max_content_width = max(get_v_width(title_text), get_v_width(stats_text))  
    
    # 确定实际的绘制宽度，例如在终端宽度减去一些边距  
    # 假设两侧各留 2 个空格的视觉边距，那么实际绘制内容区域的宽度就是 terminal_width - 4  
    # 但为了让边框看起来更宽阔，可以取 max_content_width 加上一定的内边距，然后与 terminal_width 比较  
    # 例如，让内容区域至少比最长文本多 4 个空格 (左右各2)  
    effective_width = max(max_content_width + 4, terminal_width - 4) 
    # 确保 effective_width 不会超过终端宽度  
    effective_width = min(effective_width, terminal_width) 
    
    # 确保 effective_width 至少为 10，防止终端过窄时出错  
    effective_width = max(effective_width, 10)
  
    # 绘制上边框 (左右不封闭)  
    print(f"{Color.CYAN}─{Color.RESET}" * effective_width)  
  
    # 绘制标题行 (中央对齐)  
    centered_title = align_center_v(title_text, effective_width)  
    print(centered_title)  
  
    # 绘制统计信息行 (中央对齐)  
    centered_stats = align_center_v(stats_text, effective_width)  
    print(centered_stats)  
  
    # 绘制下边框 (左右不封闭)  
    print(f"{Color.CYAN}─{Color.RESET}" * effective_width)

def display_game_list(game_list, show_hidden=False, mode='active'):  
    """      
    显示游戏列表，并高亮显示“未安装”状态和“已通关”状态的游戏。      
    如果 show_hidden 为 False，未激活的隐藏的游戏将显示为“隐藏游戏”。      
    如果 show_hidden 为 True，激活的隐藏的游戏将以粉色高亮显示。      
    已归档游戏（archived）会使用亮紫色（ARCHIVED_HIGHLIGHT）高亮名称和版本并且会在版本信息后显示金色标签。
      
    参数:      
        game_list (list): 游戏列表，每个游戏为一个列表。      
        show_hidden (bool): 是否显示隐藏的游戏。默认为 False。    
        mode (str): 显示模式 ('all', 'active', 'archived')。    
    """    
    # 根据模式过滤列表    
    if mode == 'active':    
        display_items = [game for game in game_list if game[4] == 'active']    
    elif mode == 'archived':    
        display_items = [game for game in game_list if game[4] == 'archived']    
    else: # mode == 'all'    
        display_items = game_list    
  
    if not display_items:  
        print(f"   {Color.GRAY}(当前列表为空){Color.RESET}")  
        return  
  
    # 动态计算最大宽度，确保对齐细节不破坏  
    max_name_content_width = 0  
    max_version_info_width = 0 # 用于版本信息部分的动态宽度  
  
    # 获取最大序号的位数，用于序号列的右对齐  
    max_index_width = max(len(str(len(display_items))), 2) 
  
    for g in display_items:  
        is_hidden_and_not_shown = (g[3] == "hidden" and not show_hidden)  
        name_t = "隐藏游戏" if is_hidden_and_not_shown else g[1]  
        max_name_content_width = max(max_name_content_width, get_v_width(name_t))  
          
        # 计算版本信息部分的宽度：(版本号) 或 (未安装) 或 (已通关)  
        if not is_hidden_and_not_shown and g[2]:  
            max_version_info_width = max(max_version_info_width, get_v_width(f"({g[2]})"))  
  
    # 设定列的最小视觉宽度，并加上动态计算的最大内容宽度  
    NAME_COLUMN_MIN_WIDTH = 25  
    VERSION_COLUMN_MIN_WIDTH = 10  
      
    name_column_actual_width = max(max_name_content_width, NAME_COLUMN_MIN_WIDTH)  
    version_column_actual_width = max(max_version_info_width, VERSION_COLUMN_MIN_WIDTH)  
  
    for i, game in enumerate(display_items, start=1):      
        path, name, ver, vis, arc = game  
        is_hidden_and_not_shown = (vis == "hidden" and not show_hidden)  
          
        # 1. 颜色与前缀 (保留原有细节)  
        # 序号部分进行右对齐填充  
        if mode != 'archived':  
            index_str = align_right_v(str(i), max_index_width) + "."  
            prefix = f"{Color.GOLD}{index_str}{Color.RESET}"  
        else:  
            prefix = f"{Color.ARCHIVED_HIGHLIGHT}•{Color.RESET}"  
          
        # 确定名称和版本的基础颜色  
        n_color = Color.CYAN  
        v_color = Color.GRAY # 版本信息默认颜色  
          
        if is_hidden_and_not_shown:   
            n_color = Color.GRAY  
            v_color = Color.GRAY  
        elif ver == "未安装":   
            n_color = Color.RED  
            v_color = Color.RED  
        elif ver == "已通关":   
            n_color = Color.BLUE  
            v_color = Color.BLUE  
        elif vis == "hidden": # 激活的隐藏游戏  
            n_color = Color.PINK  
            v_color = Color.PINK  
        elif arc == "archived": # 为已归档游戏应用亮紫色高亮  
            n_color = Color.ARCHIVED_HIGHLIGHT  
            v_color = Color.ARCHIVED_HIGHLIGHT  
          
        # 2. 构建游戏名称部分  
        display_name_text = "隐藏游戏" if is_hidden_and_not_shown else name  
        padded_name = pad_v(n_color + display_name_text + Color.RESET, name_column_actual_width)  
  
        # 3. 构建版本信息部分 (精确右对齐)  
        version_info_part = ""  
        if not is_hidden_and_not_shown and ver:  
            version_info_part = align_right_v(f"{v_color}({ver}){Color.RESET}", version_column_actual_width)  
        else: # 如果没有版本号，也填充相同宽度，确保后续 [已归档] 对齐  
            version_info_part = " " * version_column_actual_width  
  
        # 4. 构建 [已归档] 标签部分 (精确左对齐)  
        archived_tag_part = ""  
        if not is_hidden_and_not_shown and arc == "archived":  
            archived_tag_part = f" {Color.GOLD}[已归档]{Color.RESET}"  
  
        # 5. 打印行：将各部分组合并打印  
        # 名称 | 版本信息 (右对齐) | [已归档] (左对齐)  
        print(f"  {prefix} {padded_name} {version_info_part}{archived_tag_part}")
                
def add_new_game(game_list, folder_path=None):
    """    
    允许用户添加一个新游戏到游戏列表。    
    提示用户输入游戏的路径、中文名称和可选的英文名称，然后检测路径是否存在。    
    如果路径不存在，自动将游戏版本信息设置为“未安装”。    
    如果路径存在，继续提示用户输入版本信息。    
    """    
    while True:    
        # 提示用户输入游戏路径    
        new_game_path = input("请输入新游戏的快捷方式的路径: ")    
        if not new_game_path:    
            return  # 如果没有输入路径，直接返回目录    
        new_game_path = new_game_path.strip('"')  # 去除路径中的引号    
        # 允许 .lnk 或 .exe 结尾的路径    
        if not (new_game_path.lower().endswith('.lnk') or new_game_path.lower().endswith('.exe')):    
            print("输入不规范，路径必须以 .lnk 或 .exe 结尾。")    
            input("按任意键返回目录...")    
            return  # 如果路径不以 .lnk 或 .exe 结尾，返回目录    
    
        # 提示用户输入游戏中文名称    
        new_game_chinese_name = input("请输入新游戏的中文名称: ")    
        if not new_game_chinese_name:    
            return  # 如果没有输入名称，直接返回目录    
            
        # 提示用户输入游戏英文名称（可选）    
        new_game_english_name = input("请输入新游戏的英文名称（可选）: ")    
        new_game_name = new_game_chinese_name    
            
        # 处理英文名称为空的情况    
        if not new_game_english_name:    
            while True:    
                print("1. 无英文名称")    
                print("2. 返回目录")    
                choice = input("请选择: ")    
                if not choice:  # 直接回车    
                    return  # 直接返回目录    
                if choice == "1":    
                    # 用户选择没有英文名称，只使用中文名称    
                    new_game_name = new_game_chinese_name    
                    break    
                elif choice == "2":    
                    return  # 如果选择返回目录，则返回    
                else:    
                    print("无效的选择，请重新输入。")    
        else:    
            # 用户提供了英文名称，合并中英文名称    
            new_game_name = f"{new_game_chinese_name}：{new_game_english_name}"    
    
        # 检测路径是否存在    
        if not os.path.exists(new_game_path):    
            print("该快捷方式的路径不存在，已自动将该游戏版本信息设为未安装。")    
            new_game_version = "未安装"  # 自动设置为“未安装”    
        else:    
            # 如果路径存在，提示用户输入版本信息    
            new_game_version = input("请输入新游戏的版本信息: ")    
            if not new_game_version:    
                while True:    
                    print("1. 无版本号")    
                    print("2. 返回目录")    
                    print("3. 未安装")    
                    print("4. 已通关")  # 添加新选项    
                    choice = input("请选择: ")    
                    if not choice:    
                        return  # 如果直接回车，直接返回目录    
                    if choice == "1":    
                        new_game_version = ""  # 用户选择没有版本号    
                        break    
                    elif choice == "2":    
                        return  # 如果选择返回目录，则返回    
                    elif choice == "3":    
                        new_game_version = "未安装"  # 用户选择未安装    
                        break    
                    elif choice == "4":    
                        new_game_version = "已通关"  # 用户选择已通关    
                        break    
                    else:    
                        print("无效的选择，请重新输入。")    
    
        # 如果版本设为“已通关”，则自动归档  
        if new_game_version == "已通关":  
            new_game_archive_status = "archived"  
            print(f"因您将游戏“{new_game_name}”的版本信息设为‘已通关’，该游戏已被自动归档。")  
        else:  
            new_game_archive_status = "active"  
  
        # 将包含5个字段的新游戏信息添加到游戏列表  
        game_list.append([new_game_path, new_game_name, new_game_version, "visible", new_game_archive_status])  
        save_game_list(game_list, folder_path)  # 保存更新后的游戏列表  
        print("新游戏已添加！")  
        input("按任意键继续...")  
        break  # 添加完新的游戏后退出循环  
            
def delete_game(game_list, folder_path=None, show_hidden=False):    
    """    
    删除已添加的游戏。    
    提供一个菜单让用户选择要删除的游戏。    
    """    
    while True:    
        # 检查游戏列表是否为空    
        if not game_list:    
            print("当前没有已添加的游戏。")  # 若没有游戏，给出提示    
            input("按任意键返回目录...")    
            return    
        # 显示当前已添加的游戏列表    
        display_game_list(game_list, show_hidden, mode='all')  # 使用 mode='all' 显示所有游戏    
        # 提示用户输入要删除的游戏序号    
        choice = input("请输入想要删除的已添加游戏的序号: ")    
        if not choice:    
            return  # 如果直接回车，直接返回目录    
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(game_list):    
            print("无效的选择，请重新输入。")    
            input("按任意键继续...")    
        else:    
            game_index = int(choice) - 1    
            game_hidden = game_list[game_index][3] if len(game_list[game_index]) > 3 else "visible"    
            if game_hidden == "hidden" and not show_hidden:    
                print("该游戏为隐藏游戏，无法在未激活时删除。")    
                input("按任意键继续...")    
                return    
            # 根据用户选择删除相应游戏    
            del game_list[game_index]  # 删除指定序号的游戏    
            save_game_list(game_list, folder_path)  # 更新游戏列表文件    
            print("游戏已删除！")    
            input("按任意键继续...")    
            break    
    
def edit_game(game_list, folder_path=None, show_hidden=False):
    """      
    编辑已添加游戏的信息，包括路径、名称和版本信息。      
    用户可以选择希望编辑的游戏并更新相应信息。      
    """      
    while True:      
        # 检查游戏列表是否为空      
        if not game_list:      
            print("当前没有已添加的游戏。")      
            input("按任意键返回目录...")      
            return      
        # 显示完整的游戏列表用于编辑选择    
        display_game_list(game_list, show_hidden, mode='all')    
        # 提示用户输入要编辑的游戏的序号      
        choice = input("请输入想要编辑的游戏的序号: ")      
        if not choice:      
            return  # 如果直接回车，直接返回目录的  
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(game_list):      
            print("无效的选择，请重新输入。")      
            input("按任意键继续...")      
        else:      
            game_index = int(choice) - 1  # 获取选中游戏的索引      
            game_hidden = game_list[game_index][3] if len(game_list[game_index]) > 3 else "visible"      
            if game_hidden == "hidden" and not show_hidden:      
                print("该游戏为隐藏游戏，无法在未激活时编辑信息。")      
                input("按任意键继续...")      
                return      
            while True:      
                # 提示用户选择要编辑的信息类型      
                print("请输入想要编辑的信息的序号:")      
                print("1. 路径")      
                print("2. 名称")      
                print("3. 版本信息")      
                print("4. 管理状态")      
                info_choice = input("请选择: ")      
                if not info_choice:      
                    return  # 如果直接回车，直接返回目录的  
                # 路径编辑      
                if info_choice == "1":      
                    new_path = input(f"请输入{game_list[game_index][1]}的新路径: ")      
                    if new_path:      
                        new_path = new_path.strip('"')  # 去除路径中的引号      
                        # 确保输入的路径是有效的快捷方式 (.lnk) 或可执行文件 (.exe)      
                        if new_path.lower().endswith('.lnk') or new_path.lower().endswith('.exe'):      
                            game_list[game_index][0] = new_path  # 更新路径      
                            save_game_list(game_list, folder_path)  # 保存更新      
                            print("路径已更新！")      
                            input("按任意键继续...")      
                            return      
                        else:      
                            print("输入不规范，路径必须以 .lnk 或 .exe 结尾。")  # 如果输入不正确，给出提示      
                            input("按任意键返回目录...")      
                            return      
                # 名称编辑      
                elif info_choice == "2":      
                    # --- 交互式名称编辑器 ---  
  
                    # 1. 初始化数据  
                    current_name = game_list[game_index][1]      
                    chinese_name, english_name = "", ""      
                    if "：" in current_name:      
                        parts = current_name.rsplit("：", 1)      
                        chinese_name = parts[0]      
                        english_name = parts[1]      
                    else:      
                        chinese_name = current_name      
  
                    # 用于存储待修改的临时名称  
                    temp_chinese_name = chinese_name  
                    temp_english_name = english_name  
  
                    # 2. 进入交互式编辑循环  
                    while True:  
                        # 实时生成预览名称  
                        preview_name = f"{temp_chinese_name}：{temp_english_name}" if temp_english_name else temp_chinese_name  
  
                        # 刷新编辑界面  
                        os.system('cls' if os.name == 'nt' else 'clear')  
                        print("--- 正在编辑游戏名称 ---")  
                        print(f"最终效果预览: \033[1;36m{preview_name}\033[0m") # 高亮显示预览  
                        print("------------------------")  
                          
                        # 动态生成菜单选项  
                        print(f"1. 编辑中文名称   (当前: {temp_chinese_name})")  
                        print(f"2. {'编辑' if temp_english_name else '添加'}英文名称   (当前: {temp_english_name if temp_english_name else '无'})")  
                        if temp_english_name:  
                            print("3. 移除英文名称")  
                        print("\ns. \033[1;32m保存并返回\033[0m")  
                        print("c. \033[1;31m取消并返回\033[0m")  
                          
                        # 获取用户选择  
                        sub_choice = input("\n请选择要执行的操作: ").lower()  
  
                        if sub_choice == '1':  
                            new_cn = input(f"请输入新的中文名称 (直接回车保留 '{temp_chinese_name}'): ")  
                            if new_cn:  
                                temp_chinese_name = new_cn  
                        elif sub_choice == '2':  
                            prompt = f"请输入新的英文名称 (直接回车保留 '{temp_english_name}'): " if temp_english_name else "请输入英文名称: "  
                            new_en = input(prompt)  
                            if new_en:  
                                temp_english_name = new_en  
                        elif sub_choice == '3' and temp_english_name:  
                            confirm = input(f"确定要移除英文名称 '{temp_english_name}' 吗? (y/n): ").lower()  
                            if confirm == 'y':  
                                temp_english_name = ""  
                        elif sub_choice == 's':  
                            # 保存最终结果到游戏列表  
                            game_list[game_index][1] = preview_name  
                            save_game_list(game_list, folder_path)  
                            print("\n\033[1;32m名称已成功更新！\033[0m")  
                            input("按任意键继续...")  
                            return # 退出函数  
                        elif sub_choice == 'c':  
                            print("\n\033[1;31m操作已取消，未做任何更改。\033[0m")  
                            input("按任意键继续...")  
                            return # 退出函数  
                        else:  
                            print("\n无效输入，请重新选择。")  
                            input("按任意键继续...")  
                        # 任何有效操作（除了保存/退出）后，循环会继续，并刷新屏幕显示新状态  
                # 版本信息编辑      
                elif info_choice == "3":      
                    new_version = input(f"请输入{game_list[game_index][1]}的新版本信息: ")      
                    if new_version:      
                        game_list[game_index][2] = new_version  # 更新版本信息      
                        save_game_list(game_list, folder_path)  # 保存更新      
                        print("版本信息已更新！")      
                        input("按任意键继续...")      
                        return      
                    else:      
                        # 如果没有输入新版本，提供选项      
                        while True:      
                            print("1. 无版本号")      
                            print("2. 返回目录")      
                            print("3. 未安装")  # 添加新选项      
                            print("4. 已通关")  # 添加新选项      
                            choice = input("请选择: ")      
                            if not choice:      
                                return  # 如果直接回车，直接返回目录的  
                            if choice == "1":      
                                game_list[game_index][2] = ""  # 更新为无版本号      
                                save_game_list(game_list, folder_path)  # 保存更新      
                                print("版本信息已更新！")      
                                input("按任意键继续...")      
                                return      
                            elif choice == "2":      
                                return      
                            elif choice == "3":      
                                game_list[game_index][2] = "未安装"  # 更新为未安装      
                                save_game_list(game_list, folder_path)  # 保存更新      
                                print("版本信息已更新！")      
                                input("按任意键继续...")      
                                return      
                            elif choice == "4":      
                                game_list[game_index][2] = "已通关"  # 更新为已通关      
                                game_list[game_index][4] = "archived" # 同时自动归档    
                                print(f"因您将游戏“{game_list[game_index][1]}”的版本信息设为‘已通关’，该游戏已被自动归档。")    
                                save_game_list(game_list, folder_path)  # 保存更新      
                                print("版本信息已更新！")      
                                input("按任意键继续...")      
                                return      
                            else:      
                                print("无效的选择，请重新输入。")      
                # 状态管理    
                elif info_choice == "4":      
                    status_map = {'visible': '可见', 'hidden': '隐藏', 'active': '激活', 'archived': '已归档'}    
                    while True:      
                        current_visibility = game_list[game_index][3]      
                        current_archive = game_list[game_index][4]      
                        os.system('cls' if os.name == 'nt' else 'clear')    
                        print(f"正在管理: {game_list[game_index][1]}")    
                        print(f"当前状态: 可见性[{status_map[current_visibility]}] / 归档状态[{status_map[current_archive]}]")    
                        print("---------------------------------")    
                        print("1. 切换 可见/隐藏 状态")      
                        print("2. 切换 归档/激活 状态")      
                        state_choice = input("请选择 (直接回车返回): ")      
                        if not state_choice:      
                            return      
                        if state_choice == "1":      
                            game_list[game_index][3] = "hidden" if current_visibility == "visible" else "visible"    
                            save_game_list(game_list, folder_path)    
                            print(f"可见性状态已更新为 -> {status_map[game_list[game_index][3]]}")    
                            input("按任意键继续...")    
                            return    
                        elif state_choice == "2":      
                            game_list[game_index][4] = "archived" if current_archive == "active" else "active"    
                            save_game_list(game_list, folder_path)    
                            print(f"归档状态已更新为 -> {status_map[game_list[game_index][4]]}")    
                            input("按任意键继续...")    
                            return    
                        else:      
                            print("无效的选择。")      
                else:      
                    print("无效的选择，请重新输入。")  
                                            
def reorder_games(game_list, folder_path=None, show_hidden=False):  
    """      
    重新排序游戏列表的函数。
    使用 msvcrt 实现交互式监听（W/S上下移动，Enter选中/放下），用于选择移动某个游戏到新的位置。
    """      
    if not game_list:
        print("当前没有已添加的游戏。")  
        input("按任意键返回目录...")      
        return      
    
    # 物理备份一份原始列表，用于用户选择“取消（Esc）”时恢复
    original_list_backup = [item[:] for item in game_list]
    
    cursor_idx = 0      # 当前光标指向的索引
    selected_idx = -1  # 正在被“抓起”准备移动的索引 (-1 表示未抓起)
    
    while True:      
        # --- 渲染阶段 ---
        os.system('cls' if os.name == 'nt' else 'clear')    
        print(f"  {Color.CYAN}{Color.BOLD}--- 编辑已加入游戏的排序 (交互模式) ---{Color.RESET}")
        print(f"  {Color.GRAY}操作说明: {Color.GOLD}W/S 或 ↑/↓{Color.GRAY} 移动光标 | {Color.GOLD}Enter{Color.GRAY} 选中/放下 | {Color.GREEN}T{Color.GRAY} 保存并退出 | {Color.RED}Esc{Color.GRAY} 取消更改{Color.RESET}")
        print("  " + "─" * 60)

        # 动态计算宽度（克隆主界面 display_game_list 的对齐逻辑）
        max_name_content_width = 0
        max_version_info_width = 0
        for g in game_list:
            is_h_n_s = (g[3] == "hidden" and not show_hidden)
            name_t = "隐藏游戏" if is_h_n_s else g[1]
            max_name_content_width = max(max_name_content_width, get_v_width(name_t))
            if not is_h_n_s and g[2]:
                max_version_info_width = max(max_version_info_width, get_v_width(f"({g[2]})"))
        
        name_col_width = max(max_name_content_width, 25)
        ver_col_width = max(max_version_info_width, 10)
        max_idx_width = max(len(str(len(game_list))), 2)

        # 遍历打印每一行
        for i, game in enumerate(game_list):
            path, name, ver, vis, arc = game
            is_hidden_and_not_shown = (vis == "hidden" and not show_hidden)
            
            # 确定行首指针样式
            pointer = "  "
            line_style = ""
            if i == cursor_idx:
                pointer = f"{Color.GOLD}→ {Color.RESET}"
                line_style = Color.BOLD # 目标行加粗
            if i == selected_idx:
                pointer = f"{Color.GREEN}>>{Color.RESET}" # 抓起行显示绿色双箭头
                line_style = Color.GREEN + Color.BOLD

            # 序号区
            index_str = align_right_v(str(i + 1), max_idx_width) + "."
            prefix = f"{pointer}{Color.GOLD}{index_str}{Color.RESET}"

            # 颜色逻辑 (完全匹配主界面)
            n_color = Color.CYAN
            v_color = Color.GRAY
            if is_hidden_and_not_shown:
                n_color = Color.GRAY
                v_color = Color.GRAY
            elif ver == "未安装":
                n_color = Color.RED
                v_color = Color.RED
            elif ver == "已通关":
                n_color = Color.BLUE
                v_color = Color.BLUE
            elif vis == "hidden":
                n_color = Color.PINK
                v_color = Color.PINK
            elif arc == "archived":
                n_color = Color.ARCHIVED_HIGHLIGHT
                v_color = Color.ARCHIVED_HIGHLIGHT

            # 构建名称和版本
            disp_name = "隐藏游戏" if is_hidden_and_not_shown else name
            padded_name = pad_v(n_color + disp_name + Color.RESET, name_col_width)
            
            version_part = ""
            if not is_hidden_and_not_shown and ver:
                version_part = align_right_v(f"{v_color}({ver}){Color.RESET}", ver_col_width)
            else:
                version_part = " " * ver_col_width
                
            archived_tag = f" {Color.GOLD}[已归档]{Color.RESET}" if (not is_hidden_and_not_shown and arc == "archived") else ""

            print(f"  {prefix} {line_style}{padded_name} {version_part}{archived_tag}{Color.RESET}")

        print("  " + "─" * 60)
        # 实时状态提示
        status_msg = f"{Color.GREEN}正在移动: {game_list[selected_idx][1]}" if selected_idx != -1 else f"{Color.GRAY}当前选中: {game_list[cursor_idx][1]}"
        if (game_list[cursor_idx][3] == "hidden" and not show_hidden): status_msg = f"{Color.GRAY}当前选中: 隐藏游戏"
        print(f"  {status_msg}{Color.RESET}")

        # --- 监听按键阶段 ---
        ch = msvcrt.getch()
        
        # 处理特殊键 (方向键)
        if ch in (b'\x00', b'\xe0'):
            ch = msvcrt.getch()
            if ch == b'H': # Up
                key = 'up'
            elif ch == b'P': # Down
                key = 'down'
            else:
                key = None
        else:
            try:
                char = ch.decode('utf-8').lower()
                if char == 'w': key = 'up'
                elif char == 's': key = 'down'
                elif char == '\r': key = 'enter'
                elif char == 't': key = 'save'
                elif char == '\x1b': key = 'esc' # Esc 键
                else: key = None
            except:
                key = None

        # --- 逻辑处理阶段 ---
        if key == 'up' and cursor_idx > 0:
            if selected_idx != -1: 
                # 交换位置实现跟随移动
                game_list[cursor_idx], game_list[cursor_idx - 1] = game_list[cursor_idx - 1], game_list[cursor_idx]
                selected_idx = cursor_idx - 1
            cursor_idx -= 1
            
        elif key == 'down' and cursor_idx < len(game_list) - 1:
            if selected_idx != -1:
                game_list[cursor_idx], game_list[cursor_idx + 1] = game_list[cursor_idx + 1], game_list[cursor_idx]
                selected_idx = cursor_idx + 1
            cursor_idx += 1
            
        elif key == 'enter':
            # 只有当非隐藏游戏，或者隐藏游戏已激活时，才允许抓起移动
            is_game_hidden = (game_list[cursor_idx][3] == "hidden" and not show_hidden)
            if is_game_hidden:
                SystemLog.warn("该游戏为隐藏游戏，请先激活后再进行移动。")
                time.sleep(0.5)
                continue
                
            if selected_idx == -1:
                selected_idx = cursor_idx # 抓起
            else:
                selected_idx = -1 # 放下
                
        elif key == 'save':
            if selected_idx != -1:
                SystemLog.warn("请先按下 Enter 键放下当前移动的游戏后再保存。")
                time.sleep(1)
                continue
            save_game_list(game_list, folder_path)
            SystemLog.success("游戏排序已成功保存！")
            time.sleep(1)
            break
            
        elif key == 'esc':
            # 恢复备份
            game_list[:] = original_list_backup
            SystemLog.info("操作已取消，未保存任何更改。")
            time.sleep(1)
            break
    
def open_game_folder(game_list, folder_path=None, show_hidden=False):    
    """    
    打开选定游戏的文件夹。    
    提示用户输入要打开文件夹的游戏的序号，并打开相应的文件夹。    
    """    
    while True:    
        # 检查游戏列表是否为空    
        if not game_list:    
            print("当前没有已添加的游戏。")    
            input("按任意键返回目录...")    
            return    
            
        # 显示当前已添加的游戏列表    
        display_game_list(game_list, show_hidden, mode='all')  # 使用 mode='all' 显示所有游戏    
    
        # 提示用户输入要打开文件夹的游戏序号    
        choice = input("请输入想要打开文件夹的游戏的序号: ")    
        if not choice:    
            return  # 如果直接回车，直接返回目录的  
        # 验证用户输入有效性    
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(game_list):    
            print("无效的选择，请重新输入。")    
            input("按任意键继续...")    
        else:    
            game_path = game_list[int(choice) - 1][0]  # 获取游戏的路径    
            game_name = game_list[int(choice) - 1][1]  # 获取游戏的名称    
            game_version = game_list[int(choice) - 1][2]  # 获取游戏的版本信息    
            game_is_hidden_and_not_shown = (game_list[int(choice) - 1][3] == "hidden" and not show_hidden)  
                
            # --- 优先检查是否为隐藏游戏且未激活 ---  
            if game_is_hidden_and_not_shown:    
                print(f"该游戏为隐藏游戏，无法在未激活时打开文件夹。")    
                input("按任意键继续...")    
                return
  
            elif game_version == "未安装":    
                print(f"游戏 {game_name} 未安装，无法打开文件夹。")    
                input("按任意键继续...")    
                return    
            elif game_version == "已通关":    
                print(f"游戏 {game_name} 已通关，无需打开文件夹。")    
                input("按任意键继续...")    
                return    
            
            folder_path = os.path.dirname(game_path)  # 获取文件夹路径    
            if os.path.exists(folder_path):    
                os.startfile(folder_path)  # 打开文件夹    
                print(f"已打开{game_name}的游戏文件夹！")  # 更新输出信息    
                input("按任意键继续...")    
                break  # 退出循环    
            else:    
                print(f"路径错误或文件夹不存在: {folder_path}")    
                input("按任意键返回目录...")    
                return    
    
def manage_games(game_list, folder_path=None, show_hidden=False):
    """    
    管理游戏的菜单，包括添加、删除、编辑、排序游戏以及打开游戏文件夹。    
    用户可以选择相应的操作。    
    """    
    while True:    
        # 打印操作菜单    
        print("1. 加入新游戏")    
        print("2. 删除已添加游戏")    
        print("3. 编辑已加入游戏信息")    
        print("4. 编辑已加入游戏的排序")    
        print("5. 打开游戏文件夹")    
        choice = input("请选择: ")    
        if not choice:    
            return  # 如果直接回车，直接返回目录    
        # 根据用户选择调用对应的函数    
        if choice == "1":    
            add_new_game(game_list, folder_path)  # 调用添加游戏的函数    
            break  # 操作完成，退出循环    
        elif choice == "2":    
            delete_game(game_list, folder_path, show_hidden)  # 调用删除游戏的函数    
            break  # 操作完成，退出循环    
        elif choice == "3":    
            edit_game(game_list, folder_path, show_hidden)  # 调用编辑游戏信息的函数    
            break  # 操作完成，退出循环    
        elif choice == "4":    
            reorder_games(game_list, folder_path, show_hidden)  # 调用重新排序游戏的函数，传入 show_hidden  
            break  # 操作完成，退出循环    
        elif choice == "5":    
            open_game_folder(game_list, folder_path, show_hidden)  # 调用打开游戏文件夹的函数    
            break  # 操作完成，退出循环    
        else:    
            print("无效的选择，请重新输入。")  
    
def show_about():
    """    
    显示脚本的相关信息，如作者、版本和更新日志等。    
    """    
    os.system('cls' if os.name == 'nt' else 'clear')  # 清屏    
    print("\033[1;36m==========================\033[0m")    
    print("\033[1;36m    关于此新游戏启动器\033[0m")    
    print("\033[1;36m==========================\033[0m")    
    # 作者和版本信息    
    print(f"作者：\033[1;34m{AUTHOR}\033[0m")    
    print(f"作者博客：\033[4;36m{BLOG}\033[0m")    
    print(f"\033[1;32m当前版本：{VERSION}\033[0m")  # 使用 ANSI 转义码高亮显示版本信息，绿色高亮显示，使用全局版本变量    
        
    # 显示最近更新（倒序显示最新的3个版本）    
    print("\n\033[1;33m最近更新：\033[0m")    
    for version, date, changes in reversed(CHANGELOG[-3:]):  # 取最后3个并反转    
        print_changelog_entry(version, date, changes)    
        
    # 简洁选项提示    
    print("\n\033[1;36m=====================\033[0m")    
    print("输入 \033[1;33mF\033[0m 查看完整更新日志")    
    print("直接按 \033[1;33m回车\033[0m 返回目录")    
        
    # 用户选择    
    choice = input("\n> 请选择: ").lower()    
    if choice == 'f':    
        show_full_changelog()    
    
def print_changelog_entry(version, date, change_groups):
    """打印单个版本的更新日志（带分类处理、图标宽度自适应，实现完美对齐）"""  
    print(f"\n[\033[1;32m版本{version}\033[0m]-{date}")  
  
    type_config = {  
        "增加": {"color": "\033[1;36m", "icon": "✨"},  
        "改进": {"color": "\033[1;33m", "icon": "⚡"},  
        "移除": {"color": "\033[1;35m", "icon": "🗑️"},  
        "修复": {"color": "\033[1;31m", "icon": "🐛"},  
        "其他": {"color": "\033[1;37m", "icon": "•"}  
    }  
      
    try:  
        terminal_width = shutil.get_terminal_size().columns  
    except OSError:  
        terminal_width = 80 # 默认宽度  
  
    for change_type, descriptions in change_groups:  
        config = type_config.get(change_type, type_config["其他"])  
          
        print(f"{config['color']}{change_type}:\033[0m")  
          
        icon = config['icon']  
        # 如果图标视觉宽度小于2（说明是 '•' 这样的窄符号）  
        if get_v_width(icon) < 2: # <--- 使用 get_v_width  
            icon = ' ' + icon  # 在*前面*追加一个空格，使其“变宽”并右对齐  
          
        plain_prefix = f"  {icon} "   
        prefix_width = get_v_width(plain_prefix) # <--- 使用 get_v_width  
        subsequent_indent = ' ' * prefix_width  
          
        text_wrap_width = terminal_width - prefix_width  
        if text_wrap_width <= 0: text_wrap_width = 1  
  
        for desc in descriptions:  
            if not desc.strip(): continue  
  
            lines = []  
            current_line = ""  
            current_width = 0  
            words = re.split(r'(\s+)', desc)  
  
            for word in words:  
                if not word: continue  
                word_width = get_v_width(word) # <--- 使用 get_v_width  
  
                if current_width + word_width <= text_wrap_width:  
                    current_line += word  
                    current_width += word_width  
                else:  
                    if current_line:  
                        lines.append(current_line)  
                      
                    if word_width > text_wrap_width:  
                        temp_word_part = ""  
                        temp_part_width = 0  
                        for char in word:  
                            char_width = get_v_width(char) # <--- 使用 get_v_width  
                            if temp_part_width + char_width > text_wrap_width:  
                                lines.append(temp_word_part)  
                                temp_word_part = char  
                                temp_part_width = char_width  
                            else:  
                                temp_word_part += char  
                                temp_part_width += char_width  
                        current_line = temp_word_part  
                        current_width = temp_part_width  
                    else:  
                        current_line = word.lstrip()  
                        current_width = get_v_width(current_line) # <--- 使用 get_v_width  
  
            if current_line:  
                lines.append(current_line)  
  
            if lines:  
                print(f"{config['color']}{plain_prefix}{lines[0]}\033[0m")  
                for line in lines[1:]:  
                    print(f"{config['color']}{subsequent_indent}{line}\033[0m")  
    
def show_full_changelog():
    """显示完整更新日志"""    
    os.system('cls' if os.name == 'nt' else 'clear')    
        
    # 打印标题    
    print("\033[1;36m=====================\033[0m")    
    print("\033[1;36m    完整更新日志\033[0m")    
    print("\033[1;36m=====================\033[0m")    
        
    # 显示所有版本    
    for version, date, change_groups in CHANGELOG:    
        print_changelog_entry(version, date, change_groups)    
        
    # 返回提示    
    print("\n\033[1;36m=====================\033[0m")    
    input("按任意键返回...")    
    show_about()    
        
def show_security_settings(folder_path=None):
    """    
    允许用户查看和修改安全设置，包括TOTP验证频率和Windows Hello选项。    
    用户可以选择每次验证、无需验证、自定义验证频率，或切换Windows Hello选项。    
    """    
    # 循环直到用户做出有效选择    
    while True:    
        key, frequency, last_verified, win_hello_enabled = load_safe_config(folder_path)    
        if frequency == "每次验证":    
            current_frequency = "每次验证"  # 如果频率为“每次验证”，展示当前频率为“每次验证”    
        elif frequency == "无需验证":    
            current_frequency = "无需验证"  # 如果频率为“无需验证”，展示当前频率为“无需验证”    
        elif frequency:    
            current_frequency = f"{frequency}小时"  # 如果频率不为空，展示当前频率为某个小时数    
        else:    
            current_frequency = "未设置"    
              
        # 计算下次验证时间    
        if frequency not in ["每次验证", "无需验证"] and last_verified:    
            try:    
                last_verified_dt = datetime.datetime.strptime(last_verified, "%Y/%m/%d-%H:%M:%S")    
                next_verification_dt = last_verified_dt + datetime.timedelta(hours=float(frequency))    
                next_verification_time = next_verification_dt.strftime("%Y/%m/%d-%H:%M:%S")    
            except (ValueError, TypeError):    
                next_verification_time = "N/A" # 如果数据格式错误，则标记为N/A    
        else:    
            next_verification_time = "N/A"  # 如果没有上次验证时间或频率不是自定义的，则设置为 "N/A"    
    
        # 格式化输出字符串，包含当前验证频率和下次验证时间，用 '|' 分隔    
        output_string = f"当前验证频率: {current_frequency} | 下次验证时间: {next_verification_time}"    
        print(output_string)  # 打印格式化后的字符串    
            
        # 动态生成菜单项的描述    
        status_str = "已启用" if win_hello_enabled else "已禁用"    
        feature_desc = "激活隐藏游戏时提供 Windows Hello 选项"    
            
        print("请输入序号以选择操作: ")    
        print("1. 每次验证（默认）")    
        print("2. 无需验证")    
        print("3. 自定义验证频率")    
        print(f"4. {feature_desc} [当前状态:{status_str}]")    
            
        choice = input("请选择 (直接回车返回): ")    
        if not choice:    
            return    
    
        if choice == "1":    
            save_safe_config(key, "每次验证", last_verified, win_hello_enabled, folder_path=folder_path)    
            SystemLog.info("已选择每次验证。")    
            input("按任意键继续...")    
            break    
        elif choice == "2":    
            save_safe_config(key, "无需验证", last_verified, win_hello_enabled, folder_path=folder_path)    
            SystemLog.info("已选择无需验证。")    
            input("按任意键继续...")    
            break    
        elif choice == "3":    
            new_frequency = input("请输入验证频率（单位：小时，范围：0.01到100）: ")    
            if not new_frequency:    
                return # 如果直接回车，直接返回目录    
            # 检查输入是否在范围内    
            try:    
                frequency_value = float(new_frequency)  # 尝试将输入转换为浮点数    
                if 0.01 <= frequency_value <= 100:  # 检查是否在有效范围内    
                    save_safe_config(key, new_frequency, last_verified, win_hello_enabled, folder_path=folder_path)    
                    SystemLog.info(f"验证频率已更新为 {new_frequency} 小时！")    
                    input("按任意键继续...")    
                    break    
                else:    
                    SystemLog.warn("无效的输入，请输入范围在0.01到100之间的数。")    
            except ValueError:    
                SystemLog.warn("无效的输入，请输入数字。")    
            input("按任意键继续...")    
        elif choice == "4":    
            if win_hello_enabled:    
                save_safe_config(key, frequency, last_verified, False, folder_path=folder_path)    
                SystemLog.info(f"功能已禁用：{feature_desc}")    
            else:    
                code = input(f"  {Color.GOLD}请输入TOTP码以启用该功能: {Color.RESET}").strip()    
                if not code:    
                    SystemLog.warn("操作取消。")    
                else:    
                    totp = pyotp.TOTP(key)    
                    SystemLog.step("正在验证TOTP码", "run")  
                    if totp.verify(code):    
                        SystemLog.step("TOTP码验证", "done")  
                        save_safe_config(key, frequency, last_verified, True, folder_path=folder_path)    
                        SystemLog.info(f"功能已成功启用：{feature_desc}")    
                    else:    
                        SystemLog.step("TOTP码验证", "fail")  
                        SystemLog.warn("TOTP码错误，启用失败。")    
            input("按任意键继续...")    
            break    
        # 处理无效选择    
        else:    
            SystemLog.warn("无效的选择，请重新输入。")    
            input("按任意键继续...")    
            break    
    
def configure_webdav(folder_path=None):
    """    
    配置 WebDAV 服务器信息，并将其保存到配置文件 'MRNewGameLauncherWebDAVConfig.txt' 中。    
    用户需要输入 WebDAV 服务器地址、用户名和密码，格式为：http(s)://|用户名|密码。    
    显示当前配置（密码用星号屏蔽），仅在输入新配置时测试连接。    
    特别注意：避免出现 PermissionError: [Errno 13] Permission denied 错误。    
    """    
    if folder_path is None:    
        folder_path = get_or_create_data_folder()    
        
    file_path = os.path.join(folder_path, "MRNewGameLauncherWebDAVConfig.txt")    
        
    # 检查并显示现有配置    
    has_config = False    
    if os.path.exists(file_path):    
        try:    
            # 明确指定 GB18030 编码读取配置    
            with open(file_path, "r", encoding="GB18030") as file:    
                lines = file.readlines()    
                if len(lines) >= 3:    
                    has_config = True    
                    current_url = lines[0].strip().replace("WebDAV URL: ", "")    
                    current_username = lines[1].strip().replace("Username: ", "")    
                    current_password = lines[2].strip().replace("Password: ", "")    
                        
                    # 显示当前配置，密码用星号屏蔽    
                    print("\n当前 WebDAV 配置:")    
                    print(f"服务器地址: {current_url}")    
                    print(f"用户名: {current_username}")    
                    masked_password = '*' * len(current_password) if current_password else ""    
                    print(f"密码: {masked_password}")    
        except Exception as e:    
            SystemLog.warn(f"读取现有 WebDAV 配置时出错: {e}")  
        
    if not has_config:    
        print("\n当前未配置 WebDAV 服务器")    
            
    while True:    
        # 提示用户输入 WebDAV 服务器信息    
        webdav_input = input("\n请输入 WebDAV 服务器信息（格式：http(s)://|用户名|密码）：")    
        if not webdav_input:    
            return  # 如果直接回车，返回上一级菜单    
            
        # 检查输入格式是否正确    
        if webdav_input.count('|') != 2:    
            SystemLog.warn("输入格式不正确，请按照格式输入：http(s)://|用户名|密码")  
            input("按任意键继续...")    
            continue    
            
        # 解析输入内容    
        webdav_url, username, password = webdav_input.split('|')    
            
        # 验证 URL 格式    
        if not webdav_url.startswith(('http://', 'https://')):    
            SystemLog.warn("WebDAV 服务器地址必须以 http:// 或 https:// 开头")  
            input("按任意键继续...")    
            continue    
            
        # 测试新连接    
        SystemLog.step("正在测试 WebDAV 连接", "run")  
        if test_webdav_connection(webdav_url, username, password):    
            SystemLog.step("WebDAV 连接测试", "done")  
        else:    
            SystemLog.step("WebDAV 连接测试", "fail")  
            retry = input(f"\n  {Color.GOLD}连接测试失败！是否仍要保存此配置？(y/n): {Color.RESET}").lower()    
            if retry != 'y':    
                continue    
            
        # 保存配置到文件    
        try:    
            # 确保文件可写    
            if os.path.exists(file_path):    
                # 如果文件存在，取消隐藏属性（如果隐藏）    
                unhide_file(file_path)    
                
            # 尝试写入文件，明确指定 GB18030 编码    
            with open(file_path, "w", encoding="GB18030") as file:    
                file.write(f"WebDAV URL: {webdav_url}\n")    
                file.write(f"Username: {username}\n")    
                file.write(f"Password: {password}\n")    
                
            # 写入完成后隐藏文件以保护数据    
            hide_file(file_path)    
                
            SystemLog.info("WebDAV 配置已保存！")  
            input("按任意键继续...")    
            break    
        except PermissionError:    
            SystemLog.warn("权限不足，无法保存配置文件。请检查文件权限或尝试以管理员身份运行程序。")  
            input("按任意键继续...")    
            break    
        except Exception as e:    
            SystemLog.warn(f"保存 WebDAV 配置时出错: {e}")  
            input("按任意键继续...")    
            break    
    
def test_webdav_connection(url, username, password, max_attempts=3):
    """测试 WebDAV 连接是否成功，最多尝试3次"""    
    options = {    
        'webdav_hostname': url,    
        'webdav_login': username,    
        'webdav_password': password,    
        'webdav_encoding': 'utf-8' # 增加 WebDAV 编码设置，确保文件名和路径正确处理  
    }    
        
    for attempt in range(1, max_attempts + 1):    
        try:    
            client = Client(options)    
            client.list() # 尝试列出目录，验证连接    
            return True    
        except Exception as e:    
            if attempt < max_attempts:    
                SystemLog.info(f"WebDAV 连接失败 (尝试 {attempt}/{max_attempts}): {e}")  
                time.sleep(1) # 增加延迟，避免频繁重试  
            else:    
                SystemLog.warn(f"WebDAV 连接最终失败: {e}")  
        
    return False    
    
def derive_encryption_key(timestamp):
    """    
    基于备份时间戳生成加密密钥    
    使用PBKDF2派生一个256位的AES密钥    
        
    参数:    
        timestamp (str): 备份文件的时间戳，格式为 'YYYY.MM.DD_HH-MM-SS'    
        
    返回:    
        bytes: 256位AES密钥    
    """    
    # 使用时间戳作为密码，固定盐值    
    password = timestamp.encode('utf-8')    
        
    # 使用PBKDF2HMAC派生密钥    
    kdf = PBKDF2HMAC(    
        algorithm=hashes.SHA256(),    
        length=32,  # 256位密钥    
        salt=FIXED_SALT,    
        iterations=100000,  # 迭代次数    
    )    
        
    # 派生并返回密钥    
    return kdf.derive(password)    
    
def encrypt_data(data, key):
    """    
    使用AES-GCM加密数据    
        
    参数:    
        data (bytes): 要加密的数据    
        key (bytes): 256位AES密钥    
        
    返回:    
        bytes: 加密后的数据（包含随机生成的nonce和认证标签）    
    """    
    # 创建AESGCM对象    
    aesgcm = AESGCM(key)    
        
    # 生成随机12字节nonce    
    nonce = os.urandom(12)    
        
    # 加密数据（AES-GCM会自动添加认证标签）    
    ciphertext = aesgcm.encrypt(nonce, data, None)    
        
    # 将nonce和密文组合在一起返回    
    return nonce + ciphertext    
    
def decrypt_data(encrypted_data, key):
    """    
    使用AES-GCM解密数据    
        
    参数:    
        encrypted_data (bytes): 加密的数据（包含nonce和认证标签）    
        key (bytes): 256位AES密钥    
        
    返回:    
        bytes: 解密后的原始数据    
    """    
    # 创建AESGCM对象    
    aesgcm = AESGCM(key)    
        
    # 提取nonce（前12字节）    
    nonce = encrypted_data[:12]    
        
    # 提取密文（剩余部分）    
    ciphertext = encrypted_data[12:]    
        
    # 解密数据    
    try:    
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)    
        return plaintext    
    except Exception as e:    
        # 捕获并重新抛出更具体的解密失败信息，方便调试    
        raise ValueError(f"解密失败，请检查并确保压缩包为原始文件名及其内容未被篡改: {e}")    
    
def perform_backup(folder_path=None):  
    """      
    执行备份操作，将游戏列表、TOTP数据和版本文件打包压缩，并上传到WebDAV服务器。      
    通过以下措施防止数据泄露和文件篡改：      
    1. 文件名混淆：使用随机8位字符串重命名敏感文件（如MRNewGameLauncherGameList.txt、MRNewGameLauncherSafeConfig.txt、MRNewGameLauncherConfigVersion.txt）。      
    2. AES-GCM加密：对所有文件的敏感数据进行加密      
    3. 哈希校验：记录混淆文件名且加密后的文件和加密后的映射表的SHA256哈希值，并对备份文件进行完整性校验。      
    4. 映射表：将混淆后的文件名与原始文件名的映射关系记录在manifest.mrmap文件中。      
    5. 内存操作：全程使用内存中的文件操作，避免在磁盘上生成临时文件。      
    6. 将所有混淆文件名且加密后的文件、加密后的映射表和加密后的校验文件打包为一个ZIP文件，并上传到WebDAV服务器进行备份。      
    """      
    if folder_path is None:      
        folder_path = get_or_create_data_folder()      
          
    # 加载 WebDAV 配置      
    webdav_config_path = os.path.join(folder_path, "MRNewGameLauncherWebDAVConfig.txt")      
    if not os.path.exists(webdav_config_path):      
        SystemLog.warn("未配置 WebDAV 服务器，请先配置 WebDAV 服务器。")    
        input("按任意键继续...")      
        return      
          
    # 读取 WebDAV 配置      
    try:      
        # 明确指定 GB18030 编码读取配置      
        with open(webdav_config_path, "r", encoding="GB18030") as file:      
            lines = file.readlines()      
            webdav_url = lines[0].strip().replace("WebDAV URL: ", "")      
            username = lines[1].strip().replace("Username: ", "")      
            password = lines[2].strip().replace("Password: ", "")      
    except Exception as e:      
        SystemLog.warn(f"读取 WebDAV 配置时出错: {e}")    
        input("按任意键继续...")      
        return      
          
    # 初始化 WebDAV 客户端      
    options = {      
        'webdav_hostname': webdav_url,      
        'webdav_login': username,      
        'webdav_password': password,      
        'webdav_encoding': 'utf-8' # 增加 WebDAV 编码设置    
    }      
    client = Client(options)      
      
    # 生成备份文件名（基于当前时间）      
    timestamp = datetime.datetime.now().strftime('%Y.%m.%d_%H-%M-%S')      
    backup_filename = f"backup_{timestamp}.zip"      
          
    # 生成加密密钥（基于时间戳）      
    encryption_key = derive_encryption_key(timestamp)      
              
    # 定义需要混淆的敏感文件列表      
    sensitive_files = [      
        "MRNewGameLauncherConfigVersion.txt",      
        "MRNewGameLauncherGameList.txt",      
        "MRNewGameLauncherSafeConfig.txt"      
    ]      
          
    manifest = {}      # 映射关系：混淆文件名 -> 原始文件名      
    checksum_dict = {} # 存储每个加密后文件的SHA256哈希校验值      
          
    # 创建内存中的ZIP压缩包      
    zip_buffer = io.BytesIO()      
    try:    
        SystemLog.step("正在打包敏感配置文件", "run")    
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:      
            # 对每个敏感文件进行混淆和加密处理      
            for original_filename in sensitive_files:      
                file_path = os.path.join(folder_path, original_filename)      
                if os.path.exists(file_path):      
                    # 读取文件内容，明确指定 GB18030 编码      
                    with open(file_path, "r", encoding="GB18030") as f:      
                        content = f.read()      
                              
                    # 生成随机8位字符串作为混淆文件名      
                    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))      
                    obfuscated_filename = random_str + ".enc"      
                    manifest[obfuscated_filename] = original_filename      
                          
                    # 使用GB18030编码将内容转换为二进制数据并加密      
                    content_bytes = content.encode("GB18030")      
                    encrypted_data = encrypt_data(content_bytes, encryption_key)      
                          
                    # 计算每个混淆文件名且加密后的文件的SHA256哈希校验值      
                    hash_value = hashlib.sha256(encrypted_data).hexdigest()      
                    checksum_dict[obfuscated_filename] = hash_value      
                          
                    # 将混淆文件名且加密后的文件写入压缩包      
                    zip_file.writestr(obfuscated_filename, encrypted_data)      
                  
            # 生成映射表文件 manifest.mrmap（记录混淆文件名与原始文件名的映射关系）      
            manifest_lines = []      
            for obf, orig in manifest.items():      
                manifest_lines.append(f"{obf} → {orig}")      
            manifest_content = "\n".join(manifest_lines)      
            manifest_bytes = manifest_content.encode("GB18030")      
          
            # 加密映射表      
            encrypted_manifest = encrypt_data(manifest_bytes, encryption_key)      
                  
            # 计算加密后映射表文件的SHA256哈希校验值      
            manifest_hash = hashlib.sha256(encrypted_manifest).hexdigest()      
            checksum_dict["manifest.mrmap"] = manifest_hash      
                  
            # 将加密后的映射表文件写入压缩包      
            zip_file.writestr("manifest.mrmap", encrypted_manifest)      
                  
            # 生成校验文件 checksum.sha256（格式：文件名:哈希值）      
            checksum_lines = []      
            for filename, hash_val in checksum_dict.items():      
                checksum_lines.append(f"{filename}:{hash_val}")      
            checksum_content = "\n".join(checksum_lines)      
            checksum_bytes = checksum_content.encode("GB18030")      
                  
            # 加密校验文件      
            encrypted_checksum = encrypt_data(checksum_bytes, encryption_key)      
                  
            # 将加密后的校验文件写入压缩包      
            zip_file.writestr("checksum.sha256", encrypted_checksum)      
              
        SystemLog.step("配置文件打包加密", "done")    
    
        # 上传压缩包到 WebDAV 服务器      
        SystemLog.step("正在上传备份文件到 WebDAV 服务器", "run")    
        try:      
            # 确保备份目录存在      
            backup_dir = "MRNewGameLauncherDataBackup"      
            
            # 为上传初期的连接检查增加异常保护
            if not client.check(backup_dir):      
                client.mkdir(backup_dir)
                  
            zip_buffer.seek(0)  # 将指针重置到文件开头      
            client.upload_to(buff=zip_buffer, remote_path=f"{backup_dir}/{backup_filename}")      
            SystemLog.step(f"备份文件上传", "done")    
            SystemLog.info(f"备份成功：{backup_filename}")    
        except Exception as e:      
            SystemLog.step("备份文件上传", "fail")    
            SystemLog.warn(f"上传备份文件时出错或无法连接服务器: {e}")    
    finally:      
        zip_buffer.close()  # 关闭内存文件      
          
    input("按任意键继续...")
        
def decrypt_all_files(zip_file, encryption_key, exclude_files=None):
    """    
    解密备份文件中的所有文件（除了排除的文件）    
        
    参数:    
        zip_file: ZipFile对象，表示备份文件    
        encryption_key: 解密密钥    
        exclude_files: 要排除的文件列表    
            
    返回:    
        dict: 解密后的文件内容，格式为 {文件名: 解密后的内容}    
        None: 如果解密失败    
    """    
    if exclude_files is None:    
        exclude_files = []    
        
    decrypted_files = {}    
        
    try:    
        for filename in zip_file.namelist():    
            # 跳过排除的文件    
            if filename in exclude_files:    
                continue    
                
            # 读取加密文件    
            encrypted_data = zip_file.read(filename)    
                
            # 解密文件    
            try:    
                decrypted_data = decrypt_data(encrypted_data, encryption_key)    
                decrypted_files[filename] = decrypted_data    
            except Exception as e:    
                SystemLog.warn(f"解密文件 {filename} 失败：{e}")  
                return None    
            
        return decrypted_files    
    except Exception as e:    
        SystemLog.warn(f"解密文件过程中出错：{e}")  
        return None    
    
def verify_backup_integrity(zip_file, encryption_key):
    """    
    验证备份完整性    
        
    参数:    
        zip_file: ZipFile对象，表示备份文件    
        encryption_key: 解密密钥    
            
    返回:    
        (bool, str): 验证结果和错误信息（如果有）    
    """    
    # 定义备份文件中必须包含的文件列表    
    required_files = ['manifest.mrmap', 'checksum.sha256']    
        
    # 检查备份文件中是否包含所有必需的文件    
    for f in required_files:    
        if f not in zip_file.namelist():    
            # 如果缺少必要文件，返回验证失败和错误信息    
            if f == 'manifest.mrmap':    
                return False, "缺少必要的映射表文件"    
            elif f == 'checksum.sha256':    
                return False, "缺少必要的校验文件"    
    
    try:    
        # 1. 首先解密校验文件    
        # 读取加密的校验文件 checksum.sha256 的内容    
        encrypted_checksum = zip_file.read("checksum.sha256")    
            
        # 解密校验文件    
        try:    
            checksum_bytes = decrypt_data(encrypted_checksum, encryption_key)    
        except ValueError as e:    
            # 直接返回解密失败的原始错误信息，避免重复包装    
            return False, str(e)    
                
        checksum_content = checksum_bytes.decode("GB18030")    
            
        # 将校验文件内容解析为字典，格式为 {文件名: 哈希值}    
        checksum_dict = {}    
        for line in checksum_content.splitlines():    
            if ":" in line:    
                filename, hash_val = line.split(":", 1)    
                checksum_dict[filename] = hash_val    
            
        # 2. 验证所有文件的哈希值    
        # 用于存储验证过程中发现的错误    
        errors = []    
            
        # 遍历备份文件中的所有文件    
        for filename in zip_file.namelist():    
            # 跳过校验文件本身    
            if filename == 'checksum.sha256':    
                continue    
                
            # 读取文件内容    
            content = zip_file.read(filename)    
                
            # 计算文件的 SHA256 哈希值    
            computed_hash = hashlib.sha256(content).hexdigest()    
                
            # 检查文件是否在校验字典中    
            if filename not in checksum_dict:    
                # 如果文件未记录在校验字典中，添加错误信息    
                errors.append(f"检测到未记录的文件‘{filename}’，此文件未包含在校验列表中。")    
                continue    
                    
            # 检查计算出的哈希值是否与校验字典中的哈希值匹配    
            if checksum_dict[filename] != computed_hash:    
                # 如果哈希值不匹配，添加错误信息    
                errors.append(f"文件 {filename} 哈希不匹配")    
            
        # 如果发现任何错误，返回验证失败和错误信息    
        if errors:    
            return False, "；".join(errors)    
            
        # 如果所有文件都通过验证，返回验证成功    
        return True, ""    
            
    except Exception as e:    
        # 如果在验证过程中发生异常，返回验证失败和异常信息    
        return False, f"校验过程异常：{str(e)}"    
    
def check_version_compatibility(backup_version):
    """    
    版本兼容性检查    
    """    
    if backup_version is None:    
        return False, "备份文件中未找到版本信息，可能为旧版本备份"    
      
    try:    
        # 提取纯数字版本（假设版本格式为x.y）    
        current_main = float(VERSION)    
        backup_main = float(backup_version)    
    except ValueError: # 捕获float转换错误    
        return False, f"版本格式不兼容（当前：{VERSION}，备份：{backup_version}）"    
      
    if current_main != backup_main:    
        return False, f"主版本不兼容（当前：{VERSION}，备份：{backup_version}）"    
    return True, ""    
        
def restore_backup(client, folder_path, backup_file, restore_gamelist=False, restore_safe_config=False):  
    """        
    从备份文件中恢复游戏列表和/或安全配置。      
    验证失败时不还原任何文件。        
    特别注意：避免出现 PermissionError: [Errno 13] Permission denied 错误。        
    写入完成后重新隐藏文件。        
    验证成功后输出安全配置中的TOTP 密钥并展示 QR 码。      
    所有恢复操作完成后提示用户重新打开程序。        
    包含版本兼容性检查以及备份文件完整性验证与映射表解析        
    """        
    try:        
        # 第一阶段：下载备份文件到内存        
        SystemLog.step("正在从远程 WebDAV 下载备份包", "run")    
        zip_buffer = io.BytesIO()        
        
        # 增加对远程下载的网络异常处理
        try:
            client.download_from(buff=zip_buffer, remote_path=backup_file)        
        except Exception as e:
            SystemLog.step("远程下载失败", "fail")
            SystemLog.warn(f"从 WebDAV 下载备份文件时发生错误: {e}")
            input("按任意键继续...")
            return

        zip_buffer.seek(0)        
        SystemLog.step("远程备份包下载", "done")    
                
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:        
            # 1. 从文件名中提取时间戳        
            # 格式: backup_YYYY.MM.DD_HH-MM-SS.zip        
            SystemLog.step("正在解析备份元数据", "run")    
            filename = os.path.basename(backup_file)        
            timestamp_match = re.search(r'backup_(\d{4}\.\d{2}\.\d{2}_\d{2}-\d{2}-\d{2})\.zip', filename)    
            if not timestamp_match:    
                SystemLog.step("备份元数据解析", "fail")    
                SystemLog.warn("备份文件名格式不正确，无法提取时间戳进行解密。")    
                input("按任意键继续...")    
                return    
            timestamp = timestamp_match.group(1)    
                        
            # 生成用于解密的加密密钥（基于文件名中的时间戳）        
            encryption_key = derive_encryption_key(timestamp)        
            SystemLog.step("备份元数据解析", "done")    
    
            # 2. 验证备份完整性：检查必需文件和哈希校验        
            SystemLog.step("正在验证备份文件完整性", "run")    
            valid, reason = verify_backup_integrity(zip_file, encryption_key)        
            if not valid:        
                SystemLog.step("备份完整性校验", "fail")    
                SystemLog.warn(f"该备份文件验证失败: {reason}")    
                choice = input(f"\n  {Color.GOLD}是否删除该备份文件？(y/n): {Color.RESET}").lower()    
                if choice == 'y':        
                    try:        
                        client.clean(backup_file)        
                        SystemLog.info("该备份文件已成功删除。")    
                    except Exception as e:        
                        SystemLog.warn(f"删除该备份文件时出错: {e}")    
                    input("按任意键继续...")        
                    return        
                else:        
                    SystemLog.info("该备份文件未被删除，你可以重新选择其他的备份文件进行恢复。")    
                    input("按任意键继续...")        
                    return        
            SystemLog.step("备份文件完整性校验", "done")    
                        
            # 3. 解密所有文件（除了校验文件，因为它已经在验证过程中被解密）        
            SystemLog.step("正在解密所有配置文件数据", "run")    
            decrypted_files = decrypt_all_files(zip_file, encryption_key, exclude_files=["checksum.sha256"])        
            if decrypted_files is None:        
                SystemLog.step("配置文件数据解密", "fail")    
                SystemLog.warn("解密文件失败，无法继续恢复操作。")    
                input("按任意键继续...")        
                return        
            SystemLog.step("配置文件数据解密", "done")    
                        
            # 4. 解析映射表，按照映射表还原原始文件名        
            SystemLog.step("正在解析文件映射关系", "run")    
            try:        
                manifest_bytes = decrypted_files["manifest.mrmap"]        
                manifest_content = manifest_bytes.decode("GB18030")        
                            
                # 解析映射表，构建混淆文件名到原始文件名的映射        
                manifest_dict = {}  # 混淆文件名 -> 原始文件名        
                for line in manifest_content.splitlines():        
                    if "→" in line:        
                        parts = line.split("→")        
                        obf = parts[0].strip()        
                        orig = parts[1].strip()        
                        manifest_dict[obf] = orig        
            except Exception as e:        
                SystemLog.step("文件映射关系解析", "fail")    
                SystemLog.warn(f"解析映射表失败: {e}")    
                input("按任意键继续...")        
                return        
            SystemLog.step("文件映射关系解析", "done")    
                                    
            # 5. 读取备份版本并进行版本检查        
            SystemLog.step("正在检查版本兼容性", "run")    
            version_file_obf = None        
            for obf, orig in manifest_dict.items():        
                if orig == "MRNewGameLauncherConfigVersion.txt":        
                    version_file_obf = obf        
                    break        
                                
            backup_version = None        
            if version_file_obf and version_file_obf in decrypted_files:        
                try:        
                    version_bytes = decrypted_files[version_file_obf]        
                    version_content = version_bytes.decode("GB18030")        
                    backup_version = version_content.split('Ver：')[-1].strip()        
                except Exception as e:        
                    SystemLog.step("版本兼容性检查", "fail")    
                    SystemLog.warn(f"解析版本信息失败: {e}")    
                    input("按任意键继续...")        
                    return        
                      
            compatible, msg = check_version_compatibility(backup_version)        
            if not compatible:        
                SystemLog.step("版本兼容性检查", "fail")    
                SystemLog.warn(f"您正在尝试恢复不兼容版本的配置，可能会引发未知错误！")    
                SystemLog.warn(f"版本警告: {msg}")    
                choice = input(f"\n  {Color.GOLD}是否强制继续恢复？(y/n): {Color.RESET}").lower()    
                if choice != 'y':        
                    SystemLog.info("恢复操作已取消。")    
                    input("按任意键继续...")        
                    return        
            SystemLog.step("版本兼容性检查", "done")    
                            
            # 6. 验证安全配置（如果需要恢复安全配置）      
            backup_safe_config_data = None        
            backup_totp_key = None        
                            
            if restore_safe_config:      
                SystemLog.step("正在验证安全配置完整性", "run")    
                # 查找安全配置文件      
                safe_config_file_obf = None        
                for obf, orig in manifest_dict.items():        
                    if orig == "MRNewGameLauncherSafeConfig.txt":      
                        safe_config_file_obf = obf        
                        break        
                            
                if not safe_config_file_obf or safe_config_file_obf not in decrypted_files:        
                    SystemLog.step("安全配置完整性验证", "fail")    
                    SystemLog.warn("备份文件中缺少安全配置文件。")    
                    input("按任意键继续...")        
                    return        
                            
                # 读取解密后的安全配置数据      
                try:        
                    safe_config_bytes = decrypted_files[safe_config_file_obf]        
                    backup_safe_config_data = safe_config_bytes.decode("GB18030")        
                    backup_totp_key = backup_safe_config_data.split('\n')[0].replace("TOTP密钥：", "").strip()        
                except Exception as e:        
                    SystemLog.step("安全配置完整性验证", "fail")    
                    SystemLog.warn(f"解析安全配置数据失败: {e}")    
                    input("按任意键继续...")        
                    return        
                            
                # 加载当前的安全配置以获取TOTP密钥      
                current_totp_key, _, _, _ = load_safe_config(folder_path)      
                            
                # 如果备份的 TOTP 密钥与当前密钥不一致，要求用户输入 TOTP 码验证        
                if backup_totp_key != current_totp_key:        
                    SystemLog.info("检测到备份文件内的TOTP密钥与当前密钥不一致。") # 改为 info    
                    code = input(f"\n  {Color.GOLD}请输入当前的 TOTP 码以验证：{Color.RESET}").strip()    
                    if not code:        
                        SystemLog.warn("TOTP 验证失败，恢复操作已取消。")    
                        input("按任意键继续...")        
                        return        
                                
                    totp = pyotp.TOTP(current_totp_key)        
                    SystemLog.step("正在验证当前 TOTP 码", "run")    
                    if not totp.verify(code):        
                        SystemLog.step("当前 TOTP 码验证", "fail")    
                        SystemLog.warn("TOTP 验证失败，恢复操作已取消。")    
                        input("按任意键继续...")        
                        return        
                    SystemLog.step("当前 TOTP 码验证", "done")    
                SystemLog.step("安全配置完整性验证", "done")    
                            
            # 7. 恢复游戏列表（如果需要）        
            if restore_gamelist:        
                SystemLog.step("正在还原游戏列表 (MRNewGameLauncherGameList.txt)", "run")    
                # 查找游戏列表文件        
                gamelist_file_obf = None        
                for obf, orig in manifest_dict.items():        
                    if orig == "MRNewGameLauncherGameList.txt":        
                        gamelist_file_obf = obf        
                        break        
                                
                if not gamelist_file_obf or gamelist_file_obf not in decrypted_files:        
                    SystemLog.step("游戏列表还原", "fail")    
                    SystemLog.warn("备份文件中缺少游戏列表文件。")    
                    input("按任意键继续...")        
                    return        
                                
                # 读取解密后的游戏列表        
                try:        
                    gamelist_bytes = decrypted_files[gamelist_file_obf]        
                    game_list_data = gamelist_bytes.decode("GB18030")        
                except Exception as e:        
                    SystemLog.step("游戏列表还原", "fail")    
                    SystemLog.warn(f"解析游戏列表失败: {e}")    
                    input("按任意键继续...")        
                    return        
                                
                # 确保文件可写        
                game_list_path = os.path.join(folder_path, "MRNewGameLauncherGameList.txt")        
                if os.path.exists(game_list_path):        
                    unhide_file(game_list_path)  # 取消隐藏属性        
                                
                # 写入游戏列表文件        
                try:        
                    with open(game_list_path, "w", encoding="GB18030") as file: # 明确指定 GB18030 编码写入      
                        file.write(game_list_data)        
                finally:        
                    hide_file(game_list_path)  # 写入完成后重新隐藏文件        
                SystemLog.step("游戏列表数据还原", "done")    
                            
            # 8. 恢复安全配置数据（如果需要）      
            if restore_safe_config:      
                SystemLog.step("正在还原安全配置 (MRNewGameLauncherSafeConfig.txt)", "run")    
                safe_config_path = os.path.join(folder_path, "MRNewGameLauncherSafeConfig.txt")      
                if os.path.exists(safe_config_path):        
                    unhide_file(safe_config_path)  # 取消隐藏属性        
                                
                # 写入安全配置数据文件      
                try:        
                    with open(safe_config_path, "w", encoding="GB18030") as file: # 明确指定 GB18030 编码写入      
                        file.write(backup_safe_config_data)        
                                    
                    # 输出备份文件内的 TOTP 密钥        
                    SystemLog.info(f"备份文件内的 TOTP 密钥: {backup_totp_key}")    
                                    
                    # 通过 QR 码展示密钥        
                    SystemLog.info("TOTP 密钥的 QR 码:")    
                    display_qr_code(backup_totp_key)        
                                    
                    # 提示用户妥善保管密钥        
                    SystemLog.info("请妥善保管您的 TOTP 密钥。")    
                finally:        
                    hide_file(safe_config_path)  # 写入完成后重新隐藏文件        
                SystemLog.step("安全配置与 TOTP 密钥还原", "done")    
                            
            SystemLog.success("所有数据已成功恢复，程序即将退出。")    
            input("  按任意键关闭程序...")    
            os._exit(0)  # 退出程序        
                
    except Exception as e:        
        SystemLog.step("恢复进程", "fail")    
        SystemLog.warn(f"意外中断: {str(e)}")    
        input("按任意键继续...")        
    finally:        
        zip_buffer.close()
                        
def manage_backups(folder_path=None):  
    """        
    管理 WebDAV 服务器上的备份文件，包括列出备份、恢复备份和删除备份。        
    """        
    if folder_path is None:        
        folder_path = get_or_create_data_folder()        
            
    # 加载 WebDAV 配置        
    webdav_config_path = os.path.join(folder_path, "MRNewGameLauncherWebDAVConfig.txt")        
    if not os.path.exists(webdav_config_path):        
        SystemLog.warn("未配置 WebDAV 服务器，请先配置 WebDAV 服务器。")    
        input("按任意键继续...")        
        return        
            
    # 读取 WebDAV 配置        
    try:        
        # 明确指定 GB18030 编码读取配置      
        with open(webdav_config_path, "r", encoding="GB18030") as file:      
            lines = file.readlines()        
            webdav_url = lines[0].strip().replace("WebDAV URL: ", "")        
            username = lines[1].strip().replace("Username: ", "")        
            password = lines[2].strip().replace("Password: ", "")        
    except Exception as e:        
        SystemLog.warn(f"读取 WebDAV 配置时出错: {e}")    
        input("按任意键继续...")        
        return        
            
    # 初始化 WebDAV 客户端        
    options = {        
        'webdav_hostname': webdav_url,        
        'webdav_login': username,        
        'webdav_password': password,        
        'webdav_encoding': 'utf-8' # 增加 WebDAV 编码设置    
    }        
    client = Client(options)        
            
    # 获取备份文件列表        
    backup_dir = "MRNewGameLauncherDataBackup"        
    
    # 增加异常捕获，防止连接失败导致崩溃
    try:
        SystemLog.step("正在检查 WebDAV 远程状态", "run")
        if not client.check(backup_dir):        
            SystemLog.step("检查远程状态", "done")
            SystemLog.info("备份目录不存在，请先创建备份。")
            input("按任意键继续...")
            return        
            
        backup_files = client.list(backup_dir)        
        SystemLog.step("远程列表获取", "done")
    except Exception as e:
        SystemLog.step("远程访问失败", "fail")
        SystemLog.warn(f"无法连接到 WebDAV 服务器，请检查网络或地址有效性：{e}")
        input("按任意键继续...")
        return
            
    backup_files = [f for f in backup_files if f.endswith('.zip')]  # 只保留 .zip 文件        
    backup_files.sort(reverse=True)  # 按时间倒序排序        
            
    if not backup_files:        
        SystemLog.info("没有可用的备份文件。")    
        input("按任意键继续...")        
        return        
            
    # 显示备份文件列表        
    print("备份文件列表：")        
    for i, backup_file in enumerate(backup_files, start=1):        
        print(f"{i}. {backup_file}")        
            
    # 提示用户选择备份文件        
    choice = input("请输入要操作的备份文件序号（直接回车返回）：")        
    if not choice:        
        return        
            
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(backup_files):        
        SystemLog.warn("无效的选择，请重新输入。")    
        input("按任意键继续...")        
        return        
            
    selected_backup = backup_files[int(choice) - 1]        
    remote_path = f"{backup_dir}/{selected_backup}"        
            
    # 提供操作选项        
    print("1. 恢复游戏列表")        
    print("2. 恢复安全配置")      
    print("3. 全部恢复")        
    print("4. 删除备份")        
    operation = input("请选择操作（直接回车返回）：")        
            
    if not operation:        
        return  # 返回到上一级菜单        
            
    if operation == "1":        
        restore_backup(client, folder_path, remote_path, restore_gamelist=True, restore_safe_config=False)      
    elif operation == "2":        
        restore_backup(client, folder_path, remote_path, restore_gamelist=False, restore_safe_config=True)      
    elif operation == "3":        
        restore_backup(client, folder_path, remote_path, restore_gamelist=True, restore_safe_config=True)      
    elif operation == "4":        
        try:        
            SystemLog.step(f"正在删除备份文件: {selected_backup}", "run")    
            # 使用 clean 方法删除文件        
            client.clean(remote_path)        
            SystemLog.step("备份文件删除", "done")    
            SystemLog.info(f"备份文件 {selected_backup} 已删除。")    
        except Exception as e:        
            SystemLog.step("备份文件删除", "fail")    
            SystemLog.warn(f"删除备份文件时出错: {e}")        
        input("按任意键继续...")        
    else:        
        SystemLog.warn("无效的选择，请重新输入。")    
        input("按任意键继续...")
                            
def show_settings_menu(folder_path=None):
    """    
    设置主菜单，包含安全设置和备份设置    
    """    
    while True:    
        os.system('cls')    
        print("=====================")    
        print("      设置菜单")    
        print("=====================")    
        print("1. 安全设置")    
        print("2. 备份设置")    
        choice = input("请选择（直接回车返回）：")    
    
        if not choice:    
            return    
            
        if choice == "1":    
            show_security_settings(folder_path)    
        elif choice == "2":    
            while True:    
                os.system('cls')    
                print("=====================")    
                print("     备份设置")    
                print("=====================")    
                print("1. 配置WebDAV服务器")    
                print("2. 立即备份")    
                print("3. 管理备份")    
                sub_choice = input("请选择：")    
    
                if not sub_choice:    
                    break  # 返回到上一级菜单    
                        
                if sub_choice == "1":    
                    configure_webdav(folder_path)    
                elif sub_choice == "2":    
                    perform_backup(folder_path)    
                elif sub_choice == "3":    
                    manage_backups(folder_path)    
                else:    
                    SystemLog.warn("无效的选择，请重新输入。")  
                    input("按任意键继续...")    
        else:    
            SystemLog.warn("无效的选择，请重新输入。")  
            input("按任意键继续...")    
    
def authenticate_with_windows_hello():
    """    
    尝试使用本地 Windows Hello 提示（PIN、生物识别等）对用户进行身份验证，并返回结果状态。    
    
    返回:    
        str: 表示验证结果的状态字符串。    
             'SUCCESS'       - 验证成功    
             'CANCELED'      - 用户手动取消    
             'NOT_AVAILABLE' - 系统未设置 Windows Hello    
             'FAILED'        - 其他所有失败情况    
    """    
    async def verify_user_async():    
        """Windows Hello 验证的核心异步逻辑。"""    
        # 1. 检查 Windows Hello 在系统上是否可用。    
        availability = await UserConsentVerifier.check_availability_async()    
        if availability != UserConsentVerifierAvailability.AVAILABLE:    
            return 'NOT_AVAILABLE'    
    
        SystemLog.step("正在调用 Windows Hello 验证界面", "run")  
        # 2. 请求用户验证。    
        prompt_message = "MRNewGameLauncher 正在尝试显示隐藏游戏。请验证您的身份以允许此操作。"    
        result = await UserConsentVerifier.request_verification_async(prompt_message)    
    
        # 3. 检查验证结果。    
        if result == UserConsentVerificationResult.VERIFIED:    
            SystemLog.step("Windows Hello 验证", "done")  
            return 'SUCCESS'    
        elif result == UserConsentVerificationResult.CANCELED:    
            SystemLog.step("Windows Hello 验证", "fail")  
            return 'CANCELED'    
        else:    
            SystemLog.step("Windows Hello 验证", "fail")  
            return 'FAILED'    
    
    # 使用 asyncio.run() 来运行异步函数    
    try:    
        return asyncio.run(verify_user_async())    
    except Exception: # 捕获 asyncio.run 自身的异常    
        SystemLog.warn("Windows Hello API 调用异常。")  
        return 'FAILED'    
  
def show_archived_games(game_list, folder_path, show_hidden, key):
    """  
    显示已归档的游戏。  
    支持调用全局函数来激活/重新隐藏游戏。  
    返回最新的 show_hidden 状态。  
    """  
    while True:  
        os.system('cls' if os.name == 'nt' else 'clear')  
        print("=====================")  
        print("   已归档游戏列表")  
        print("=====================")  
  
        display_game_list(game_list, show_hidden, mode='archived')  
  
        print("\n---------------------")  
        toggle_hidden_text = "重新隐藏游戏" if show_hidden else "激活隐藏游戏"  
        print(f"a. {toggle_hidden_text} (全局)")  
        print()  
  
        choice = input("请选择操作 (直接回车返回): ").lower()  
  
        if not choice:  
            return show_hidden  # 返回当前的状态  
  
        if choice == 'a':  
            # 调用全局处理函数，并用其返回值更新当前状态  
            show_hidden = handle_toggle_hidden_games(show_hidden, folder_path, key)  
        else:  
            SystemLog.warn("无效的选择。")  
            input("按任意键继续...")  
  
def handle_toggle_hidden_games(show_hidden, folder_path, key):
    """  
    一个可复用的函数，专门处理激活或重新隐藏游戏的逻辑。  
    包含所有验证流程（Windows Hello, TOTP），并返回最新的显示状态。  
  
    返回:  
        bool: 最新的 show_hidden 状态。  
    """  
    if show_hidden:  
        # 如果已经是激活状态，则直接重新隐藏  
        SystemLog.info("隐藏游戏已重新隐藏！")  
        input("按任意键继续...")  
        return False  
    else:  
        # --- 激活逻辑 ---  
        # 尝试加载当前的 Windows Hello 选项状态  
        _, _, _, win_hello_enabled = load_safe_config(folder_path)  
        auth_success = False  
  
        if win_hello_enabled:  
            print("1. 使用 Windows Hello (推荐)")  
            print("2. 使用 TOTP 码")  
            auth_choice = input("请选择验证方式 (直接回车返回): ")  
  
            if auth_choice == "1":  
                auth_result = authenticate_with_windows_hello()  
                if auth_result == 'SUCCESS':  
                    auth_success = True  
                elif auth_result == 'CANCELED':  
                    SystemLog.warn("操作已取消，无法激活隐藏游戏。")  
                elif auth_result == 'NOT_AVAILABLE':  
                    SystemLog.warn("此设备上未设置 Windows Hello！无法激活隐藏游戏。")  
                else: # 'FAILED'  
                    SystemLog.warn("Windows Hello 验证失败，无法激活隐藏游戏。")  
            elif auth_choice == "2":  
                code = input(f"  {Color.GOLD}请输入TOTP码以激活隐藏游戏: {Color.RESET}").strip()  
                if not code: # 如果没有输入，视为取消  
                    SystemLog.warn("操作已取消，无法激活隐藏游戏。")  
                else:  
                    totp = pyotp.TOTP(key)  
                    SystemLog.step("正在验证TOTP码", "run")  
                    if totp.verify(code): # 验证TOTP码  
                        SystemLog.step("TOTP码验证", "done")  
                        auth_success = True  
                    else:  
                        SystemLog.step("TOTP码验证", "fail")  
                        SystemLog.warn("TOTP验证失败，无法激活隐藏游戏。")  
            elif not auth_choice:  
                # 用户直接回车，不做任何操作，仅为占位  
                pass  
            else:
                SystemLog.warn("无效的选择，无法激活隐藏游戏。")  
        else:  
            # Windows Hello 未启用，直接要求TOTP  
            code = input(f"  {Color.GOLD}请输入TOTP码以激活隐藏游戏: {Color.RESET}").strip()  
            if not code: # 如果没有输入，视为取消  
                SystemLog.warn("操作已取消，无法激活隐藏游戏。")  
            else:  
                totp = pyotp.TOTP(key)  
                SystemLog.step("正在验证TOTP码", "run")  
                if totp.verify(code): # 验证TOTP码  
                    SystemLog.step("TOTP码验证", "done")  
                    auth_success = True  
                else:  
                    SystemLog.step("TOTP码验证", "fail")  
                    SystemLog.warn("TOTP验证失败，无法激活隐藏游戏。")  
  
        # 根据最终的认证结果进行操作  
        if auth_success:  
            SystemLog.info("隐藏游戏已激活！")  
            input("按任意键继续...")  
            return True  
        else:  
            # 只有在有实际操作（非直接回车）但失败时才暂停  
            # 如果 auth_choice 存在 (即用户输入了内容) 或 win_hello_enabled 为 False (强制TOTP)  
            if (win_hello_enabled and auth_choice) or not win_hello_enabled:  
                input("按任意键继续...")  
            return False  
                
def start_game(game_path, game_list, show_hidden=False):
    """    
    启动单个游戏的函数，用于组合启动时多线程调用。    
    统一使用cmd /c start命令，实现彻底的进程分离，避免Godot引擎启动时在控制台输出信息导致程序挂起    
    """    
    # --- 严格检查隐藏状态 ---  
    if not show_hidden:    
        for game in game_list:    
            # 检查当前列表项是否与目标游戏路径匹配  
            if game[0] == game_path:  
                # 检查该游戏是否标记为隐藏，并且全局设置是隐藏的  
                if game[3] == "hidden":   
                    SystemLog.warn(f"该游戏为隐藏状态，无法在未激活时启动。")  
                    return    
                # 如果不是隐藏状态，或者全局设置是显示隐藏，则允许启动  
                break # 找到匹配项后，无需继续检查  
    
    try:    
        game_name = os.path.basename(game_path)  
        SystemLog.step(f"正在拉起游戏进程: {game_name}", "run")  
            
        # 使用绝对路径和引号确保路径正确    
        absolute_path = os.path.abspath(game_path)    
            
        # 定义终极进程分离标志    
        # DETACHED_PROCESS: 不继承父进程的控制台    
        # CREATE_NEW_PROCESS_GROUP: 创建新的进程组，使子进程不会收到发给父进程的信号    
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP    
            
        # 对于 .exe 游戏，显式将其工作目录设置为 .exe 所在目录，以确保游戏资源正确加载。    
        _cwd = None    
        if game_path.lower().endswith('.exe'):    
            _cwd = os.path.dirname(absolute_path)    
        # 对于 .lnk 快捷方式（以及其他非 .exe 文件），Windows 的 'start' 命令会根据快捷方式自身属性或系统默认行为处理其工作目录，因此此处无需额外指定 _cwd。    
            
        # 统一使用 cmd /c start 命令来启动所有游戏 (包括 .lnk, .exe 等)，但添加适当的延迟    
        subprocess.Popen(    
            f'cmd /c start "" "{absolute_path}"', # 统一启动命令    
            shell=True,                           # 必须为 True 才能执行 'cmd /c' 命令    
            stdout=subprocess.DEVNULL,            # 丢弃标准输出，解决Godot输出问题    
            stderr=subprocess.DEVNULL,            # 丢弃错误输出    
            creationflags=flags,                  # 应用强分离标志    
            cwd=_cwd                              # 为 cmd.exe 设置工作目录    
        )    
            
        # 添加微小延迟，避免组合启动时的多个启动命令过于密集造成冲突    
        time.sleep(0.1)  # 100毫秒延迟    
            
        SystemLog.step(f"游戏 {game_name} 启动指令发送", "done")  
            
    except Exception as e:    
        SystemLog.step(f"游戏 {game_name} 启动", "fail")  
        SystemLog.warn(f"启动游戏失败: {e}")  
        # 失败时回退到原始的os.startfile方法    
        try:    
            os.startfile(game_path)    
            SystemLog.info("尝试使用备用方法启动成功。")  
        except Exception as fallback_error:    
            SystemLog.warn(f"备用启动也失败: {fallback_error}")  
    
def menu():
    """    
    主菜单函数，负责展示游戏启动列表并允许用户执行相关操作。    
    此函数的主要功能包括：    
    1. 检查 TOTP 密钥，必要时生成并保存新的密钥。    
    2. 加载游戏列表并提供用户入口，选择启动游戏或进行管理操作。    
    3. 支持组合启动多个游戏，使用多线程实现并行启动。    
    4. 提供安全设置、游戏管理、关于信息等功能。    
    5. 崩溃日志功能。    
    6. 支持通过 Windows Hello 激活隐藏游戏。    
    
    用户可以通过输入序号启动单个游戏，或输入组合格式（如1+2+3）同时启动多个游戏。    
    如果输入无效，会提示用户重新输入。    
    """    
    # 设置退出处理器，在程序开始时就注册    
    setup_exit_handler()    
          
    folder_path = get_or_create_data_folder()  # 获取或创建数据文件夹    
    create_or_update_version_file(folder_path)  # 版本文件初始化    
          
    # 检查并创建配置文件 (MRNewGameLauncherSafeConfig.txt)    
    config_path = os.path.join(folder_path, "MRNewGameLauncherSafeConfig.txt")    
    if not os.path.exists(config_path):    
        key = generate_totp_key()    
        # 将生成的TOTP密钥保存到文件，并默认禁用Windows Hello选项    
        save_safe_config(key, "每次验证", None, False, folder_path=folder_path)    
        # 打印生成的TOTP密钥    
        SystemLog.info(f"TOTP密钥: {key}")  
        # 提示用户显示该密钥的QR码    
        SystemLog.info("TOTP密钥的QR码:")  
        display_qr_code(key) # 通过QR码展示密钥，方便用户扫描保存    
        SystemLog.info("请妥善保管您的TOTP密钥")  
        input("按任意键继续...")    
        os.system('cls' if os.name == 'nt' else 'clear') # 清屏    
      
    # 从存储中加载安全配置，包括TOTP数据和Windows Hello选项状态    
    key, frequency, last_verified, _ = load_safe_config(folder_path)    
    # 检查TOTP验证是否成功    
    if not verify_totp(key, frequency, last_verified):    
        # 如果验证失败，则结束当前函数执行    
        return # 通过verify_totp函数中已经处理过退出提示    
      
    game_list = load_game_list(folder_path)  # 加载完整的游戏列表    
    show_hidden = False  # 默认不显示隐藏游戏    
          
    while True:    
        game_list = load_game_list(folder_path)  # 每次循环都重新加载，确保数据最新  
        draw_header(game_list) # 调用新的Header，传入完整的游戏列表  
        
        # 顶部功能区  
        print(f"  {Color.BOLD}[ 000. 关于 ]   [ 00. 设置 ]   [ 0. 管理游戏 ]{Color.RESET}\n")  
        
        # 游戏列表  
        display_game_list(game_list, show_hidden, mode='active')  
        
        # 动态计算序号  
        active_games = [g for g in game_list if g[4] == 'active']  
        option_index = len(active_games) + 1  
        has_hidden_games = any(g[3] == "hidden" for g in active_games)  
        has_archived_games = any(g[4] == "archived" for g in game_list)  
  
        print(f"\n{Color.CYAN}  " + "─" * 50 + Color.RESET)  
        
        # 底部选项动态生成  
        footer_parts = []  
        toggle_hidden_idx = -1  
        if has_hidden_games:  
            toggle_text = "重新隐藏游戏" if show_hidden else "激活隐藏游戏"  
            footer_parts.append(f"{Color.PINK}{option_index}. {toggle_text}{Color.RESET}")  
            toggle_hidden_idx = option_index  
            option_index += 1  
          
        archive_idx = -1  
        if has_archived_games:  
            footer_parts.append(f"{Color.BLUE}{option_index}. 查看已归档游戏{Color.RESET}")  
            archive_idx = option_index  
            option_index += 1  
            
        exit_idx = option_index  
        footer_parts.append(f"{Color.RED}{exit_idx}. 退出{Color.RESET}")  
  
        # 打印操作行  
        # 这里优化了打印方式，使其在单行内更紧凑，并增加了间距  
        print("  " + "    ".join(footer_parts))  
        print() # 换行  
        
        choice = input(f"  {Color.GOLD}请输入序号以启动游戏或退出（支持组合启动，如1+2+3）: {Color.RESET}").strip()  
      
        if choice == "000":    
            show_about()  # 查看脚本信息    
        elif choice == "00":    
            show_settings_menu(folder_path)  # 进入设置菜单    
        elif choice == "0":    
            # 管理游戏时，传入完整的列表  
            manage_games(game_list, folder_path, show_hidden)  # 进入游戏管理菜单    
            game_list = load_game_list(folder_path) # 操作后必须重新加载完整列表  
        elif has_hidden_games and choice == str(toggle_hidden_idx):    
             show_hidden = handle_toggle_hidden_games(show_hidden, folder_path, key)  
        elif has_archived_games and choice == str(archive_idx):  
            show_hidden = show_archived_games(game_list, folder_path, show_hidden, key)  
            game_list = load_game_list(folder_path) # 从归档菜单返回后，重新加载列表  
        elif choice == str(exit_idx):    
            break  # 退出程序    
        elif '+' in choice:  # 只有当输入中包含 + 时，才会进入组合启动逻辑    
            if not re.match(r'^\d+(\+\d+)*$', choice):  # 检查格式是否正确    
                SystemLog.warn("组合启动的输入格式不正确，请重新输入。")  
                input("按任意键继续...")    
                continue    
                  
            game_indices = [int(i) for i in choice.split('+')]  
            errors = []  
            games_to_start = []      
                  
            for index in game_indices:      
                if not (1 <= index <= len(active_games)):      
                    errors.append(f"无效的游戏序号: {index}")      
                    continue      
                  
                game_data = active_games[index - 1]  
                game_path = game_data[0]  
                game_name = game_data[1]  
                game_version = game_data[2]  
                game_hidden = game_data[3]  
                      
                # --- 严格检查隐藏状态 ---  
                if game_hidden == "hidden" and not show_hidden:        
                    errors.append(f"序号 {index} (游戏 '{game_name}') 为隐藏游戏，无法在未激活时启动。")        
                    continue
                elif game_version == "未安装":        
                    errors.append(f"游戏 {game_name} 未安装，无法启动。")        
                    continue    
                elif game_version == "已通关":        
                    errors.append(f"游戏 {game_name} 已通关，无需再次启动。")        
                    continue    
                elif not os.path.exists(game_path):      
                    errors.append(f"游戏 {game_name} 路径错误或文件不存在: {game_path}")      
                    continue      
                games_to_start.append(game_path)      
                  
            if errors:      
                SystemLog.warn("以下错误导致无法组合启动游戏：")  
                for error in errors:      
                    print(f"- {error}")      
                input("按任意键继续...")      
                continue      
                  
            threads = []      
            for game_path in games_to_start:      
                thread = threading.Thread(target=start_game, args=(game_path, game_list, show_hidden))      
                thread.start()      
                threads.append(thread)      
            for thread in threads:      
                thread.join()      
            break      
        elif choice.isdigit() and 1 <= int(choice) <= len(active_games):      
            game_data = active_games[int(choice) - 1]  
            game_path = game_data[0]  
            game_name = game_data[1]  
            game_version = game_data[2]  
            game_hidden = game_data[3]  
                  
            # --- 严格检查隐藏状态 ---  
            if game_hidden == "hidden" and not show_hidden:        
                SystemLog.warn(f"该游戏为隐藏游戏，无法在未激活时启动。")  
                input("按任意键继续...")
            elif game_version == "未安装":        
                SystemLog.warn(f"游戏 {game_name} 未安装，无法启动。")  
                input("按任意键继续...")        
            elif game_version == "已通关":        
                SystemLog.warn(f"游戏 {game_name} 已通关，无需再次启动。")  
                input("按任意键继续...")    
            elif os.path.exists(game_path):      
                start_game(game_path, game_list, show_hidden)  # 启动所选游戏      
                break      
            else:      
                SystemLog.warn(f"路径错误或文件不存在: {game_path}")  
                input("按任意键返回目录...")      
        else:      
            SystemLog.warn("无效的选择，请重新输入。")  
            input("按任意键继续...")  
                
if __name__ == "__main__":    
    menu()  # 运行主菜单
