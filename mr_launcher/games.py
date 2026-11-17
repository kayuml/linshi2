

"""MR 新游戏启动器 v40.0 —— games 模块。"""

import msvcrt
import os
import subprocess
import time

from .security import handle_toggle_hidden_games
from .storage import save_game_list
from .ui import Color, SystemLog, align_right_v, display_game_list, get_v_width, pad_v

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
