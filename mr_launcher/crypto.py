

"""MR 新游戏启动器 v39.0 —— crypto 模块（由 MRNewGameLauncher39.0.py 模块化重构而来，逻辑保持不变）。"""

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from .config import AES_GCM_NONCE_LENGTH, AES_KEY_LENGTH, FIXED_SALT, PBKDF2_ITERATIONS

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
        length=AES_KEY_LENGTH,  # 256位密钥    
        salt=FIXED_SALT,    
        iterations=PBKDF2_ITERATIONS,  # 迭代次数    
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
    nonce = os.urandom(AES_GCM_NONCE_LENGTH)    
        
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
    nonce = encrypted_data[:AES_GCM_NONCE_LENGTH]    
        
    # 提取密文（剩余部分）    
    ciphertext = encrypted_data[AES_GCM_NONCE_LENGTH:]    
        
    # 解密数据    
    try:    
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)    
        return plaintext    
    except Exception as e:    
        # 捕获并重新抛出更具体的解密失败信息，方便调试    
        raise ValueError(f"解密失败，请检查并确保压缩包为原始文件名及其内容未被篡改: {e}")
