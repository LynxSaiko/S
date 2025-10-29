"""
Directory Bruteforce - Find hidden files and directories on Web Servers (General Focus)
"""
import sys
import requests
import threading
import time
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Tuple, Any, Optional # <-- BARIS INI DIPERBAIKI!

# The MODULE_INFO and OPTIONS dictionaries remain the same for framework compatibility.
MODULE_INFO = {
    "description": "Directory and file bruteforce on web servers with optional smart CMS detection"
}

OPTIONS = {
    "url": {
        "type": "str",
        "description": "Target URL (http:// or https://)",
        "required": True,
        "default": "http://example.com"
    },
    "wordlist": {
        "type": "str",
        "description": "Path to wordlist file or built-in list (common, large, or file path)",
        "required": False,
        "default": "common"
    },
    "extensions": {
        "type": "str",
        "description": "File extensions to try (comma-separated)",
        "required": False,
        "default": "php,html,txt,js,css,bak"
    },
    "threads": {
        "type": "int",
        "description": "Number of threads",
        "required": False,
        "default": 20
    },
    "timeout": {
        "type": "int",
        "description": "Request timeout in seconds",
        "required": False,
        "default": 5
    },
    "user_agent": {
        "type": "str",
        "description": "Custom User-Agent",
        "required": False,
        "default": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
}

import requests
import threading
import time
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Tuple, Any

# --- CMS Detection and Wordlists (Kept for smart bruteforce capability) ---

# [CMS detection and CMS-specific wordlist functions are kept identical 
# as they provide the 'smart' part of the module's description and act as an excellent general list fallback.]

def detect_cms(target_url, timeout=5):
    """Automatically detect if target uses a CMS with high confidence"""
    # ... (function content remains the same as in the original code)
    print("[*] Auto-detecting CMS...")
    
    cms_indicators = {
        'wordpress': [
            r'wp-content', r'wp-includes', r'wordpress', r'wp-json', r'wp-admin', r'wp-config',
            r'<link[^>]*wp-content', r'<script[^>]*wp-includes', r'<meta[^>]*generator[^>]*wordpress',
            'wp-login.php', 'xmlrpc.php'
        ],
        'joomla': [
            r'joomla', r'media/jui', r'templates/system', r'components/com_', r'modules/mod_',
            r'<meta[^>]*generator[^>]*joomla', r'<link[^>]*templates/system',
            'administrator', 'components', 'modules'
        ],
        'drupal': [
            r'drupal', r'sites/all', r'core/assets', r'misc/drupal', r'modules/node',
            r'<meta[^>]*generator[^>]*drupal', r'<link[^>]*sites/default',
            'sites/default', 'update.php', 'install.php'
        ],
        'magento': [
            r'magento', r'static/frontend', r'media/wysiwyg', r'js/mage', r'skin/frontend',
            r'<meta[^>]*generator[^>]*magento', r'<script[^>]*mage/',
            'admin', 'var/', 'media/'
        ]
    }
    
    try:
        response = requests.get(target_url, timeout=timeout, allow_redirects=True)
        content = response.text.lower()
        headers = response.headers
        
        confidence_scores = {}
        
        # Check content
        for cms, indicators in cms_indicators.items():
            score = 0
            for indicator in indicators:
                if re.search(indicator, content, re.IGNORECASE):
                    score += 1
            if score > 0:
                confidence_scores[cms] = score
        
        # Check headers
        server_header = headers.get('server', '').lower()
        x_powered_by = headers.get('x-powered-by', '').lower()
        x_generator = headers.get('x-generator', '').lower()
        
        for cms in cms_indicators.keys():
            if cms in server_header or cms in x_powered_by or cms in x_generator:
                confidence_scores[cms] = confidence_scores.get(cms, 0) + 2
        
        # Check common CMS paths with direct requests (Reduced for brevity and speed)
        cms_test_paths = {
            'wordpress': ['wp-admin/', 'wp-content/'],
            'joomla': ['administrator/', 'components/'],
            'drupal': ['sites/default/', 'modules/'],
            'magento': ['admin/', 'media/']
        }
        
        for cms, paths in cms_test_paths.items():
            for path in paths:
                try:
                    test_url = urljoin(target_url, path)
                    test_resp = requests.get(test_url, timeout=2, allow_redirects=False)
                    if test_resp.status_code in [200, 301, 302, 403, 401]:
                        confidence_scores[cms] = confidence_scores.get(cms, 0) + 1
                        break
                except:
                    continue
        
        # Determine the CMS with highest confidence
        if confidence_scores:
            detected_cms = max(confidence_scores.items(), key=lambda x: x[1])
            cms_name, confidence = detected_cms
            
            if confidence >= 2:
                print(f"[+] CMS Detected: {cms_name.upper()} (confidence: {confidence}/5)")
                return cms_name
            else:
                print(f"[-] Low confidence CMS detection: {cms_name} (confidence: {confidence}/5)")
                print("[*] Using general wordlist")
                return "general"
        else:
            print("[-] No CMS detected - Using general wordlist")
            return "general"
            
    except Exception as e:
        print(f"[-] CMS detection failed: {e}")
        print("[*] Using general wordlist as fallback")
        return "general"


def get_cms_specific_wordlist(cms_type):
    """Get wordlist specific to detected CMS"""
    # ... (function content remains the same as in the original code)
    if cms_type == "wordpress":
        return [
            "wp-admin", "wp-content", "wp-includes", "wp-json", "wp-login.php",
            "wp-config.php", "xmlrpc.php", "wp-cron.php", "wp-load.php",
            "wp-content/uploads/", "wp-content/plugins/", "wp-content/themes/",
            "readme.html", ".htaccess"
        ]
    elif cms_type == "joomla":
        return [
            "administrator", "components", "modules", "plugins", "templates",
            "configuration.php", "web.config.txt", "htaccess.txt",
            "administrator/index.php", "components/com_content/", "images/", "media/"
        ]
    elif cms_type == "drupal":
        return [
            "sites", "modules", "themes", "profiles", "misc",
            "sites/default/settings.php", "sites/default/files/", "sites/all/modules/",
            "update.php", "install.php", "cron.php", ".htaccess"
        ]
    elif cms_type == "magento":
        return [
            "admin", "admin/dashboard/", "var/", "media/", "skin/", "app/", "lib/",
            "var/backups/", "var/log/", "app/etc/local.xml", ".htaccess"
        ]
    else:
        return get_general_wordlist()


def get_general_wordlist():
    """Comprehensive wordlist for general websites (non-CMS)"""
    return [
        # Administrative paths
        "admin", "administrator", "login", "panel", "dashboard", "cp",
        "manager", "backend", "secure", "private", "hidden", "secret",
        
        # Common directories
        "images", "css", "js", "assets", "static", "uploads", "files", "storage",
        "backup", "backups", "old", "temp", "tmp", "cache", "log", "logs",
        "db", "database", "data", "config", "configuration", "setup",
        
        # Common files
        "robots.txt", "sitemap.xml", ".htaccess", ".htpasswd", ".git", ".svn", ".env",
        "readme.txt", "license.txt", "backup.zip", "dump.sql",
        "test.php", "info.php", "phpinfo.php",
        
        # API endpoints
        "api", "api/v1", "graphql", "rest",
        
        # Development
        "dev", "development", "staging", "test", "testing", "demo",
        
        # Index/Root files (already handled by extensions, but good to include)
        "index", "main", "default", "home"
    ]


def load_wordlist(wordlist_param: str, cms_type: str = "general") -> List[str]:
    """Load wordlist from file or use appropriate built-in wordlist"""
    
    print(f"[*] Loading wordlist: {wordlist_param}")
    
    # 1. Check if the wordlist_param is a file path
    if os.path.isfile(wordlist_param):
        try:
            with open(wordlist_param, 'r', encoding='utf-8', errors='ignore') as f:
                words = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            print(f"[+] Loaded {len(words)} words from file: {wordlist_param}")
            return words
        except Exception as e:
            print(f"[!] Error loading wordlist from file: {e}")
            # Fallback to general
            wordlist_param = "common" 
            cms_type = "general" # Force general fallback if file fails
    
    # 2. Handle built-in wordlists ('common', 'large')
    if wordlist_param == "large":
        base_list = get_general_wordlist() # Force general base for the 'large' built-in
        
        # Generate variations for a "large" list
        final_list = list(set([
            item for word in base_list for item in [
                word, word.upper(), word.capitalize(), f"{word}1", f"{word}_bak", f"old_{word}"
            ]
        ]))
        
        print(f"[+] Using large GENERAL wordlist: {len(final_list)} words")
        return final_list
        
    elif wordlist_param == "common":
        # Even if CMS detected, we default to the general list if the user explicitly set 'common'
        # unless we prioritize CMS specificity for a "smart" scan. Here, we prioritize the user's explicit 'common'.
        wordlist = get_general_wordlist()
        print(f"[+] Using common GENERAL wordlist: {len(wordlist)} words")
        return wordlist
    
    # 3. Default fallback (should not be reached if 'common' is default)
    wordlist = get_general_wordlist()
    print(f"[+] Using default GENERAL wordlist: {len(wordlist)} words")
    return wordlist


class DirectoryBruteforcer:
    def __init__(self, base_url: str, timeout: int = 5, user_agent: str = None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.user_agent = user_agent
        self.found_paths = []
        self.session = requests.Session()
        
        headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(headers)
        self.session.max_redirects = 0
        
    def check_path(self, path: str) -> Optional[Tuple[str, int, int, str]]:
        """Check if a path exists on the target"""
        url = urljoin(self.base_url + '/', path.lstrip('/')) # Ensure proper joining
        
        try:
            response = self.session.get(url, timeout=self.timeout, allow_redirects=False)
            
            # Interesting status codes
            if response.status_code in [200, 403, 301, 302, 401, 500]:
                size = len(response.content) if response.content else 0
                message = "OK"
                if response.status_code == 403: message = "Forbidden"
                elif response.status_code == 301 or response.status_code == 302:
                    message = f"Redirect → {response.headers.get('Location', '?')}"
                elif response.status_code == 401: message = "Unauthorized"
                elif response.status_code == 500: message = "Server Error"
                
                return path, response.status_code, size, message
            
            return None # Skip all other status codes (e.g., 404)
        
        except requests.exceptions.RequestException:
            return None
        except Exception:
            return None


def generate_paths(base_words: List[str], extensions: str) -> List[str]:
    """Generate paths with extensions - REMOVED limits for full wordlist usage"""
    paths = set()
    extensions_list = [ext.strip().lstrip('.') for ext in extensions.split(',') if ext.strip()]
    
    for word in base_words:
        word = word.strip('/') # Clean trailing/leading slash for proper path generation
        if not word: continue

        # 1. Add as directory (always check with trailing slash)
        paths.add(word + "/")
        
        # 2. Add as file with extensions
        for ext in extensions_list:
            if not word.endswith('.' + ext): # Avoid creating path.ext.ext
                paths.add(word + "." + ext)

        # 3. Add as file without any extension or trailing slash
        paths.add(word)
    
    return list(paths)


def run(session: Dict[str, Any], options: Dict[str, Any]) -> bool:
    url = options.get("url", "http://example.com")
    wordlist_param = options.get("wordlist", "common")
    extensions = options.get("extensions", "php,html,txt,js,css,bak")
    threads = int(options.get("threads", 20))
    timeout = int(options.get("timeout", 5))
    user_agent = options.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Validate URL
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    print(f"[*] Starting Directory Bruteforce")
    print(f"[*] Target: {url}")
    print(f"[*] Wordlist: {wordlist_param}")
    print(f"[*] Extensions: {extensions}")
    print(f"[*] Threads: {threads}")
    print(f"[*] Timeout: {timeout}s")
    print("-" * 60)
    
    # Test connection
    try:
        test_response = requests.get(url, timeout=10, allow_redirects=True)
        print(f"[+] Target is accessible (Status: {test_response.status_code})")
    except Exception as e:
        print(f"[!] Cannot connect to target: {e}")
        return False
    
    # Auto-detect CMS (For smart bruteforcing, but the general wordlist will be prioritized)
    cms_type = detect_cms(url, timeout)
    
    # Load wordlist, prioritizing general or user-supplied file
    base_words = load_wordlist(wordlist_param, cms_type)
    
    # Generate paths (no artificial limits)
    paths = generate_paths(base_words, extensions)
    
    print(f"[*] Total base words used: {len(base_words)}")
    print(f"[*] Generated total paths to test: {len(paths)}")
    
    if len(paths) > 5000:
        print(f"[!] WARNING: Large scan ({len(paths)} paths) detected. This may take a while or lead to rate limiting.")
    
    print("-" * 60)
    
    bruteforcer = DirectoryBruteforcer(url, timeout, user_agent)
    found_count = 0
    
    start_time = time.time()
    
    def check_single_path(path):
        return path, bruteforcer.check_path(path)
    
    print("[*] Starting scan...\n")
    print(f"{'STATUS':<6} | {'SIZE':<6} | PATH")
    print("-" * 50)
    
    # Use ThreadPoolExecutor
    completed = 0
    total = len(paths)
    
    with ThreadPoolExecutor(max_workers=threads) as executor:
        future_to_path = {executor.submit(check_single_path, path): path for path in paths}
        
        for future in as_completed(future_to_path):
            path, result = future.result()
            completed += 1
            
            if result:
                path, status_code, size, message = result
                found_count += 1
                
                # Color-coded output based on status (ANSI codes)
                color = "\033[0m" # Default
                if status_code == 200: color = "\033[92m"  # Green
                elif status_code in [301, 302]: color = "\033[94m" # Blue
                elif status_code == 403: color = "\033[93m" # Yellow
                elif status_code == 401: color = "\033[95m" # Magenta
                elif status_code == 500: color = "\033[91m" # Red
                
                output_line = f"{status_code:<6} {size:<6} {path}"
                if status_code in [301, 302]:
                    output_line = f"{status_code:<6} {size:<6} {path} → {message.split('→')[1].strip()}"
                
                print(f"{color}{output_line}\033[0m")
                
                bruteforcer.found_paths.append((path, status_code, size, message))
            
            # Progress update
            if completed % 100 == 0 or completed == total:
                percent = (completed / total) * 100
                elapsed = time.time() - start_time
                speed = completed / elapsed if elapsed > 0 else 0
                # Use sys.stdout.write for in-line progress update
                sys.stdout.write(f"\r[*] Progress: {completed}/{total} ({percent:.1f}%) - {speed:.1f} req/sec")
                sys.stdout.flush()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Final cleanup of progress line
    sys.stdout.write('\r' + ' ' * 80 + '\r')
    
    print("\n" + "=" * 60)
    print("[*] Scan completed!")
    print(f"[*] Time elapsed: {total_time:.2f} seconds")
    print(f"[*] Total requests: {len(paths)}")
    print(f"[+] Interesting paths found: {found_count}")
    print(f"[*] Average speed: {len(paths)/total_time:.1f} requests/second")
    
    # --- Results Summary and Saving ---
    if found_count > 0:
        print("\n[+] INTERESTING PATHS FOUND:")
        
        # Group by status code
        status_groups: Dict[int, List[Tuple[str, int, str]]] = {}
        for path, status, size, msg in bruteforcer.found_paths:
            if status not in status_groups: status_groups[status] = []
            status_groups[status].append((path, size, msg))
        
        # Display most interesting first
        interesting_codes = [200, 403, 401, 301, 302, 500]
        for status in interesting_codes:
            if status in status_groups:
                count = len(status_groups[status])
                status_name = {
                    200: "OK", 301: "Moved Permanently", 302: "Found", 
                    403: "Forbidden", 401: "Unauthorized", 500: "Server Error"
                }.get(status, f"Status {status}")
                
                print(f"\n--- {status_name} ({status}, {count} paths) ---")
                
                for path, size, msg in status_groups[status][:20]: # Limit summary to 20
                    if status in [200, 403, 500]:
                        print(f"  {path} ({size} bytes)")
                    elif status in [301, 302]:
                        print(f"  {path} → {msg.split('→')[1].strip()}")
                    else:
                        print(f"  {path} - {msg}")
                
                if count > 20:
                    print(f"  ... and {count - 20} more (see output file)")
        
        # Save results
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace(':', '_')
        output_file = f"dir_scan_{domain}_{int(time.time())}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Directory Scan Results\n")
            f.write(f"=====================\n")
            f.write(f"Target: {url}\n")
            f.write(f"CMS Detected: {cms_type if cms_type != 'general' else 'None/General'}\n")
            f.write(f"Wordlist: {wordlist_param}\n")
            f.write(f"Total tested: {len(paths)}\n")
            f.write(f"Found: {found_count}\n\n")
            
            for status in sorted(status_groups.keys()):
                status_name = {
                    200: "OK (200)", 301: "Moved Permanently (301)", 
                    302: "Found (302)", 403: "Forbidden (403)", 
                    401: "Unauthorized (401)", 500: "Server Error (500)"
                }.get(status, f"Status {status}")
                
                f.write(f"{status_name}:\n")
                f.write("-" * len(status_name) + "\n")
                for path, size, msg in status_groups[status]:
                    if status in [200, 403, 500]:
                        f.write(f"{path} ({size} bytes)\n")
                    elif status in [301, 302]:
                        f.write(f"{path} -> {msg}\n")
                    else:
                        f.write(f"{path} - {msg}\n")
                f.write("\n")
        
        print(f"\n[+] Results saved to: {output_file}")
        
    else:
        print("\n[-] No interesting paths found")
        
    return found_count > 0
