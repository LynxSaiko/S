"""
Directory Bruteforce - Find hidden files and directories on Web Servers
"""

MODULE_INFO = {
    "description": "Directory and file bruteforce on web servers"
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
        "description": "Path to wordlist file or built-in list",
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

class DirectoryBruteforcer:
    def __init__(self, base_url, timeout=5, user_agent=None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.user_agent = user_agent
        self.found_paths = []
        self.session = requests.Session()
        
        if user_agent:
            self.session.headers.update({'User-Agent': user_agent})
    
    def check_path(self, path):
        """Check if a path exists on the target"""
        url = urljoin(self.base_url, path)
        
        try:
            response = self.session.get(url, timeout=self.timeout, allow_redirects=False)
            
            # Filter interesting responses
            if response.status_code == 200:
                return path, response.status_code, len(response.content), "OK"
            elif response.status_code == 403:
                return path, response.status_code, len(response.content), "Forbidden"
            elif response.status_code == 301 or response.status_code == 302:
                return path, response.status_code, 0, f"Redirect to {response.headers.get('Location', '?')}"
            elif response.status_code == 401:
                return path, response.status_code, 0, "Unauthorized"
            elif response.status_code == 500:
                return path, response.status_code, len(response.content), "Server Error"
            else:
                return None
        
        except requests.exceptions.RequestException:
            return None

def get_builtin_wordlist():
    """Comprehensive built-in wordlist"""
    wordlist = [
        # Administrative
        "admin", "administrator", "login", "panel", "dashboard", "cp", "controlpanel",
        "manager", "management", "sysadmin", "webadmin", "adminpanel",
        "backend", "secure", "private", "hidden", "secret",
        
        # API endpoints
        "api", "api/v1", "api/v2", "rest", "graphql", "json", "xml",
        
        # Common directories
        "images", "img", "css", "js", "fonts", "assets", "static",
        "uploads", "downloads", "files", "storage", "media",
        "doc", "docs", "document", "documents", "pdf", "archive",
        "backup", "backups", "old", "temp", "tmp", "cache", "log", "logs",
        "db", "database", "sql", "data", "config", "configuration",
        "setup", "install", "update", "upgrade", "maintenance",
        
        # Framework specific
        "wp-admin", "wp-content", "wp-includes", "wordpress",
        "phpmyadmin", "mysql", "pma",
        "joomla", "drupal", "magento", "prestashop",
        "laravel", "symfony", "yii", "codeigniter",
        
        # Common files
        "robots.txt", "sitemap.xml", "sitemap.html", "sitemap_index.xml",
        ".htaccess", ".htpasswd", ".git", ".svn", ".env", ".DS_Store",
        "readme.txt", "license.txt", "changelog.txt", "version.txt",
        "backup.zip", "dump.sql", "database.sql", "backup.sql",
        "test.php", "info.php", "phpinfo.php", "debug.php",
        
        # User related
        "user", "users", "account", "accounts", "member", "members",
        "profile", "profiles", "settings", "preferences",
        
        # Additional common paths
        "cgi-bin", "bin", "scripts", "tools", "utility", "utilities",
        "web", "webapp", "application", "apps", "console", "shell",
        
        # Backup extensions
        "backup", "bak", "old", "temp", "tmp", "archive"
    ]
    
    return wordlist

def load_wordlist(wordlist_param):
    """Load wordlist from file or use built-in"""
    if wordlist_param == "common":
        return get_builtin_wordlist()
    elif wordlist_param == "large":
        large_list = get_builtin_wordlist()
        # Add some variations
        variations = []
        for word in large_list:
            variations.extend([
                word,
                word.upper(),
                word.capitalize(),
                f"{word}1",
                f"{word}2",
                f"{word}2023",
                f"{word}2024"
            ])
        return list(set(variations))  # Remove duplicates
    elif os.path.isfile(wordlist_param):
        try:
            with open(wordlist_param, 'r', encoding='utf-8', errors='ignore') as f:
                words = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                return words[:10000]  # Limit to 10,000 words for safety
        except Exception as e:
            print(f"[!] Error loading wordlist: {e}")
            return get_builtin_wordlist()
    else:
        return get_builtin_wordlist()

def generate_paths(base_words, extensions):
    """Generate paths with extensions - LIMITED to prevent excessive combinations"""
    paths = []
    extensions_list = [ext.strip() for ext in extensions.split(',')] if extensions else []
    
    # Limit the number of base words if too many
    if len(base_words) > 1000:
        base_words = base_words[:1000]
        print(f"[*] Limited wordlist to 1000 words for performance")
    
    for word in base_words:
        # Add as directory (limit this)
        if len(paths) < 5000:  # Safety limit
            paths.append(word + "/")
        
        # Add as file with extensions (limit this too)
        for ext in extensions_list[:10]:  # Max 10 extensions
            if ext and len(paths) < 5000:
                paths.append(word + "." + ext)
        
        # Also add without trailing slash
        if len(paths) < 5000:
            paths.append(word)
    
    return list(set(paths))[:5000]  # Final safety limit

def run(session, options):
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
    
    # Test connection first
    try:
        test_response = requests.get(url, timeout=10, allow_redirects=False)
        print(f"[+] Target is accessible (Status: {test_response.status_code})")
    except Exception as e:
        print(f"[!] Cannot connect to target: {e}")
        return False
    
    # Load and generate paths WITH LIMITS
    base_words = load_wordlist(wordlist_param)
    paths = generate_paths(base_words, extensions)
    
    print(f"[*] Loaded {len(base_words)} base words")
    print(f"[*] Generated {len(paths)} total paths to test")
    
    if len(paths) > 1000:
        print(f"[*] Large scan detected - this may take a while...")
    
    print("-" * 60)
    
    bruteforcer = DirectoryBruteforcer(url, timeout, user_agent)
    found_count = 0
    
    start_time = time.time()
    
    def check_single_path(path):
        result = bruteforcer.check_path(path)
        return path, result
    
    print("[*] Starting scan...\n")
    print("STATUS | CODE | SIZE | PATH")
    print("-" * 50)
    
    # Use ThreadPoolExecutor with progress tracking
    completed = 0
    total = len(paths)
    
    with ThreadPoolExecutor(max_workers=threads) as executor:
        # Submit all tasks
        future_to_path = {executor.submit(check_single_path, path): path for path in paths}
        
        # Process results as they complete
        for future in as_completed(future_to_path):
            path, result = future.result()
            completed += 1
            
            if result:
                path, status_code, size, message = result
                found_count += 1
                
                # Color-coded output based on status
                if status_code == 200:
                    print(f" 200   {size:6} {path}")
                elif status_code == 403:
                    print(f" 403   {size:6} {path}")
                elif status_code in [301, 302]:
                    print(f" {status_code}   {size:6} {path} → {message}")
                elif status_code == 401:
                    print(f" 401   {size:6} {path}")
                elif status_code == 500:
                    print(f" 500   {size:6} {path}")
                else:
                    print(f" {status_code}   {size:6} {path}")
                
                bruteforcer.found_paths.append((path, status_code, size, message))
            
            # Progress update
            if completed % 50 == 0 or completed == total:
                percent = (completed / total) * 100
                print(f"[*] Progress: {completed}/{total} ({percent:.1f}%)")
    
    end_time = time.time()
    
    print("\n" + "=" * 60)
    print("[*] Scan completed!")
    print(f"[*] Time elapsed: {end_time - start_time:.2f} seconds")
    print(f"[*] Paths found: {found_count}/{len(paths)}")
    
    if found_count > 0:
        print("\n[+] INTERESTING PATHS FOUND:")
        
        # Group by status code
        status_groups = {}
        for path, status, size, msg in bruteforcer.found_paths:
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append((path, size, msg))
        
        # Display most interesting first
        interesting_codes = [200, 301, 302, 403, 401, 500]
        for status in interesting_codes:
            if status in status_groups:
                print(f"\n--- Status {status} ({len(status_groups[status])} paths) ---")
                for path, size, msg in status_groups[status][:10]:  # Show first 10
                    if status == 200:
                        print(f"  {path} ({size} bytes)")
                    else:
                        print(f"  {path} - {msg}")
                if len(status_groups[status]) > 10:
                    print(f"  ... and {len(status_groups[status]) - 10} more")
        
        # Save results
        domain = url.replace('://', '_').replace('/', '_').replace(':', '_')
        output_file = f"dir_scan_{domain}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Directory Scan Results - {url}\n")
            f.write(f"Time: {time.ctime()}\n")
            f.write(f"Scan duration: {end_time - start_time:.2f}s\n")
            f.write(f"Total paths tested: {len(paths)}\n")
            f.write(f"Paths found: {found_count}\n\n")
            
            for status in sorted(status_groups.keys()):
                f.write(f"=== Status {status} ===\n")
                for path, size, msg in status_groups[status]:
                    if status == 200:
                        f.write(f"{path} ({size} bytes)\n")
                    else:
                        f.write(f"{path} - {msg}\n")
                f.write("\n")
        
        print(f"\n[+] Results saved to: {output_file}")
        
        # Suggest next steps
        print("\n[+] Next steps:")
        if 200 in status_groups:
            print("  - Visit the found pages in your browser")
        if 403 in status_groups or 401 in status_groups:
            print("  - Try authentication bypass techniques")
        if 301 in status_groups or 302 in status_groups:
            print("  - Check the redirect locations")
    else:
        print("[-] No interesting paths found")
        print("[*] Try:")
        print("  - Different wordlist")
        print("  - More file extensions") 
        print("  - Check if target is blocking requests")
    
    return found_count > 0
