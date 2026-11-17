

"""MR 新游戏启动器 v40.0 —— ui 模块。"""

import os
import re
import shutil
import unicodedata

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
