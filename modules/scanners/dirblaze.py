import requests
import threading
import time
from pathlib import Path
import sys
import random
import concurrent.futures
from queue import Queue
import re
import urllib.parse

# Suppress SSL warnings
try:
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except:
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except:
        pass

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# Rich untuk table
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from rich.text import Text
    from rich.columns import Columns
    from rich.align import Align
    from rich.live import Live
    from rich.layout import Layout
    from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False

MODULE_INFO = {
    "name": "discovery/dirbuster_ultra",
    "description": "Ultra fast directory and file bruteforce dengan real-time progress tracking"
}

OPTIONS = {
    "TARGET": {
        "required": True,
        "default": "http://localhost",
        "description": "Target URL"
    },
    "WORDLIST": {
        "required": True,
        "default": "common_dirs.txt",
        "description": "File wordlist untuk directory bruteforce"
    },
    "EXTENSIONS": {
        "required": False,
        "default": "php,html,js,txt,json,xml,asp,aspx,jsp",
        "description": "Ekstensi file yang akan di-test (dipisahkan koma)"
    },
    "USER_AGENT": {
        "required": False,
        "default": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "description": "User-Agent untuk request"
    },
    "THREADS": {
        "required": False,
        "default": "50",
        "description": "Jumlah threads (1-200)"
    },
    "DELAY": {
        "required": False,
        "default": "0.01",
        "description": "Delay antara request (detik)"
    },
    "TIMEOUT": {
        "required": False,
        "default": "3",
        "description": "Timeout request (detik)"
    },
    "SSL_VERIFY": {
        "required": False,
        "default": "false",
        "description": "Verify SSL certificate (true/false)"
    },
    "PROXY": {
        "required": False,
        "default": "",
        "description": "Proxy server (optional)"
    },
    "FOLLOW_REDIRECTS": {
        "required": False,
        "default": "true",
        "description": "Follow redirects (true/false)"
    },
    "CHECK_FILE_SIZE": {
        "required": False,
        "default": "true",
        "description": "Check file size untuk filter false positive (true/false)"
    },
    "MIN_FILE_SIZE": {
        "required": False,
        "default": "10",
        "description": "Minimum file size dalam bytes"
    },
    "MAX_FILE_SIZE": {
        "required": False,
        "default": "10485760",
        "description": "Maximum file size dalam bytes (10MB default)"
    },
    "SHOW_ALL": {
        "required": False,
        "default": "false",
        "description": "Tampilkan semua response termasuk 404 (true/false)"
    },
    "RECURSIVE": {
        "required": False,
        "default": "false",
        "description": "Bruteforce recursively pada directories yang ditemukan (true/false)"
    }
}

def display_header():
    """Display header panel yang menarik"""
    if not RICH_AVAILABLE:
        return
    
    header_text = Text()
    header_text.append("🔍 ", style="bold red")
    header_text.append("DIRBUSTER ULTRA ", style="bold yellow")
    header_text.append("DIRECTORY ", style="bold cyan")
    header_text.append("BRUTEFORCE", style="bold green")
    
    sub_text = Text()
    sub_text.append("⚡ ", style="bold yellow")
    sub_text.append("High-Speed Directory & File Discovery Tool", style="bold white")
    
    header_panel = Panel(
        Align.center(header_text + "\n" + sub_text),
        border_style="bright_blue",
        padding=(1, 2),
        style="bold"
    )
    
    console.print(header_panel)

class DirectoryBruteforcer:
    """Class untuk directory bruteforce yang ultra cepat"""
    
    def __init__(self, options):
        self.options = options
        self.setup_components()
        self.results = {
            "found_paths": [],
            "attempts": 0,
            "start_time": None,
            "current_speed": 0,
            "status_codes": {},
            "interesting_paths": []
        }
        self.stop_event = threading.Event()
        self.path_queue = Queue()
        self.lock = threading.Lock()
    
    def setup_components(self):
        """Setup komponen"""
        self.headers = {
            'User-Agent': self.options.get("USER_AGENT"),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        self.ssl_verify = self.options.get("SSL_VERIFY", "false").lower() == "true"
        self.timeout = int(self.options.get("TIMEOUT", "3"))
        self.threads = max(1, min(200, int(self.options.get("THREADS", "50"))))
        self.delay = float(self.options.get("DELAY", "0.01"))
        self.follow_redirects = self.options.get("FOLLOW_REDIRECTS", "true").lower() == "true"
        self.check_file_size = self.options.get("CHECK_FILE_SIZE", "true").lower() == "true"
        self.min_file_size = int(self.options.get("MIN_FILE_SIZE", "10"))
        self.max_file_size = int(self.options.get("MAX_FILE_SIZE", "10485760"))
        self.show_all = self.options.get("SHOW_ALL", "false").lower() == "true"
        self.recursive = self.options.get("RECURSIVE", "false").lower() == "true"
        
        # Parse extensions
        self.extensions = []
        extensions_str = self.options.get("EXTENSIONS", "php,html,js,txt,json,xml,asp,aspx,jsp")
        if extensions_str:
            self.extensions = [ext.strip() for ext in extensions_str.split(',') if ext.strip()]
        
        # Setup proxies
        self.proxies = {}
        proxy = self.options.get("PROXY", "").strip()
        if proxy:
            self.proxies = {"http": proxy, "https": proxy}
        
        # Load wordlist
        self.wordlist = self.load_wordlist()
        
        # Threading
        self.progress_bar = None
        
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[*] [cyan]Configuration Loaded[/cyan]\n"
                f"[*] Wordlist: [yellow]{len(self.wordlist)} paths[/yellow]\n"
                f"[*] Extensions: [green]{', '.join(self.extensions)}[/green]\n"
                f"[*] Threads: [blue]{self.threads}[/blue]\n"
                f"[*] Timeout: [magenta]{self.timeout}s[/magenta]",
                border_style="blue",
                padding=(1, 2)
            ))
    
    def load_wordlist(self):
        """Load wordlist dari file atau gunakan default"""
        wordlist_file = self.options.get("WORDLIST", "")
        wordlist = []
        
        try:
            if Path(wordlist_file).is_file():
                with open(wordlist_file, 'r', encoding='utf-8', errors='ignore') as f:
                    wordlist = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                if RICH_AVAILABLE:
                    console.print(f"[*] [green]Loaded {len(wordlist)} paths from {wordlist_file}[/green]")
            else:
                # Gunakan built-in super wordlist
                wordlist = self.get_super_wordlist()
                if RICH_AVAILABLE:
                    console.print(f"[*] [yellow]Using built-in super wordlist with {len(wordlist)} paths[/yellow]")
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[*] [red]Error loading wordlist: {e}[/red]")
            wordlist = self.get_super_wordlist()
        
        return wordlist
    
    def get_super_wordlist(self):
        """Super comprehensive built-in wordlist"""
        return [
            # ==================== ADMIN & LOGIN PATHS ====================
            "admin", "administrator", "adminpanel", "admin_login", "admin_area",
            "admin1", "admin2", "admin3", "admin4", "admin5", "admin6", "admin7", "admin8",
            "admin-login", "admincp", "admin_cp", "admin_control", "admin_center",
            "adminconsole", "admin_console", "admin-portal", "admin_portal",
            "login", "log_in", "signin", "sign_in", "member_login", "user_login",
            "auth", "authentication", "authenticate", "authorize", "authorization",
            "portal", "myaccount", "account", "user", "member", "client", "customer",
            "secure", "secure_login", "secure-auth", "secure_auth",
            "dashboard", "control", "controlpanel", "cp", "cpanel", "webcp",
            "webadmin", "sysadmin", "serveradmin", "siteadmin", "server", "system",
            "manage", "manager", "management", "admin_manage", "admin_management",
            "panel", "admin_panel", "control_panel", "user_panel", "member_panel",
            "root", "superuser", "super_admin", "superadmin", "super_user",
            "backend", "back_end", "backoffice", "back_office", "backoffice_login",
            "staff", "staff_login", "employee", "employee_login", "hr", "hr_login",
            "moderator", "moderator_login", "editor", "editor_login", "publisher",
            
            # ==================== COMMON DIRECTORIES ====================
            "public", "private", "protected", "hidden", "secret", "confidential",
            "uploads", "upload", "files", "file", "images", "image", "img", "pictures",
            "photos", "assets", "static", "media", "download", "downloads", "documents",
            "docs", "storage", "data", "database", "db", "sql", "mysql", "postgres",
            "system", "sys", "config", "configuration", "settings", "setup", "install",
            "installation", "update", "upgrade", "migrate", "migration",
            "backup", "backups", "bak", "back", "old", "temp", "tmp", "cache", "cached",
            "logging", "logs", "error_log", "access_log", "debug", "debug_log",
            "app", "application", "apps", "webapp", "webapps", "mobile", "mobi",
            "api", "apis", "rest", "restapi", "graphql", "soap", "json", "xml",
            "v1", "v2", "v3", "v4", "version1", "version2", "version3",
            "service", "services", "webservice", "webservices", "microservice",
            "content", "contents", "pages", "page", "posts", "post", "articles",
            "article", "blog", "blogs", "news", "newsletter", "forum", "forums",
            "board", "boards", "chat", "message", "mail", "email", "contact",
            "contacts", "support", "helpdesk", "ticket", "tickets",
            
            # ==================== TECHNOLOGY SPECIFIC ====================
            "php", "phpmyadmin", "phppgadmin", "phpinfo", "test.php", "debug.php",
            "info.php", "status.php", "server-status", "server_info",
            "asp", "aspx", "asmx", "ashx", "web.config", "global.asax",
            "jsp", "servlet", "struts", "spring", "web-inf", "web.xml",
            "python", "django", "flask", "py", "wsgi", "cgi-bin", "cgi",
            "ruby", "rails", "rack", "sinatra", "config.ru",
            "node", "express", "npm", "package.json", "app.js", "server.js",
            
            # ==================== CMS SPECIFIC ====================
            "wp", "wp-admin", "wp-login.php", "wp-content", "wp-includes",
            "wordpress", "wp-json", "wp-ajax", "wp-cron.php", "wp-mail.php",
            "joomla", "administrator", "component", "modules", "plugins",
            "templates", "images", "media", "cache", "joomla16", "joomla17",
            "drupal", "user", "user/login", "admin", "node", "taxonomy",
            "comment", "block", "filter", "file", "image", "drupal7", "drupal8",
            "magento", "adminhtml", "customer", "catalog", "checkout",
            "wishlist", "sales", "review", "newsletter", "magento2",
            "laravel", "artisan", "storage", "vendor", "bootstrap",
            "resources", "routes", "middleware", "laravel5", "laravel6",
            
            # ==================== CONFIGURATION FILES ====================
            ".htaccess", ".htpasswd", ".git", ".gitignore", ".gitconfig",
            ".svn", ".env", ".dockerignore", ".editorconfig", ".env.local",
            ".env.production", ".env.development", ".env.test",
            "config.php", "config.json", "config.xml", "config.yml",
            "config.yaml", "configuration.php", "settings.php", "setting.php",
            "database.php", "db.php", "db_config.php", "database.xml",
            "app.config", "web.config", "application.cfg", "app.ini",
            "env.php", "environment.php", "setup.php", "install.php",
            "backup.sql", "backup.zip", "backup.tar", "backup.gz",
            "dump.sql", "database.sql", "db_backup.sql", "db_dump.sql",
            "www.zip", "site.zip", "web.zip", "public.zip", "backup_www",
            "backup_2024", "backup_2023", "backup2024", "backup2023",
            "backup_2022", "backup2022", "backup_2021", "backup2021",
            
            # ==================== API ENDPOINTS ====================
            "api/v1", "api/v2", "api/v3", "api/v4", "rest/api", "rest/v1",
            "rest/v2", "graphql", "graphiql", "playground", "voyager",
            "oauth", "oauth2", "auth", "authentication", "token", "jwt",
            "session", "sso", "cas", "openid", "saml", "ldap",
            "users", "user", "customers", "customer", "clients", "client",
            "products", "product", "items", "item", "goods", "catalog",
            "orders", "order", "payments", "payment", "billing", "invoice",
            "categories", "category", "tags", "tag", "types", "type",
            "search", "find", "query", "filter", "sort", "page", "limit",
            "upload", "download", "file", "files", "image", "images",
            "media", "assets", "document", "documents",
            
            # ==================== DEVELOPMENT & TESTING ====================
            "dev", "development", "develop", "developer", "developers",
            "test", "testing", "test1", "test2", "test3", "test4", "test5",
            "stage", "staging", "preprod", "pre-production", "pre_prod",
            "demo", "demonstration", "sample", "example", "sandbox",
            "debug", "debugging", "troubleshoot", "troubleshooting",
            "qa", "quality", "quality-assurance", "quality_assurance",
            "uat", "user-acceptance-testing", "user_acceptance_testing",
            "build", "builds", "dist", "distrib", "distribution",
            "deploy", "deployment", "release", "releases", "version",
            
            # ==================== SECURITY & HIDDEN PATHS ====================
            "security", "secure", "protected", "private", "hidden", "secret",
            "confidential", "restricted", "auth", "authorization", "permission",
            "access", "acl", "firewall", "waf", "security-check",
            "_admin", "_private", "_hidden", "_secret", "_backup", "_tmp",
            ".admin", ".private", ".hidden", ".secret", ".backup", ".tmp",
            "~admin", "~private", "~hidden", "~secret", "~backup", "~tmp",
            "backup_", "bak_", "old_", "temp_", "tmp_", "archived_",
            "_backup", "_bak", "_old", "_temp", "_tmp", "_archived",
            "shell", "cmd", "command", "exec", "execute", "system", "eval",
            "phpinfo", "info.php", "test.php", "debug.php", "status.php",
            
            # ==================== DOCUMENTATION ====================
            "docs", "documentation", "doc", "help", "helps", "guide",
            "guides", "manual", "manuals", "tutorial", "tutorials",
            "faq", "faqs", "knowledgebase", "kb", "support", "helpsupport",
            "howto", "how-to", "instruction", "instructions", "readme",
            "terms", "terms-of-service", "tos", "termsofservice",
            "privacy", "privacy-policy", "privacypolicy",
            "license", "licensing", "eula", "agreement",
            "disclaimer", "copyright", "legal", "notice",
            
            # ==================== E-COMMERCE ====================
            "shop", "shopping", "store", "estore", "ecommerce", "e-commerce",
            "cart", "shopping-cart", "basket", "checkout", "payment",
            "pay", "checkout-success", "checkout-failed", "checkout_success",
            "orders", "order-history", "order-tracking", "order_history",
            "products", "product-detail", "catalog", "category", "categories",
            "wishlist", "favorites", "compare", "review", "reviews", "rating",
            "customer", "my-account", "account-settings", "my_account",
            "billing", "shipping", "address", "payment-method", "invoice",
            
            # ==================== SERVER & INFRASTRUCTURE ====================
            "server", "server-status", "server-info", "server_information",
            "webmin", "plesk", "cpanel", "whm", "directadmin", "virtualmin",
            "virtuoso", "webmail", "roundcube", "squirrelmail", "horde",
            "phpmyadmin", "phppgadmin", "adminer", "mysql-admin", "mysql_admin",
            "pgadmin", "sqlite", "mongodb", "redis-admin", "redis_admin",
            "monitoring", "monitor", "status", "health", "healthcheck",
            "metrics", "statistics", "stats", "analytics", "report", "reports",
            "performance", "perf", "benchmark", "load", "traffic",
            
            # ==================== ADDITIONAL COMMON PATHS ====================
            "index", "main", "home", "default", "start", "welcome",
            "web", "website", "site", "cms", "content-management",
            "user-content", "member-area", "client-area", "partner",
            "partners", "affiliate", "affiliates", "reseller", "resellers",
            "vendor", "vendors", "supplier", "suppliers", "provider", "providers",
            "operator", "operators", "mod", "mods", "redactor", "editors",
            "publisher", "publishers", "author", "authors", "writer", "writers",
            "contributor", "contributors", "guest", "guests", "visitor", "visitors",
            "subscriber", "subscribers", "registrar", "registration", "register",
            "signup", "sign_up", "create-account", "new-account", "activate",
            "activation", "verify", "verification", "confirm", "confirmation",
            "recover", "recovery", "reset", "reset-password", "forgot",
            "forgot-password", "change-password", "password-reset",
            "logout", "log_out", "signout", "sign_out", "exit", "leave",
            "session", "sessions", "profile", "profiles", "settings",
            "preferences", "options", "configs", "setup", "installer",
            "installation", "wizard", "guide", "tutorial", "helpdesk",
            "ticket", "tickets", "issue", "issues", "bug", "bugs",
            "report", "reports", "feedback", "suggestions", "contact-us",
            "contact-form", "about", "about-us", "company", "team",
            "careers", "jobs", "career", "job", "opportunities",
            "services", "our-services", "products", "our-products",
            "portfolio", "work", "works", "cases", "study", "studies",
            "testimonial", "testimonials", "reviews", "rating", "ratings",
            "like", "likes", "favorite", "favorites", "bookmark", "bookmarks",
            "save", "saved", "history", "timeline", "activity", "activities",
            "notification", "notifications", "alert", "alerts", "message",
            "messages", "inbox", "outbox", "compose", "new-message",
            "chat", "chats", "conversation", "conversations", "forum",
            "forums", "discussion", "discussions", "topic", "topics",
            "thread", "threads", "post", "posts", "comment", "comments",
            "reply", "replies", "blog", "blogs", "article", "articles",
            "news", "newsletter", "subscription", "subscriptions",
            "feed", "feeds", "rss", "atom", "xmlrpc", "sitemap",
            "sitemap.xml", "sitemap_index.xml", "robots", "robots.txt",
            "humans.txt", "ads.txt", "security.txt", "well-known",
            ".well-known", "well-known/security.txt", "well-known/assetlinks.json",
            
            # ==================== FILE EXTENSIONS ====================
            "index.php", "index.html", "index.htm", "index.asp", "index.aspx",
            "index.jsp", "index.js", "default.php", "default.html", "default.asp",
            "main.php", "main.html", "home.php", "home.html", "admin.php",
            "admin.html", "admin.asp", "admin.aspx", "login.php", "login.html",
            "login.asp", "login.aspx", "config.php", "config.html", "config.asp",
            "test.php", "test.html", "test.asp", "debug.php", "debug.html",
            "setup.php", "setup.html", "install.php", "install.html",
            "readme.txt", "license.txt", "changelog.txt", "version.txt",
            "error_log", "access_log", "debug.log", "system.log",
        ]
    
    def generate_path_combinations(self):
        """Generate semua kombinasi path yang akan di-test"""
        all_paths = []
        
        for path in self.wordlist:
            # Skip empty paths
            if not path.strip():
                continue
                
            # Tambahkan path asli (dengan atau tanpa leading slash)
            if not path.startswith('/'):
                all_paths.append(f"/{path}")
            else:
                all_paths.append(path)
            
            # Tambahkan dengan extensions untuk file-like paths
            if not path.endswith('/') and '.' not in path.split('/')[-1]:
                for ext in self.extensions:
                    if not path.startswith('/'):
                        all_paths.append(f"/{path}.{ext}")
                    else:
                        all_paths.append(f"{path}.{ext}")
            
            # Tambahkan kombinasi directory + file untuk directory-like paths
            if not path.endswith('.') and not any(path.endswith(ext) for ext in self.extensions):
                if not path.startswith('/'):
                    all_paths.append(f"/{path}/")
                else:
                    all_paths.append(f"{path}/")
                    
                for ext in self.extensions:
                    if not path.startswith('/'):
                        all_paths.append(f"/{path}/index.{ext}")
                        all_paths.append(f"/{path}/main.{ext}")
                        all_paths.append(f"/{path}/default.{ext}")
                    else:
                        all_paths.append(f"{path}/index.{ext}")
                        all_paths.append(f"{path}/main.{ext}")
                        all_paths.append(f"{path}/default.{ext}")
        
        # Hapus duplikat dan return
        unique_paths = list(dict.fromkeys(all_paths))
        
        if RICH_AVAILABLE:
            console.print(f"[*] [cyan]Generated {len(unique_paths):,} total path combinations[/cyan]")
        
        return unique_paths
    
    def create_session(self):
        """Create session dengan connection pooling"""
        session = requests.Session()
        session.headers.update(self.headers)
        
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=1
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def check_path(self, session, full_url, original_path):
        """Check single path"""
        try:
            start_time = time.time()
            response = session.get(
                full_url,
                verify=self.ssl_verify,
                timeout=self.timeout,
                proxies=self.proxies,
                allow_redirects=self.follow_redirects,
                stream=True  # Stream untuk menghindari download content besar
            )
            
            response_time = time.time() - start_time
            content_length = int(response.headers.get('content-length', 0))
            
            # Jika content-length tidak ada, baca sedikit content untuk menentukan size
            if content_length == 0:
                content_length = len(response.content) if len(response.content) < 1024 else 1024
            
            # Filter berdasarkan file size jika diaktifkan
            if self.check_file_size:
                if content_length < self.min_file_size or content_length > self.max_file_size:
                    response.close()
                    return None
            
            result = {
                "url": full_url,
                "path": original_path,
                "status_code": response.status_code,
                "content_length": content_length,
                "headers": dict(response.headers),
                "final_url": response.url,
                "title": self.extract_title(response.text) if content_length < 10000 else "Content too large"
            }
            
            response.close()
            return result
            
        except requests.exceptions.Timeout:
            return {
                "url": full_url,
                "path": original_path,
                "status_code": "TIMEOUT",
                "error": "Request timeout",
                "content_length": 0
            }
        except requests.exceptions.ConnectionError:
            return {
                "url": full_url,
                "path": original_path,
                "status_code": "CONN_ERROR",
                "error": "Connection error",
                "content_length": 0
            }
        except Exception as e:
            return {
                "url": full_url,
                "path": original_path,
                "status_code": "ERROR",
                "error": str(e),
                "content_length": 0
            }
    
    def extract_title(self, html):
        """Extract title dari HTML"""
        if not html:
            return "No Title"
        
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            return title[:100] + "..." if len(title) > 100 else title
        return "No Title"
    
    def is_interesting_response(self, result):
        """Check jika response menarik untuk ditampilkan"""
        # Convert status_code ke string untuk konsistensi
        status_code = str(result["status_code"])
        
        if status_code in ['200', '201', '301', '302', '307', '401', '403', '500', '503']:
            return True
        
        # Include 404 jika show_all diaktifkan
        if self.show_all and status_code == '404':
            return True
            
        return False
    
    def is_high_priority(self, result):
        """Check jika path termasuk high priority"""
        high_priority_keywords = [
            'admin', 'login', 'config', 'backup', 'sql', 'database', 
            'password', 'secret', 'api', 'ssh', 'ftp', 'ssh', 'cpanel',
            'phpmyadmin', 'webmin', 'plesk', 'env', 'git', 'svn'
        ]
        
        path_lower = result["path"].lower()
        return any(keyword in path_lower for keyword in high_priority_keywords)
    
    def worker(self):
        """Worker thread untuk bruteforce"""
        session = self.create_session()
        
        while not self.stop_event.is_set() and not self.path_queue.empty():
            try:
                path = self.path_queue.get(timeout=1)
            except:
                break
            
            full_url = f"{self.options.get('TARGET').rstrip('/')}{path}"
            result = self.check_path(session, full_url, path)
            
            with self.lock:
                self.results["attempts"] += 1
                
                # Update status code statistics
                if result:
                    # Convert status_code ke string untuk konsistensi
                    status = str(result["status_code"])
                    if status in self.results["status_codes"]:
                        self.results["status_codes"][status] += 1
                    else:
                        self.results["status_codes"][status] = 1
                
                if result and self.is_interesting_response(result):
                    self.results["found_paths"].append(result)
                    
                    # Tandai sebagai interesting jika high priority
                    if self.is_high_priority(result):
                        self.results["interesting_paths"].append(result)
                    
                    # Tampilkan hasil langsung jika menarik
                    status_code_str = str(result["status_code"])
                    if status_code_str in ['200', '301', '302', '401', '403']:
                        self.display_live_result(result)
            
            # Delay antara requests
            if self.delay > 0:
                time.sleep(self.delay)
            
            # Update progress bar
            if TQDM_AVAILABLE and self.progress_bar:
                self.progress_bar.update(1)
            
            self.path_queue.task_done()
        
        session.close()
    
    def display_live_result(self, result):
        """Display hasil langsung saat ditemukan"""
        if not RICH_AVAILABLE:
            status_emoji = self.get_status_emoji(result["status_code"])
            status_code_str = str(result["status_code"])
            print(f"[FOUND] {status_emoji} {status_code_str:>3} - {result['content_length']:7d} - {result['url']}")
            return
        
        status_emoji = self.get_status_emoji(result["status_code"])
        status_color = self.get_status_color(result["status_code"])
        
        # Highlight interesting paths
        is_interesting = self.is_high_priority(result)
        path_style = "bold magenta" if is_interesting else "cyan"
        
        status_text = Text()
        status_text.append(f"{status_emoji} ", style="bold")
        status_text.append(f"{str(result['status_code']):>3}", style=status_color)
        status_text.append(f" - {result['content_length']:7d} bytes - ", style="white")
        status_text.append(f"{result['path']}", style=path_style)
        
        if is_interesting:
            status_text.append(" ⚡", style="bold yellow")
        
        console.print(status_text)
    
    def get_status_emoji(self, status_code):
        """Get emoji untuk status code"""
        # Convert ke string untuk konsistensi
        status_str = str(status_code)
        emoji_map = {
            '200': "✅", '201': "✅", '301': "🔄", '302': "🔄", '307': "🔄",
            '401': "🔐", '403': "🚫", '404': "❌", '500': "💥", '503': "🔧",
            "TIMEOUT": "⏰", "CONN_ERROR": "🔌", "ERROR": "❓"
        }
        return emoji_map.get(status_str, "❓")
    
    def get_status_color(self, status_code):
        """Get color untuk status code"""
        # Convert ke string untuk konsistensi
        status_str = str(status_code)
        color_map = {
            '200': "green", '201': "green", '301': "yellow", '302': "yellow", '307': "yellow",
            '401': "magenta", '403': "red", '404': "white", '500': "red", '503': "yellow",
            "TIMEOUT": "blue", "CONN_ERROR": "red", "ERROR": "white"
        }
        return color_map.get(status_str, "white")
    
    def run(self):
        """Main execution"""
        display_header()
        
        # Generate semua path combinations
        all_paths = self.generate_path_combinations()
        
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[*] [cyan]Bruteforce Configuration[/cyan]\n"
                f"[*] Target: [yellow]{self.options.get('TARGET')}[/yellow]\n"
                f"[*] Total Paths: [red]{len(all_paths):,}[/red]\n"
                f"[*] Threads: [green]{self.threads}[/green]\n"
                f"[*] Extensions: [blue]{', '.join(self.extensions)}[/blue]\n"
                f"[*] Delay: [magenta]{self.delay}s[/magenta]\n"
                f"[*] Timeout: [cyan]{self.timeout}s[/cyan]",
                border_style="blue",
                padding=(1, 2)
            ))
        
        # Masukkan semua paths ke queue
        for path in all_paths:
            self.path_queue.put(path)
        
        self.total_attempts = len(all_paths)
        self.results["start_time"] = time.time()
        
        # Setup progress bar
        if TQDM_AVAILABLE:
            self.progress_bar = tqdm(
                total=self.total_attempts,
                desc="Bruteforcing",
                unit="path",
                dynamic_ncols=True,
                bar_format="{l_bar}{bar:20}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]",
                position=0,
                leave=True
            )
            self.progress_bar.set_postfix_str("Starting...")
        else:
            print(f"[*] Starting directory bruteforce with {self.total_attempts:,} paths...")
        
        # Start worker threads
        threads = []
        for i in range(self.threads):
            thread = threading.Thread(
                target=self.worker,
                name=f"DirWorker-{i+1}"
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Monitor progress
        last_attempts = 0
        last_time = time.time()
        
        try:
            while not self.stop_event.is_set() and self.results["attempts"] < self.total_attempts:
                time.sleep(0.5)
                
                # Calculate current speed
                current_time = time.time()
                attempts_diff = self.results["attempts"] - last_attempts
                time_diff = current_time - last_time
                
                if time_diff > 0:
                    current_speed = attempts_diff / time_diff
                    self.results["current_speed"] = current_speed
                    
                    if TQDM_AVAILABLE and self.progress_bar:
                        elapsed = current_time - self.results["start_time"]
                        eta = (self.total_attempts - self.results["attempts"]) / current_speed if current_speed > 0 else 0
                        postfix = f"Speed: {current_speed:,.0f}/s | ETA: {eta:.0f}s"
                        self.progress_bar.set_postfix_str(postfix)
                
                last_attempts = self.results["attempts"]
                last_time = current_time
                
                if self.path_queue.empty():
                    break
                    
        except KeyboardInterrupt:
            self.stop_event.set()
            if RICH_AVAILABLE:
                console.print("\n[*] [yellow]Bruteforce interrupted by user[/yellow]")
        
        self.stop_event.set()
        for thread in threads:
            thread.join(timeout=2)
        
        # Tampilkan hasil akhir
        self.display_final_results()
    
    def display_final_results(self):
        """Display hasil akhir"""
        elapsed_time = time.time() - self.results["start_time"]
        
        if TQDM_AVAILABLE and self.progress_bar:
            self.progress_bar.close()
        
        if not RICH_AVAILABLE:
            self.display_simple_results(elapsed_time)
            return
        
        # Tampilkan summary statistics
        attempts_per_second = self.results["attempts"] / elapsed_time if elapsed_time > 0 else 0
        
        summary_content = (
            f"[*] [bold cyan]Target:[/bold cyan] {self.options.get('TARGET')}\n"
            f"[*] [bold yellow]Total Attempts:[/bold yellow] {self.results['attempts']:,}\n"
            f"[*] [bold green]Found Paths:[/bold green] {len(self.results['found_paths'])}\n"
            f"[*] [bold magenta]Interesting Paths:[/bold magenta] {len(self.results['interesting_paths'])}\n"
            f"[*] [bold blue]Execution Time:[/bold blue] {elapsed_time:.2f} seconds\n"
            f"[*] [bold cyan]Average Speed:[/bold cyan] {attempts_per_second:,.1f} paths/second"
        )
        
        summary_panel = Panel(
            summary_content,
            title="SCAN SUMMARY",
            border_style="bright_blue",
            padding=(1, 2)
        )
        
        console.print(summary_panel)
        
        # Tampilkan status code statistics
        if self.results["status_codes"]:
            status_table = Table(
                title="Status Code Statistics",
                box=box.SIMPLE,
                show_header=True,
                header_style="bold magenta"
            )
            status_table.add_column("Status", style="bold", justify="center")
            status_table.add_column("Count", style="cyan", justify="right")
            status_table.add_column("Percentage", style="green", justify="right")
            
            total_attempts = self.results["attempts"]
            for code, count in sorted(self.results["status_codes"].items()):
                percentage = (count / total_attempts) * 100
                status_table.add_row(
                    str(code),
                    f"{count:,}",
                    f"{percentage:.1f}%"
                )
            
            console.print(status_table)
        
        # Tampilkan interesting paths terlebih dahulu
        if self.results["interesting_paths"]:
            self.display_interesting_paths()
        
        # Tampilkan semua hasil yang ditemukan
        if self.results["found_paths"]:
            self.display_results_table()
        else:
            console.print(Panel(
                "❌ [bold red]No interesting paths found during bruteforce[/bold red]\n"
                f"💡 Tried {self.results['attempts']:,} different paths\n"
                "💡 Try using different wordlists or check the target URL",
                border_style="red",
                padding=(1, 2)
            ))
    
    def display_interesting_paths(self):
        """Display interesting/high priority paths"""
        table = Table(
            title="⚡ INTERESTING PATHS FOUND",
            box=box.DOUBLE_EDGE,
            show_header=True,
            header_style="bold yellow"
        )
        table.add_column("Status", style="bold", width=4, justify="center")
        table.add_column("Path", style="magenta", overflow="fold")
        table.add_column("Size", style="yellow", justify="right", width=10)
        table.add_column("Title", style="green", overflow="fold")
        
        for result in self.results["interesting_paths"][:20]:  # Tampilkan max 20
            status_emoji = self.get_status_emoji(result["status_code"])
            content_length = result["content_length"]
            title = result.get("title", "No Title")
            
            # Format file size
            if content_length >= 1024 * 1024:
                size_str = f"{content_length / (1024 * 1024):.1f} MB"
            elif content_length >= 1024:
                size_str = f"{content_length / 1024:.1f} KB"
            else:
                size_str = f"{content_length} B"
            
            table.add_row(
                f"{status_emoji}",
                f"{result['path']}",
                f"{size_str}",
                f"{title[:50]}..." if len(title) > 50 else title
            )
        
        interesting_panel = Panel(
            table,
            title=f"⚡ FOUND {len(self.results['interesting_paths'])} INTERESTING PATHS",
            border_style="yellow",
            padding=(1, 1)
        )
        
        console.print(interesting_panel)
    
    def display_results_table(self):
        """Display semua hasil dalam table"""
        table = Table(
            title="ALL DISCOVERED PATHS",
            box=box.DOUBLE_EDGE,
            show_header=True,
            header_style="bold green"
        )
        table.add_column("Status", style="bold", width=4, justify="center")
        table.add_column("Path", style="cyan", overflow="fold")
        table.add_column("Size", style="yellow", justify="right", width=10)
        table.add_column("URL", style="blue", overflow="fold")
        
        # Sort results dengan key yang aman (convert status_code ke string)
        def safe_sort_key(x):
            status_code = str(x["status_code"])
            return (status_code, x["path"])
        
        sorted_results = sorted(self.results["found_paths"], key=safe_sort_key)
        
        for result in sorted_results[:100]:  # Tampilkan max 100 results
            status_emoji = self.get_status_emoji(result["status_code"])
            content_length = result["content_length"]
            
            # Format file size
            if content_length >= 1024 * 1024:
                size_str = f"{content_length / (1024 * 1024):.1f} MB"
            elif content_length >= 1024:
                size_str = f"{content_length / 1024:.1f} KB"
            else:
                size_str = f"{content_length} B"
            
            # Highlight interesting paths
            path_style = "bold magenta" if self.is_high_priority(result) else "cyan"
            
            table.add_row(
                f"{status_emoji}",
                f"{result['path']}",
                f"{size_str}",
                f"{result['url'][:60]}..." if len(result['url']) > 60 else result['url']
            )
        
        results_panel = Panel(
            table,
            title=f"DISCOVERED {len(self.results['found_paths'])} PATHS (showing first 100)",
            border_style="green",
            padding=(1, 1)
        )
        
        console.print(results_panel)
        
        # Tampilkan pesan jika ada lebih dari 100 results
        if len(self.results["found_paths"]) > 100:
            console.print(f"[*] [yellow]... and {len(self.results['found_paths']) - 100} more paths found[/yellow]")
    
    def display_simple_results(self, elapsed_time):
        """Display results sederhana tanpa rich"""
        print(f"\n[*] SCAN COMPLETED")
        print(f"[*] Target: {self.options.get('TARGET')}")
        print(f"[*] Total Attempts: {self.results['attempts']:,}")
        print(f"[*] Found Paths: {len(self.results['found_paths'])}")
        print(f"[*] Interesting Paths: {len(self.results['interesting_paths'])}")
        print(f"[*] Execution Time: {elapsed_time:.2f} seconds")
        
        if self.results["interesting_paths"]:
            print(f"\n[*] INTERESTING PATHS:")
            for result in self.results["interesting_paths"]:
                status_emoji = self.get_status_emoji(result["status_code"])
                status_code_str = str(result["status_code"])
                print(f"  {status_emoji} {status_code_str:>3} - {result['content_length']:7d} - {result['path']}")
        
        if self.results["found_paths"]:
            print(f"\n[*] ALL FOUND PATHS:")
            for result in self.results["found_paths"][:50]:  # Tampilkan max 50
                status_emoji = self.get_status_emoji(result["status_code"])
                status_code_str = str(result["status_code"])
                print(f"  {status_emoji} {status_code_str:>3} - {result['content_length']:7d} - {result['path']}")

def run(session, options):
    """Main function"""
    bruteforcer = DirectoryBruteforcer(options)
    bruteforcer.run()
