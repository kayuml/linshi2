

"""MR 新游戏启动器 v39.0 —— main 模块。"""

import os
import re
import threading

from .about import show_about
from .config import SAFE_CONFIG_FILE_NAME
from .games import manage_games, show_archived_games, start_game
from .logging_sys import setup_exit_handler
from .security import display_qr_code, generate_totp_key, handle_toggle_hidden_games, load_safe_config, normalize_seed, save_safe_config, verify_totp
from .settings_menu import show_settings_menu
from .storage import create_or_update_version_file, get_or_create_data_folder, load_game_list
from .ui import Color, SystemLog, display_game_list, draw_header

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
    config_path = os.path.join(folder_path, SAFE_CONFIG_FILE_NAME)    
    if not os.path.exists(config_path):    
        key = generate_totp_key()    
        # 将生成的TOTP密钥保存到文件，并默认禁用Windows Hello选项    
        save_safe_config(key, "每次验证", None, False, folder_path=folder_path)    
        # 打印生成的TOTP密钥    
        SystemLog.info(f"TOTP密钥: {key}")  
        # 提示用户显示该密钥的QR码    
        SystemLog.info("TOTP密钥的QR码:")  
        display_qr_code(key) # 通过QR码展示密钥，方便用户扫描保存    
        SystemLog.warn("此密钥同时是备份解密密钥：未保存将无法在其他设备上恢复备份！")
        SystemLog.info("请复制并妥善保存上方密钥（建议离线保存），随后需回输一次以确认已保存。")
        while True:
            confirm = input(f"\n  {Color.GOLD}请输入上方显示的TOTP密钥以确认已保存（直接回车退出程序）: {Color.RESET}").strip()
            if not confirm:
                SystemLog.warn("未确认保存密钥，程序退出。请重新运行并保存密钥。")
                return
            if normalize_seed(confirm) == normalize_seed(key):
                SystemLog.success("密钥保存确认成功。")
                break
            SystemLog.warn("输入与显示的密钥不一致，请核对后重新输入。")
            SystemLog.info(f"TOTP密钥: {key}")  
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
