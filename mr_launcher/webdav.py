

"""MR 新游戏启动器 v40.0 —— webdav 模块。"""

import datetime
import getpass
import hashlib
import io
import os
import random
import re
import string
import time
import zipfile

from webdav3.client import Client
import pyotp

from .config import (
    BACKUP_DIR_NAME,
    BACKUP_FILE_PREFIX,
    BACKUP_FILE_SUFFIX,
    BACKUP_FILENAME_PATTERN,
    BACKUP_TIMESTAMP_FORMAT,
    CHECKSUM_FILE_NAME,
    DATA_FILE_ENCODING,
    ENCRYPTED_FILE_SUFFIX,
    GAME_LIST_FILE_NAME,
    MANIFEST_FILE_NAME,
    OBFUSCATED_NAME_LENGTH,
    SAFE_CONFIG_FILE_NAME,
    SENSITIVE_FILES,
    VERSION,
    VERSION_FILE_NAME,
    WEBDAV_CONFIG_FILE_NAME,
    WEBDAV_ENCODING,
    WEBDAV_MAX_ATTEMPTS,
    WEBDAV_RETRY_DELAY,
    BACKUP_KEY_HEADER_NAME,
    BACKUP_SEED_MAX_ATTEMPTS,
    MIGRATED_FILE_SUFFIX,
)
from .crypto import (BackupFormatError, BackupUnlockError, build_key_header, decrypt_data,
    derive_encryption_key, encrypt_data, generate_dek, unwrap_dek_from_header)
from .security import display_qr_code, load_safe_config, normalize_seed
from .storage import get_or_create_data_folder, hide_file, unhide_file
from .ui import Color, SystemLog

def configure_webdav(folder_path=None):
    """    
    配置 WebDAV 服务器信息，并将其保存到配置文件 'MRNewGameLauncherWebDAVConfig.txt' 中。    
    用户需要输入 WebDAV 服务器地址、用户名和密码，格式为：http(s)://|用户名|密码。    
    显示当前配置（密码用星号屏蔽），仅在输入新配置时测试连接。    
    特别注意：避免出现 PermissionError: [Errno 13] Permission denied 错误。    
    """    
    if folder_path is None:    
        folder_path = get_or_create_data_folder()    
        
    file_path = os.path.join(folder_path, WEBDAV_CONFIG_FILE_NAME)    
        
    # 检查并显示现有配置    
    has_config = False    
    if os.path.exists(file_path):    
        try:    
            # 明确指定 GB18030 编码读取配置    
            with open(file_path, "r", encoding=DATA_FILE_ENCODING) as file:    
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
            with open(file_path, "w", encoding=DATA_FILE_ENCODING) as file:    
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

def test_webdav_connection(url, username, password, max_attempts=WEBDAV_MAX_ATTEMPTS):
    """测试 WebDAV 连接是否成功，最多尝试3次"""    
    options = {    
        'webdav_hostname': url,    
        'webdav_login': username,    
        'webdav_password': password,    
        'webdav_encoding': WEBDAV_ENCODING # 增加 WebDAV 编码设置，确保文件名和路径正确处理  
    }    
        
    for attempt in range(1, max_attempts + 1):    
        try:    
            client = Client(options)    
            client.list() # 尝试列出目录，验证连接    
            return True    
        except Exception as e:    
            if attempt < max_attempts:    
                SystemLog.info(f"WebDAV 连接失败 (尝试 {attempt}/{max_attempts}): {e}")  
                time.sleep(WEBDAV_RETRY_DELAY) # 增加延迟，避免频繁重试  
            else:    
                SystemLog.warn(f"WebDAV 连接最终失败: {e}")  
        
    return False

def _get_webdav_client(folder_path, quiet=False):
    """读取 WebDAV 配置并初始化客户端；未配置或读取失败时返回 None。"""
    webdav_config_path = os.path.join(folder_path, WEBDAV_CONFIG_FILE_NAME)
    if not os.path.exists(webdav_config_path):
        if not quiet:
            SystemLog.warn("未配置 WebDAV 服务器，请先配置 WebDAV 服务器。"); input("按任意键继续...")
        return None
    try:
        with open(webdav_config_path, "r", encoding=DATA_FILE_ENCODING) as file:
            lines = file.readlines()
            webdav_url = lines[0].strip().replace("WebDAV URL: ", ""); username = lines[1].strip().replace("Username: ", ""); password = lines[2].strip().replace("Password: ", "")
    except Exception as e:
        if not quiet:
            SystemLog.warn(f"读取 WebDAV 配置时出错: {e}"); input("按任意键继续...")
        return None
    return Client({'webdav_hostname': webdav_url, 'webdav_login': username, 'webdav_password': password, 'webdav_encoding': WEBDAV_ENCODING})

def _acquire_backup_key(zip_file, filename, folder_path):
    """判定格式并取得解密密钥。返回 (key, version)；取消/无法解锁返回 (None, 0)。头部损坏硬性中止，绝不回退v1。"""
    if BACKUP_KEY_HEADER_NAME in zip_file.namelist():
        header_bytes = zip_file.read(BACKUP_KEY_HEADER_NAME)
        local_seed, _, _, _ = load_safe_config(folder_path)
        if local_seed:
            try:
                return unwrap_dek_from_header(header_bytes, normalize_seed(local_seed)), 2
            except BackupFormatError as e:
                SystemLog.warn(f"备份密钥头部损坏: {e}"); return None, 0
            except BackupUnlockError:
                pass
        SystemLog.info("本地TOTP密钥无法解开此备份，需要输入备份时使用的TOTP密钥。")
        attempts = BACKUP_SEED_MAX_ATTEMPTS
        while attempts > 0:
            seed = getpass.getpass(f"  {Color.GOLD}请输入备份时使用的TOTP密钥（直接回车取消）: {Color.RESET}").strip()
            if not seed:
                SystemLog.warn("已取消输入，无法解密该备份。"); return None, 0
            try:
                return unwrap_dek_from_header(header_bytes, normalize_seed(seed)), 2
            except BackupFormatError as e:
                SystemLog.warn(f"备份密钥头部损坏: {e}"); return None, 0
            except BackupUnlockError as e:
                attempts -= 1; SystemLog.warn(f"{e}（剩余 {attempts} 次机会）")
        SystemLog.warn("多次输入均不正确，无法解密该备份。"); return None, 0
    timestamp_match = re.search(BACKUP_FILENAME_PATTERN, filename)
    if not timestamp_match:
        SystemLog.warn("备份文件名格式不正确，无法提取时间戳进行解密。"); return None, 0
    SystemLog.warn("此为旧格式(v1)备份：密钥由文件名时间戳派生，加密强度极弱、等效明文。")
    return derive_encryption_key(timestamp_match.group(1)), 1

def _build_backup_zip(folder_path):
    """
    在内存中构建 v2 加密备份包（WebDAV 备份与本地备份共用同一打包逻辑）。
    返回 (zip_bytes, backup_filename)；缺少 TOTP 密钥或打包失败时返回 (None, None)。
    """
    local_seed, _, _, _ = load_safe_config(folder_path)
    if not local_seed:
        SystemLog.warn("未找到TOTP密钥，无法创建加密备份。请先运行主程序生成密钥。")
        return None, None
    timestamp = datetime.datetime.now().strftime(BACKUP_TIMESTAMP_FORMAT)
    backup_filename = f"{BACKUP_FILE_PREFIX}{timestamp}{BACKUP_FILE_SUFFIX}"
    encryption_key = generate_dek()
    key_header = build_key_header(encryption_key, normalize_seed(local_seed))
    manifest = {}
    checksum_dict = {}
    zip_buffer = io.BytesIO()
    try:
        SystemLog.step("正在打包敏感配置文件", "run")
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 写入 v2 明文密钥头部（不含种子信息；DEK 被种子派生的 KEK 包裹）
            zip_file.writestr(BACKUP_KEY_HEADER_NAME, key_header)
            for original_filename in SENSITIVE_FILES:
                file_path = os.path.join(folder_path, original_filename)
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding=DATA_FILE_ENCODING) as f:
                        content = f.read()
                    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=OBFUSCATED_NAME_LENGTH))
                    obfuscated_filename = random_str + ENCRYPTED_FILE_SUFFIX
                    manifest[obfuscated_filename] = original_filename
                    encrypted_data = encrypt_data(content.encode(DATA_FILE_ENCODING), encryption_key)
                    checksum_dict[obfuscated_filename] = hashlib.sha256(encrypted_data).hexdigest()
                    zip_file.writestr(obfuscated_filename, encrypted_data)
            manifest_bytes = "\n".join(f"{obf} → {orig}" for obf, orig in manifest.items()).encode(DATA_FILE_ENCODING)
            encrypted_manifest = encrypt_data(manifest_bytes, encryption_key)
            checksum_dict[MANIFEST_FILE_NAME] = hashlib.sha256(encrypted_manifest).hexdigest()
            zip_file.writestr(MANIFEST_FILE_NAME, encrypted_manifest)
            checksum_bytes = "\n".join(f"{fn}:{hv}" for fn, hv in checksum_dict.items()).encode(DATA_FILE_ENCODING)
            zip_file.writestr(CHECKSUM_FILE_NAME, encrypt_data(checksum_bytes, encryption_key))
        SystemLog.step("配置文件打包加密", "done")
        return zip_buffer.getvalue(), backup_filename
    except Exception as e:
        SystemLog.step("配置文件打包加密", "fail")
        SystemLog.warn(f"打包备份时出错: {e}")
        return None, None
    finally:
        zip_buffer.close()

def perform_backup(folder_path=None):
    """
    执行云端备份：构建 v2 加密包并上传到 WebDAV 服务器。
    加密采用 v2：每备份随机 DEK，由本地 TOTP 种子经 HKDF 派生的 KEK 包裹后写入明文头部 keyfile.json。
    """
    if folder_path is None:
        folder_path = get_or_create_data_folder()
    client = _get_webdav_client(folder_path)
    if client is None:
        return
    zip_bytes, backup_filename = _build_backup_zip(folder_path)
    if zip_bytes is None:
        input("按任意键继续...")
        return
    SystemLog.step("正在上传备份文件到 WebDAV 服务器", "run")
    try:
        backup_dir = BACKUP_DIR_NAME
        if not client.check(backup_dir):
            client.mkdir(backup_dir)
        client.upload_to(buff=io.BytesIO(zip_bytes), remote_path=f"{backup_dir}/{backup_filename}")
        SystemLog.step("备份文件上传", "done")
        SystemLog.info(f"备份成功：{backup_filename}")
    except Exception as e:
        SystemLog.step("备份文件上传", "fail")
        SystemLog.warn(f"上传备份文件时出错或无法连接服务器: {e}")
    input("按任意键继续...")

def perform_local_backup(folder_path=None):
    """
    执行本地备份：构建与云端备份完全相同的 v2 加密包，直接保存到数据目录（MRNewGameLauncherData）内。
    无需配置 WebDAV，可离线使用；压缩包不设置隐藏属性，便于自行复制到其他位置保管。
    可在"管理备份"中直接选择本地备份进行恢复/删除。
    """
    if folder_path is None:
        folder_path = get_or_create_data_folder()
    zip_bytes, backup_filename = _build_backup_zip(folder_path)
    if zip_bytes is None:
        input("按任意键继续...")
        return
    local_path = os.path.join(folder_path, backup_filename)
    try:
        with open(local_path, "wb") as f:
            f.write(zip_bytes)
        SystemLog.info(f"本地备份成功：{local_path}")
        SystemLog.info("该压缩包与云端备份格式一致（v2加密），可复制到其他位置保管。")
    except PermissionError:
        SystemLog.warn("权限不足，无法写入本地备份。请检查文件夹写入权限或尝试以管理员身份运行。")
    except Exception as e:
        SystemLog.warn(f"写入本地备份时出错: {e}")
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
    required_files = [MANIFEST_FILE_NAME, CHECKSUM_FILE_NAME]    
        
    # 检查备份文件中是否包含所有必需的文件    
    for f in required_files:    
        if f not in zip_file.namelist():    
            # 如果缺少必要文件，返回验证失败和错误信息    
            if f == MANIFEST_FILE_NAME:    
                return False, "缺少必要的映射表文件"    
            elif f == CHECKSUM_FILE_NAME:    
                return False, "缺少必要的校验文件"    
    
    try:    
        # 1. 首先解密校验文件    
        # 读取加密的校验文件 checksum.sha256 的内容    
        encrypted_checksum = zip_file.read(CHECKSUM_FILE_NAME)    
            
        # 解密校验文件    
        try:    
            checksum_bytes = decrypt_data(encrypted_checksum, encryption_key)    
        except ValueError as e:    
            # 直接返回解密失败的原始错误信息，避免重复包装    
            return False, str(e)    
                
        checksum_content = checksum_bytes.decode(DATA_FILE_ENCODING)    
            
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
            if filename == CHECKSUM_FILE_NAME or filename == BACKUP_KEY_HEADER_NAME:    
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

def restore_backup(client, folder_path, backup_file, restore_gamelist=False, restore_safe_config=False, zip_data=None, local_path=None):  
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
        # 第一阶段：备份包数据由调用方（管理备份）预读后传入
        if zip_data is None:
            SystemLog.warn("缺少备份包数据，无法继续")
            input("按任意键继续...")
            return
        source_tag = "本地" if local_path is not None else "云端"
        SystemLog.info(f"来源：{source_tag}备份包（已由调用方预读）")
        zip_buffer = io.BytesIO(zip_data)

                
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:        
            # 1. 判定格式并取得解密密钥（v2 种子包裹 / v1 时间戳兼容）
            SystemLog.step("正在解析备份元数据", "run")
            filename = os.path.basename(backup_file)
            encryption_key, fmt_version = _acquire_backup_key(zip_file, filename, folder_path)
            if encryption_key is None:
                SystemLog.step("备份元数据解析", "fail")
                input("按任意键继续...")
                return
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
                        if local_path is not None:
                            os.remove(local_path)
                        else:
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
            decrypted_files = decrypt_all_files(zip_file, encryption_key, exclude_files=[CHECKSUM_FILE_NAME, BACKUP_KEY_HEADER_NAME])        
            if decrypted_files is None:        
                SystemLog.step("配置文件数据解密", "fail")    
                SystemLog.warn("解密文件失败，无法继续恢复操作。")    
                input("按任意键继续...")        
                return        
            SystemLog.step("配置文件数据解密", "done")    
                        
            # 4. 解析映射表，按照映射表还原原始文件名        
            SystemLog.step("正在解析文件映射关系", "run")    
            try:        
                manifest_bytes = decrypted_files[MANIFEST_FILE_NAME]        
                manifest_content = manifest_bytes.decode(DATA_FILE_ENCODING)        
                            
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
                if orig == VERSION_FILE_NAME:        
                    version_file_obf = obf        
                    break        
                                
            backup_version = None        
            if version_file_obf and version_file_obf in decrypted_files:        
                try:        
                    version_bytes = decrypted_files[version_file_obf]        
                    version_content = version_bytes.decode(VERSION_FILE_ENCODING)        
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
                    if orig == SAFE_CONFIG_FILE_NAME:      
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
                    backup_safe_config_data = safe_config_bytes.decode(DATA_FILE_ENCODING)        
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
                SystemLog.step(f"正在还原游戏列表 ({GAME_LIST_FILE_NAME})", "run")    
                # 查找游戏列表文件        
                gamelist_file_obf = None        
                for obf, orig in manifest_dict.items():        
                    if orig == GAME_LIST_FILE_NAME:        
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
                    game_list_data = gamelist_bytes.decode(DATA_FILE_ENCODING)        
                except Exception as e:        
                    SystemLog.step("游戏列表还原", "fail")    
                    SystemLog.warn(f"解析游戏列表失败: {e}")    
                    input("按任意键继续...")        
                    return        
                                
                # 确保文件可写        
                game_list_path = os.path.join(folder_path, GAME_LIST_FILE_NAME)        
                if os.path.exists(game_list_path):        
                    unhide_file(game_list_path)  # 取消隐藏属性        
                                
                # 写入游戏列表文件        
                try:        
                    with open(game_list_path, "w", encoding=DATA_FILE_ENCODING) as file: # 明确指定 GB18030 编码写入      
                        file.write(game_list_data)        
                finally:        
                    hide_file(game_list_path)  # 写入完成后重新隐藏文件        
                SystemLog.step("游戏列表数据还原", "done")    
                            
            # 8. 恢复安全配置数据（如果需要）      
            if restore_safe_config:      
                SystemLog.step(f"正在还原安全配置 ({SAFE_CONFIG_FILE_NAME})", "run")    
                safe_config_path = os.path.join(folder_path, SAFE_CONFIG_FILE_NAME)      
                if os.path.exists(safe_config_path):        
                    unhide_file(safe_config_path)  # 取消隐藏属性        
                                
                # 写入安全配置数据文件      
                try:        
                    with open(safe_config_path, "w", encoding=DATA_FILE_ENCODING) as file: # 明确指定 GB18030 编码写入      
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
                            
            # v1 备份恢复成功后，询问是否原地升级为 v2（覆盖原包）
            if fmt_version == 1:
                up = input(f"\n  {Color.GOLD}是否将当前加密格式为v1版本的压缩包升级至 v2（现有的会被自动覆盖替换）？(y/n): {Color.RESET}").lower()
                if up == 'y':
                    _upgrade_backup_in_place(client, folder_path, backup_file, decrypted_files, manifest_dict, local_path)
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
    管理备份文件（云端 + 本地），包括列出、恢复、删除。
    本地备份来自数据目录内的 backup_*.zip；云端备份来自 WebDAV（未配置时仅显示本地）。
    v1 包在恢复成功后会询问是否原地升级为 v2。
    """
    if folder_path is None:
        folder_path = get_or_create_data_folder()
    client = _get_webdav_client(folder_path, quiet=True)
    entries = []
    try:
        for f in os.listdir(folder_path):
            if f.startswith(BACKUP_FILE_PREFIX) and f.endswith(BACKUP_FILE_SUFFIX):
                entries.append({"source": "local", "name": f, "path": os.path.join(folder_path, f)})
    except Exception as e:
        SystemLog.warn(f"读取本地备份列表时出错: {e}")
    if client is not None:
        try:
            SystemLog.step("正在检查 WebDAV 远程状态", "run")
            if client.check(BACKUP_DIR_NAME):
                remote_files = [f for f in client.list(BACKUP_DIR_NAME) if f.endswith(BACKUP_FILE_SUFFIX)]
                for f in remote_files:
                    entries.append({"source": "remote", "name": f, "path": f"{BACKUP_DIR_NAME}/{f}"})
                SystemLog.step("远程列表获取", "done")
            else:
                SystemLog.step("检查远程状态", "done")
                SystemLog.info("云端备份目录不存在（尚未创建云端备份）。")
        except Exception as e:
            SystemLog.step("远程访问失败", "fail")
            SystemLog.warn(f"无法连接 WebDAV，仅显示本地备份: {e}")
    else:
        SystemLog.info("未配置 WebDAV，仅显示本地备份。")
    entries.sort(key=lambda e: e["name"], reverse=True)
    if not entries:
        SystemLog.info("没有可用的备份文件。")
        input("按任意键继续...")
        return
    print("备份文件列表：")
    for i, e in enumerate(entries, start=1):
        tag = f"{Color.CYAN}[本地]{Color.RESET}" if e["source"] == "local" else f"{Color.BLUE}[云端]{Color.RESET}"
        print(f"{i}. {tag} {e['name']}")
    choice = input("请输入要操作的备份文件序号（直接回车返回）：")
    if not choice:
        return
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(entries):
        SystemLog.warn("无效的选择，请重新输入。")
        input("按任意键继续...")
        return
    sel = entries[int(choice) - 1]
    is_local = sel["source"] == "local"
    SystemLog.step("正在读取备份包以识别格式", "run")
    try:
        if is_local:
            with open(sel["path"], "rb") as f:
                zip_data = f.read()
        else:
            detect_buffer = io.BytesIO()
            client.download_from(buff=detect_buffer, remote_path=sel["path"])
            zip_data = detect_buffer.getvalue()
            detect_buffer.close()
    except Exception as e:
        SystemLog.step("备份包读取", "fail")
        SystemLog.warn(f"读取备份文件时出错: {e}")
        input("按任意键继续...")
        return
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zf:
            is_v2 = BACKUP_KEY_HEADER_NAME in zf.namelist()
        SystemLog.step("备份包格式识别", "done")
    except Exception as e:
        SystemLog.step("备份包格式识别", "fail")
        SystemLog.warn(f"无法读取备份包（可能已损坏）: {e}")
        input("按任意键继续...")
        return
    format_tag = f"{Color.GREEN}[v2]{Color.RESET}" if is_v2 else f"{Color.RED}[v1]{Color.RESET}"
    print(f"\n已选择: [{'本地' if is_local else '云端'}] {sel['name']} {format_tag}")
    print("1. 恢复游戏列表")
    print("2. 恢复安全配置")
    print("3. 全部恢复")
    print("4. 删除备份")
    operation = input("请选择操作（直接回车返回）：")
    if not operation:
        return
    local_path = sel["path"] if is_local else None
    if operation == "1":
        restore_backup(client, folder_path, sel["path"], restore_gamelist=True, restore_safe_config=False, zip_data=zip_data, local_path=local_path)
    elif operation == "2":
        restore_backup(client, folder_path, sel["path"], restore_gamelist=False, restore_safe_config=True, zip_data=zip_data, local_path=local_path)
    elif operation == "3":
        restore_backup(client, folder_path, sel["path"], restore_gamelist=True, restore_safe_config=True, zip_data=zip_data, local_path=local_path)
    elif operation == "4":
        try:
            SystemLog.step(f"正在删除备份文件: {sel['name']}", "run")
            if is_local:
                os.remove(sel["path"])
            else:
                client.clean(sel["path"])
            SystemLog.step("备份文件删除", "done")
            SystemLog.info(f"备份文件 {sel['name']} 已删除。")
        except Exception as e:
            SystemLog.step("备份文件删除", "fail")
            SystemLog.warn(f"删除备份文件时出错: {e}")
        input("按任意键继续...")
    else:
        SystemLog.warn("无效的选择，请重新输入。")
        input("按任意键继续...")


def _upgrade_backup_in_place(client, folder_path, backup_file, decrypted_files, manifest_dict, local_path=None):
    """将已解密的 v1 备份内容以 v2 重新加密并原地覆盖（本地写回原文件 / 云端覆盖原远程路径）。
    先自校验再覆盖，失败时原包保持不变。"""
    local_seed, _, _, _ = load_safe_config(folder_path)
    if not local_seed:
        SystemLog.warn("未找到本地TOTP密钥，无法升级。"); return
    seed = normalize_seed(local_seed); dek = generate_dek(); key_header = build_key_header(dek, seed)
    new_buffer = io.BytesIO(); new_manifest = {}; new_checksum = {}
    with zipfile.ZipFile(new_buffer, 'w', zipfile.ZIP_DEFLATED) as nz:
        nz.writestr(BACKUP_KEY_HEADER_NAME, key_header)
        for obf, orig in manifest_dict.items():
            if obf not in decrypted_files: continue
            enc = encrypt_data(decrypted_files[obf], dek)
            new_obf = ''.join(random.choices(string.ascii_letters + string.digits, k=OBFUSCATED_NAME_LENGTH)) + ENCRYPTED_FILE_SUFFIX
            nz.writestr(new_obf, enc); new_manifest[new_obf] = orig; new_checksum[new_obf] = hashlib.sha256(enc).hexdigest()
        enc_manifest = encrypt_data("\n".join(f"{o} → {g}" for o, g in new_manifest.items()).encode(DATA_FILE_ENCODING), dek)
        new_checksum[MANIFEST_FILE_NAME] = hashlib.sha256(enc_manifest).hexdigest(); nz.writestr(MANIFEST_FILE_NAME, enc_manifest)
        nz.writestr(CHECKSUM_FILE_NAME, encrypt_data("\n".join(f"{f}:{h}" for f, h in new_checksum.items()).encode(DATA_FILE_ENCODING), dek))
    new_buffer.seek(0)
    with zipfile.ZipFile(new_buffer, 'r') as nz:
        ok, reason = verify_backup_integrity(nz, dek)
        if not ok:
            SystemLog.warn(f"升级自校验失败，已中止（原包未改动）: {reason}"); return
        try:
            unwrap_dek_from_header(nz.read(BACKUP_KEY_HEADER_NAME), seed)
        except (BackupFormatError, BackupUnlockError) as e:
            SystemLog.warn(f"升级自校验失败，已中止（原包未改动）: {e}"); return
    data = new_buffer.getvalue(); new_buffer.close()
    try:
        if local_path is not None:
            with open(local_path, "wb") as f:
                f.write(data)
            SystemLog.info(f"已原地升级为v2：{local_path}")
        else:
            client.upload_to(buff=io.BytesIO(data), remote_path=backup_file)
            SystemLog.info(f"已原地升级为v2：{backup_file}")
    except Exception as e:
        SystemLog.warn(f"覆盖写入升级包时出错: {e}")
