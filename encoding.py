import json
import base58

from solders.pubkey import Pubkey
from solders.keypair import Keypair
import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,            
        salt=salt,
        iterations=390000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

def encrypt_secret(secret_key: bytes, password: str) -> str:
    salt = os.urandom(16)         
    iv = os.urandom(16)         
    key = derive_key(password, salt)

    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(secret_key) + encryptor.finalize()

    data = salt + iv + ct
    return base64.b64encode(data).decode()

def decrypt_secret(encoded: str, password: str) -> bytes:
    raw = base64.b64decode(encoded)
    salt, iv, ct = raw[:16], raw[16:32], raw[32:]
    key = derive_key(password, salt)

    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    secret_key = decryptor.update(ct) + decryptor.finalize()
    return base58.b58encode(secret_key).decode()
