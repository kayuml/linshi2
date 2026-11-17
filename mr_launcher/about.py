

"""MR 新游戏启动器 v39.0 —— about 模块。"""

import os

from .config import AUTHOR, BLOG, CHANGELOG, VERSION
from .ui import print_changelog_entry

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
