

"""MR 新游戏启动器 v39.0 —— storage 模块（由 MRNewGameLauncher39.0.py 模块化重构而来，逻辑保持不变）。"""

import ctypes
import os
import shutil

import win32api
import win32file

from .config import (
    DATA_FILE_ENCODING,
    DATA_FOLDER_NAME,
    FILE_ATTRIBUTE_HIDDEN,
    FILE_ATTRIBUTE_NORMAL,
    GAME_LIST_FILE_NAME,
    VERSION,
    VERSION_FILE_NAME,
)

def create_or_update_version_file(folder_path):
    """    
    创建/更新版本文件    
    """    
    version_file = os.path.join(folder_path, VERSION_FILE_NAME)    
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
    folder_path = os.path.join(drive, DATA_FOLDER_NAME)    
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
        folder_path = os.path.join(drive, DATA_FOLDER_NAME)    
        if os.path.exists(folder_path):    
            existing_folders.append(folder_path)    
        
    if len(existing_folders) == 1:    
        return existing_folders[0]    
    elif len(existing_folders) > 1:    
        print(f"发现多个 {DATA_FOLDER_NAME} 文件夹，请选择一个:")    
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
        
    file_path = os.path.join(folder_path, GAME_LIST_FILE_NAME)    
        
    if os.path.exists(file_path):  # 检查游戏列表文件是否存在    
        # 使用 GB18030 编码读取文件，以支持特殊字符并与备份功能保持一致  
        with open(file_path, "r", encoding=DATA_FILE_ENCODING) as file:  
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
        
    file_path = os.path.join(folder_path, GAME_LIST_FILE_NAME)    
        
    if os.path.exists(file_path):    
        unhide_file(file_path)  # 确保文件是可见的    
    # 使用 GB18030 编码写入文件，以支持特殊字符并与备份功能保持一致  
    with open(file_path, "w", encoding=DATA_FILE_ENCODING) as file:  
        # 将每个游戏的信息以'|'连接并写入文件    
        for game in game_list:    
            file.write('|'.join(game) + "\n")    
    hide_file(file_path)  # 保存后隐藏文件

def hide_file(filepath):
    """    
    将指定文件设置为隐藏属性（Windows系统）。    
    """    
    if os.name == 'nt':  # 检查是否为Windows操作系统    
        ctypes.windll.kernel32.SetFileAttributesW(filepath, FILE_ATTRIBUTE_HIDDEN)

def unhide_file(filepath):
    if os.name == 'nt':  # 检查是否为Windows操作系统    
        ctypes.windll.kernel32.SetFileAttributesW(filepath, FILE_ATTRIBUTE_NORMAL)
