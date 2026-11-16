

"""MR 新游戏启动器 v39.0 —— logging_sys 模块（由 MRNewGameLauncher39.0.py 模块化重构而来，逻辑保持不变）。"""

import datetime
import os
import sys
import traceback

import psutil

from .storage import get_or_create_data_folder

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
