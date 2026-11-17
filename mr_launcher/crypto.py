"""MR 新游戏启动器 v40.0 —— crypto 模块。
v1（旧格式，仅用于恢复/迁移旧备份）：时间戳 + 固定盐 PBKDF2 派生密钥。
v2（新格式）：每备份随机 DEK，用 TOTP 种子经 HKDF 派生的 KEK 以 AES-GCM 包裹，头部字节作 AAD。
"""
import base64, json, os, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from .config import (AES_GCM_NONCE_LENGTH, AES_KEY_LENGTH, BACKUP_DEK_LENGTH, BACKUP_FORMAT_MAGIC,
    BACKUP_FORMAT_VERSION, BACKUP_KEK_INFO, BACKUP_KEK_KDF, BACKUP_KEK_SALT_LENGTH, FIXED_SALT, PBKDF2_ITERATIONS)

class BackupFormatError(ValueError):
    """密钥头部结构/版本/算法不合法（硬性错误，不应重试或回退）。"""

class BackupUnlockError(ValueError):
    """TOTP 种子不正确，或密钥头部已被篡改（GCM 校验失败）。"""

def derive_encryption_key(timestamp):
    """【v1 旧格式，仅用于恢复/迁移旧备份】时间戳+固定盐 PBKDF2，不具备实际保密强度。"""
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=AES_KEY_LENGTH, salt=FIXED_SALT, iterations=PBKDF2_ITERATIONS)
    return kdf.derive(timestamp.encode('utf-8'))

def encrypt_data(data, key):
    """AES-GCM 加密，返回 nonce+密文+认证标签。"""
    nonce = os.urandom(AES_GCM_NONCE_LENGTH)
    return nonce + AESGCM(key).encrypt(nonce, data, None)

def decrypt_data(encrypted_data, key):
    """AES-GCM 解密（前12字节为nonce）。"""
    nonce = encrypted_data[:AES_GCM_NONCE_LENGTH]; ciphertext = encrypted_data[AES_GCM_NONCE_LENGTH:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, None)
    except Exception as e:
        raise ValueError(f"解密失败，请检查并确保压缩包为原始文件名及其内容未被篡改: {e}")

def derive_kek_from_seed(seed, salt):
    """由（已规范化的）TOTP 种子派生包裹密钥 KEK（160位随机种子，HKDF 足够）。"""
    return HKDF(algorithm=hashes.SHA256(), length=AES_KEY_LENGTH, salt=salt, info=BACKUP_KEK_INFO).derive(seed.encode("utf-8"))

def generate_dek():
    """为单个备份生成独立随机 256 位数据密钥 DEK。"""
    return secrets.token_bytes(BACKUP_DEK_LENGTH)

def _header_aad(f):
    return json.dumps(f, sort_keys=True, separators=(",", ":")).encode("utf-8")

def build_key_header(dek, seed):
    """生成 v2 明文密钥头部：KDF 参数 + 随机盐 + 被 KEK 包裹的 DEK（头部作 AAD）。"""
    salt = secrets.token_bytes(BACKUP_KEK_SALT_LENGTH); kek = derive_kek_from_seed(seed, salt); nonce = os.urandom(AES_GCM_NONCE_LENGTH)
    fields = {"magic": BACKUP_FORMAT_MAGIC, "version": BACKUP_FORMAT_VERSION, "kdf": BACKUP_KEK_KDF,
              "salt": base64.b64encode(salt).decode("ascii"), "wrap_nonce": base64.b64encode(nonce).decode("ascii")}
    wrapped = AESGCM(kek).encrypt(nonce, dek, _header_aad(fields))
    header = dict(fields); header["wrapped_dek"] = base64.b64encode(wrapped).decode("ascii")
    return json.dumps(header, sort_keys=True, indent=2).encode("utf-8")

def unwrap_dek_from_header(header_bytes, seed):
    """解出 DEK。结构问题抛 BackupFormatError；种子错误/篡改抛 BackupUnlockError。"""
    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except Exception:
        raise BackupFormatError("密钥头部不是有效的 JSON")
    if not isinstance(header, dict): raise BackupFormatError("密钥头部结构不正确")
    if header.get("magic") != BACKUP_FORMAT_MAGIC: raise BackupFormatError("密钥头部格式标识不正确")
    if header.get("version") != BACKUP_FORMAT_VERSION: raise BackupFormatError(f"不支持的备份格式版本: {header.get('version')}")
    if header.get("kdf") != BACKUP_KEK_KDF: raise BackupFormatError(f"不支持的密钥派生算法: {header.get('kdf')}")
    if "wrapped_dek" not in header: raise BackupFormatError("密钥头部缺少被包裹的密钥")
    fields = {k: v for k, v in header.items() if k != "wrapped_dek"}
    try:
        salt = base64.b64decode(fields["salt"]); nonce = base64.b64decode(fields["wrap_nonce"]); wrapped = base64.b64decode(header["wrapped_dek"])
    except Exception:
        raise BackupFormatError("密钥头部字段编码不正确")
    if len(salt) != BACKUP_KEK_SALT_LENGTH or len(nonce) != AES_GCM_NONCE_LENGTH: raise BackupFormatError("密钥头部盐/nonce 长度不正确")
    kek = derive_kek_from_seed(seed, salt)
    try:
        return AESGCM(kek).decrypt(nonce, wrapped, _header_aad(fields))
    except Exception:
        raise BackupUnlockError("TOTP 密钥不正确，或密钥头部已被篡改")
