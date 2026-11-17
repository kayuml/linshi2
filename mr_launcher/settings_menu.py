

"""MR 新游戏启动器 v39.0 —— settings_menu 模块（由 MRNewGameLauncher39.0.py 模块化重构而来，逻辑保持不变）。"""

import datetime
import os

import pyotp

from .config import DATETIME_FORMAT
from .security import load_safe_config, save_safe_config
from .ui import Color, SystemLog
from .webdav import configure_webdav, manage_backups, perform_backup

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
                last_verified_dt = datetime.datetime.strptime(last_verified, DATETIME_FORMAT)    
                next_verification_dt = last_verified_dt + datetime.timedelta(hours=float(frequency))    
                next_verification_time = next_verification_dt.strftime(DATETIME_FORMAT)    
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
