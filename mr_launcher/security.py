

"""MR 新游戏启动器 v39.0 —— security 模块（由 MRNewGameLauncher39.0.py 模块化重构而来，逻辑保持不变）。"""

import asyncio
import datetime
import os

from winrt.windows.security.credentials.ui import UserConsentVerificationResult
from winrt.windows.security.credentials.ui import UserConsentVerifier
from winrt.windows.security.credentials.ui import UserConsentVerifierAvailability
import pyotp
import qrcode

from .storage import get_or_create_data_folder, hide_file, unhide_file
from .ui import Color, SystemLog

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
