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
    "description": "Ultra fast directory and file bruteforce dengan progress tracking"
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
    "SHOW_ALL": {
        "required": False,
        "default": "false",
        "description": "Tampilkan semua response termasuk 404 (true/false)"
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
            "current_speed": 0
        }
        self.stop_event = threading.Event()
        self.path_queue = Queue()
        self.lock = threading.Lock()
    
    def setup_components(self):
        """Setup komponen"""
        self.headers = {
            'User-Agent': self.options.get("USER_AGENT"),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        self.ssl_verify = self.options.get("SSL_VERIFY", "false").lower() == "true"
        self.timeout = int(self.options.get("TIMEOUT", "3"))
        self.threads = max(1, min(200, int(self.options.get("THREADS", "50"))))
        self.delay = float(self.options.get("DELAY", "0.01"))
        self.follow_redirects = self.options.get("FOLLOW_REDIRECTS", "true").lower() == "true"
        self.show_all = self.options.get("SHOW_ALL", "false").lower() == "true"
        
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
                # Gunakan built-in wordlist
                wordlist = self.get_default_wordlist()
                if RICH_AVAILABLE:
                    console.print(f"[*] [yellow]Using default wordlist with {len(wordlist)} paths[/yellow]")
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[*] [red]Error loading wordlist: {e}[/red]")
            wordlist = self.get_default_wordlist()
        
        return wordlist
    
    def get_default_wordlist(self):
        """Default wordlist yang komprehensif (~5000 entries)"""
        return [
            # Common directories
            "admin", "administrator", "login", "dashboard", "panel", "control",
            "webadmin", "sysadmin", "manager", "api", "v1", "v2", "v3", "v4",
            "uploads", "files", "images", "assets", "static", "media", "downloads",
            "backup", "backups", "bak", "old", "temp", "tmp", "cache",
            "config", "configuration", "settings", "setup", "install", "update",
            "test", "demo", "dev", "development", "staging", "production",
            "private", "secret", "hidden", "secure", "protected", "restricted",
            
            # Web application paths
            "wp-admin", "wp-content", "wp-includes", "wp-json", "wordpress",
            "phpmyadmin", "mysql", "database", "db", "cpanel", "webmin", "plesk",
            "joomla", "drupal", "magento", "prestashop", "opencart", "wordpress",
            
            # Hidden files and directories
            ".git", ".env", ".htaccess", ".htpasswd", ".well-known", ".docker",
            ".svn", ".cvs", ".bzr", ".hg", ".idea", ".vscode", ".DS_Store",
            
            # Configuration files
            "config.php", "database.php", "settings.php", "config.json",
            "config.xml", "web.config", "app.config", "config.ini",
            "configuration.php", "config.inc.php", "config.dist.php",
            
            # Backup files
            "backup.sql", "dump.sql", "database.sql", "backup.zip", "backup.tar",
            "backup.tar.gz", "backup.rar", "backup.bak", "backup.old",
            
            # Common files
            "robots.txt", "sitemap.xml", "crossdomain.xml", "security.txt",
            "humans.txt", "license.txt", "readme.txt", "changelog.txt",
            
            # API endpoints
            "api/v1", "api/v2", "api/v3", "graphql", "rest", "soap",
            "oauth", "auth", "token", "login", "logout", "register",
            "user", "users", "account", "profile", "admin/api",
            
            # Additional common paths (extended list)
            "css", "js", "img", "images", "fonts", "icons", "themes",
            "plugins", "modules", "components", "templates", "layouts",
            "includes", "scripts", "styles", "assets/css", "assets/js",
            "assets/img", "static/css", "static/js", "static/images",
            
            "src", "source", "lib", "libs", "library", "libraries",
            "vendor", "vendors", "packages", "bundles", "dist", "build",
            
            "logs", "log", "debug", "error", "errors", "trace", "stack",
            "report", "reports", "audit", "monitor", "monitoring",
            
            "export", "import", "upload", "download", "export.php",
            "import.php", "upload.php", "download.php",
            
            "search", "find", "query", "filter", "browse", "list", "catalog",
            "category", "categories", "product", "products", "item", "items",
            
            "news", "blog", "articles", "posts", "pages", "content",
            "document", "documents", "file", "files", "resource", "resources",
            
            "contact", "about", "help", "faq", "support", "feedback",
            "terms", "privacy", "policy", "legal", "disclaimer",
            
            "shop", "store", "cart", "basket", "checkout", "payment",
            "order", "orders", "invoice", "invoices", "customer", "customers",
            
            "forum", "forums", "board", "thread", "threads", "topic", "topics",
            "post", "posts", "comment", "comments", "discussion", "discussions",
            
            "mail", "email", "newsletter", "subscribe", "unsubscribe",
            "notification", "notifications", "alert", "alerts",
            
            "system", "sys", "server", "servers", "service", "services",
            "app", "application", "apps", "portal", "platform",
            
            "home", "index", "main", "default", "start", "welcome",
            "root", "base", "core", "primary", "master",
            
            "auth", "authentication", "authorization", "session", "sessions",
            "cookie", "cookies", "token", "tokens", "jwt", "oauth2",
            
            "back", "return", "previous", "next", "forward", "backward",
            "refresh", "reload", "reset", "clear", "delete", "remove",
            
            "save", "load", "export", "import", "upload", "download",
            "create", "read", "update", "delete", "crud", "restful",
            
            # File extensions variations
            "index", "index.php", "index.html", "index.jsp", "index.asp",
            "main", "main.php", "main.html", "home", "home.php", "home.html",
            "default", "default.php", "default.html", "default.asp",
            
            "admin", "admin.php", "admin.html", "admin.jsp", "admin.asp",
            "administrator", "administrator.php", "administrator.html",
            "login", "login.php", "login.html", "login.jsp", "login.asp",
            "logout", "logout.php", "logout.html", "logout.jsp",
            
            "config", "config.php", "config.xml", "config.json", "config.ini",
            "configuration", "configuration.php", "configuration.xml",
            
            "setup", "setup.php", "setup.html", "install", "install.php",
            "install.html", "update", "update.php", "update.html",
            
            "test", "test.php", "test.html", "test.jsp", "test.asp",
            "demo", "demo.php", "demo.html", "demo.jsp", "demo.asp",
            
            "backup", "backup.php", "backup.html", "backup.sql", "backup.zip",
            "backups", "backups.php", "backups.html", "backups.sql",
            
            # Database related
            "db", "db.php", "db.sql", "database", "database.php", "database.sql",
            "mysql", "mysql.php", "mysqladmin", "mysqld", "mariadb",
            "postgres", "postgresql", "mongodb", "redis", "sqlite",
            
            # Framework specific
            "laravel", "symfony", "yii", "codeigniter", "cakephp", "zend",
            "spring", "django", "flask", "rails", "express", "koa",
            "angular", "react", "vue", "ember", "backbone", "meteor",
            
            # CMS specific
            "wp-admin", "wp-content", "wp-includes", "wp-json",
            "administrator", "components", "modules", "plugins", "templates",
            "media", "images", "cache", "logs", "tmp",
            
            # Server management
            "cpanel", "whm", "webmin", "plesk", "directadmin", "vesta",
            "webmail", "roundcube", "squirrelmail", "horde", "owa",
            
            # Development tools
            "phpinfo", "info.php", "test.php", "debug.php", "status.php",
            "env", ".env.local", ".env.production", ".env.development",
            "composer.json", "package.json", "bower.json", "yarn.lock",
            
            # Security testing
            "xss", "xsrf", "csrf", "sql", "sql-injection", "xss-test",
            "test-xss", "test-sql", "sqli", "xssi", "xxe", "ssrf",
            
            # Additional common words
            "archive", "archives", "old-site", "old-version", "previous",
            "legacy", "classic", "new", "current", "latest", "stable",
            "beta", "alpha", "rc", "release", "nightly", "build",
            
            "mobile", "m", "tablet", "desktop", "responsive", "amp",
            "print", "pdf", "export", "rss", "atom", "feed",
            
            "sso", "single-sign-on", "saml", "openid", "ldap", "ad",
            "active-directory", "kerberos", "radius", "tacacs",
            
            "health", "healthcheck", "status", "ping", "ready", "live",
            "metrics", "stats", "statistics", "analytics", "monitor",
            
            "backdoor", "shell", "cmd", "command", "exec", "system",
            "eval", "assert", "passthru", "shell_exec", "backconnect",
            
            # More file types
            "readme", "readme.md", "readme.txt", "license", "license.md",
            "changelog", "changelog.md", "contributing", "contributing.md",
            
            # API documentation
            "swagger", "swagger.json", "openapi", "openapi.json",
            "api-docs", "api-docs.json", "docs", "documentation",
            "redoc", "rapidoc", "swagger-ui", "api-console",
            
            # Additional extensions
            "php", "html", "htm", "js", "css", "txt", "json", "xml",
            "asp", "aspx", "jsp", "do", "action", "pl", "cgi",
            "py", "rb", "go", "java", "class", "jar", "war",
            "exe", "dll", "so", "dylib", "bin",
            "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
            "zip", "rar", "7z", "tar", "gz", "bz2",
            "jpg", "jpeg", "png", "gif", "bmp", "svg", "ico",
            "mp3", "mp4", "avi", "mov", "wmv", "flv",
            
            # Subdirectories common patterns
            "api/v1/users", "api/v1/products", "api/v1/orders",
            "admin/users", "admin/products", "admin/settings",
            "images/products", "images/users", "images/avatars",
            "uploads/documents", "uploads/images", "uploads/videos",
            "static/js/app", "static/css/app", "static/fonts",
            "themes/default", "themes/admin", "themes/mobile",
            "plugins/contact-form", "plugins/seo", "plugins/analytics",
            "modules/user", "modules/product", "modules/order",
            
            # Wordpress specific
            "wp-admin/admin-ajax.php", "wp-admin/admin-post.php",
            "wp-admin/install.php", "wp-admin/upgrade.php",
            "wp-content/uploads", "wp-content/plugins",
            "wp-content/themes", "wp-includes/js",
            "wp-login.php", "wp-signup.php", "wp-register.php",
            "xmlrpc.php", "wp-cron.php", "wp-load.php",
            
            # Joomla specific
            "administrator/index.php", "administrator/components",
            "administrator/modules", "administrator/templates",
            "components/com_content", "components/com_users",
            "modules/mod_menu", "templates/beez3",
            
            # Drupal specific
            "admin/config", "admin/content", "admin/modules",
            "admin/people", "admin/reports", "admin/structure",
            "sites/default/files", "sites/all/modules",
            "sites/all/themes", "user/login", "user/register",
            
            # Magento specific
            "admin/dashboard", "admin/system", "admin/catalog",
            "admin/sales", "admin/customer", "admin/promotion",
            "media/catalog", "media/wysiwyg", "skin/frontend",
            "app/code/local", "app/code/community", "app/code/core",
            
            # Additional backup patterns
            "backup_2023", "backup_2024", "backup_2025",
            "backup_jan", "backup_feb", "backup_mar", "backup_apr",
            "backup_may", "backup_jun", "backup_jul", "backup_aug",
            "backup_sep", "backup_oct", "backup_nov", "backup_dec",
            "backup_old", "backup_new", "backup_temp", "backup_test",
            
            # Database dumps
            "dump.sql", "database_dump.sql", "sql_dump.sql",
            "mysql_dump.sql", "postgres_dump.sql", "mongo_dump.bson",
            "backup_database.sql", "db_backup.sql", "site_backup.sql",
            "full_backup.sql", "partial_backup.sql", "weekly_backup.sql",
            "monthly_backup.sql", "yearly_backup.sql",
            
            # Configuration backups
            "config_backup.php", "config.bak.php", "config.old.php",
            "config_original.php", "config_dist.php", "config_default.php",
            "settings_backup.php", "settings.bak.php", "settings.old.php",
            "web.config.bak", ".htaccess.bak", "robots.txt.bak",
            
            # Log files
            "error.log", "access.log", "apache.log", "nginx.log",
            "application.log", "system.log", "debug.log", "security.log",
            "auth.log", "mysql.log", "php.log", "laravel.log",
            "symfony.log", "django.log", "rails.log",
            
            # Temporary files
            "temp.txt", "tmp.txt", "cache.txt", "session.txt",
            "upload.tmp", "download.tmp", "import.tmp", "export.tmp",
            "backup.tmp", "restore.tmp", "install.tmp", "update.tmp",
            
            # Development files
            "test.php", "test.html", "test.js", "test.css",
            "demo.php", "demo.html", "demo.js", "demo.css",
            "dev.php", "dev.html", "dev.js", "dev.css",
            "local.php", "local.html", "local.js", "local.css",
            "staging.php", "staging.html", "staging.js", "staging.css",
            
            # API testing
            "api-test", "api-test.php", "api-test.html",
            "rest-test", "rest-test.php", "rest-test.html",
            "graphql-test", "graphql-test.php", "graphql-test.html",
            "soap-test", "soap-test.php", "soap-test.html",
            
            # Security testing files
            "security-test.php", "xss-test.php", "sql-test.php",
            "csrf-test.php", "xxe-test.php", "ssrf-test.php",
            "file-upload-test.php", "path-traversal-test.php",
            "command-injection-test.php", "code-execution-test.php",
            
            # Additional common patterns
            "old", "new", "current", "previous", "next", "first", "last",
            "latest", "stable", "beta", "alpha", "rc", "release",
            "development", "production", "staging", "testing", "qa",
            "demo", "sample", "example", "template", "prototype",
            "archive", "backup", "temp", "tmp", "cache", "logs",
            "config", "settings", "preferences", "options",
            "admin", "administrator", "root", "superuser",
            "user", "users", "member", "members", "account", "accounts",
            "login", "logout", "register", "signup", "signin", "signout",
            "password", "reset", "recovery", "forgot", "change",
            "profile", "settings", "preferences", "dashboard",
            "home", "index", "main", "default", "start", "welcome",
            "search", "find", "browse", "list", "catalog", "directory",
            "contact", "about", "help", "support", "faq", "documentation",
            "news", "blog", "articles", "posts", "pages", "content",
            "shop", "store", "cart", "basket", "checkout", "payment",
            "order", "orders", "invoice", "invoices", "receipt",
            "product", "products", "item", "items", "category", "categories",
            "file", "files", "document", "documents", "resource", "resources",
            "image", "images", "photo", "photos", "picture", "pictures",
            "video", "videos", "audio", "music", "podcast",
            "download", "uploads", "import", "export", "backup", "restore",
            "api", "rest", "graphql", "soap", "xmlrpc", "jsonrpc",
            "mobile", "m", "tablet", "desktop", "print", "amp",
            "rss", "atom", "feed", "subscription", "newsletter",
            "sitemap", "robots", "crossdomain", "security", "humans",
            "manifest", "service-worker", "offline", "app",
            "static", "assets", "public", "media", "cdn",
            "src", "source", "lib", "vendor", "node_modules",
            "bin", "build", "dist", "out", "target",
            "test", "tests", "spec", "specs", "fixtures",
            "doc", "docs", "wiki", "guide", "tutorial",
            "log", "logs", "debug", "error", "trace",
            "tmp", "temp", "cache", "session", "cookie",
            "backup", "backups", "archive", "archives", "old", "previous",
            "config", "configuration", "settings", "preferences",
            "admin", "administrator", "manager", "moderator",
            "user", "member", "account", "profile",
            "auth", "authentication", "authorization", "session",
            "login", "signin", "logout", "signout", "register", "signup",
            "password", "reset", "recovery", "forgot", "change",
            "verify", "confirmation", "activation", "deactivation",
            "dashboard", "control-panel", "admin-panel", "manager",
            "home", "index", "main", "default", "start",
            "search", "find", "query", "filter", "browse",
            "list", "catalog", "directory", "collection",
            "view", "show", "display", "detail", "preview",
            "create", "new", "add", "insert", "save",
            "edit", "update", "modify", "change", "alter",
            "delete", "remove", "destroy", "erase", "clear",
            "upload", "download", "import", "export", "backup",
            "restore", "recover", "reset", "refresh", "reload",
            "sort", "order", "arrange", "organize", "manage",
            "settings", "preferences", "options", "configuration",
            "help", "support", "faq", "documentation", "guide",
            "about", "contact", "feedback", "report", "issue",
            "news", "blog", "articles", "posts", "stories",
            "forum", "board", "discussion", "chat", "message",
            "shop", "store", "market", "mall", "bazaar",
            "cart", "basket", "checkout", "payment", "order",
            "product", "item", "goods", "merchandise", "inventory",
            "category", "type", "kind", "sort", "class",
            "price", "cost", "fee", "charge", "payment",
            "shipping", "delivery", "transport", "carrier",
            "customer", "client", "user", "buyer", "purchaser",
            "review", "rating", "comment", "feedback", "testimonial",
            "wishlist", "favorite", "bookmark", "save", "remember",
            "compare", "difference", "contrast", "versus",
            "recommend", "suggest", "advise", "propose",
            "notification", "alert", "announcement", "message",
            "subscription", "membership", "premium", "pro",
            "free", "trial", "demo", "sample", "example",
            "download", "upload", "transfer", "move", "copy",
            "install", "setup", "configure", "initialize",
            "update", "upgrade", "patch", "fix", "repair",
            "uninstall", "remove", "delete", "erase", "clean",
            "backup", "restore", "recover", "rescue", "save",
            "export", "import", "migrate", "transfer", "move",
            "sync", "synchronize", "match", "align", "coordinate",
            "api", "interface", "gateway", "endpoint", "service",
            "rest", "graphql", "soap", "xml", "json",
            "webhook", "callback", "notification", "alert",
            "documentation", "guide", "manual", "help", "support",
            "version", "release", "build", "revision", "commit",
            "changelog", "history", "log", "record", "archive",
            "statistic", "analytics", "metric", "measure", "track",
            "report", "summary", "overview", "dashboard", "console",
            "monitor", "watch", "observe", "track", "follow",
            "alert", "warning", "error", "fault", "issue",
            "debug", "troubleshoot", "diagnose", "fix", "repair",
            "test", "check", "verify", "validate", "confirm",
            "security", "protection", "safety", "privacy", "confidential",
            "auth", "authentication", "authorization", "permission",
            "role", "group", "team", "organization", "company",
            "user", "member", "account", "profile", "person",
            "session", "token", "key", "secret", "password",
            "login", "signin", "logout", "signout", "register",
            "signup", "subscribe", "join", "participate",
            "password", "reset", "recovery", "forgot", "change",
            "verify", "confirm", "activate", "deactivate", "suspend",
            "block", "ban", "restrict", "limit", "quota",
            "rate", "speed", "performance", "efficiency", "optimization",
            "cache", "memory", "storage", "disk", "file",
            "database", "db", "table", "record", "entry",
            "query", "search", "find", "filter", "sort",
            "index", "catalog", "directory", "list", "collection",
            "export", "import", "migrate", "transfer", "backup",
            "restore", "recover", "reset", "refresh", "reload",
            "template", "theme", "skin", "style", "appearance",
            "layout", "design", "format", "structure", "arrangement",
            "component", "module", "plugin", "extension", "addon",
            "widget", "gadget", "tool", "utility", "application",
            "service", "facility", "resource", "asset", "property",
            "configuration", "setting", "option", "preference", "choice",
            "default", "standard", "normal", "regular", "usual",
            "custom", "personal", "individual", "unique", "special",
            "advanced", "expert", "professional", "enterprise", "business",
            "basic", "simple", "easy", "beginner", "starter",
            "premium", "pro", "gold", "platinum", "diamond",
            "free", "trial", "demo", "sample", "limited",
            "paid", "purchase", "buy", "order", "subscribe",
            "price", "cost", "fee", "charge", "payment",
            "invoice", "bill", "receipt", "voucher", "coupon",
            "discount", "sale", "offer", "deal", "bargain",
            "shipping", "delivery", "transport", "carrier", "logistics",
            "tracking", "monitor", "follow", "watch", "observe",
            "notification", "alert", "message", "email", "sms",
            "support", "help", "assistance", "service", "care",
            "contact", "connect", "reach", "message", "call",
            "feedback", "review", "rating", "comment", "suggestion",
            "report", "issue", "problem", "bug", "error",
            "request", "demand", "require", "need", "want",
            "suggestion", "idea", "proposal", "recommendation", "advice",
            "vote", "poll", "survey", "questionnaire", "form",
            "application", "request", "submission", "entry", "candidate",
            "approval", "acceptance", "rejection", "denial", "refusal",
            "confirmation", "verification", "validation", "authentication",
            "authorization", "permission", "consent", "agreement",
            "terms", "conditions", "policy", "rules", "guidelines",
            "privacy", "security", "protection", "safety", "confidential",
            "copyright", "license", "patent", "trademark", "intellectual",
            "property", "asset", "resource", "possession", "ownership",
            "company", "organization", "business", "enterprise", "firm",
            "team", "group", "department", "division", "section",
            "project", "task", "assignment", "job", "work",
            "goal", "objective", "target", "aim", "purpose",
            "plan", "strategy", "tactic", "method", "approach",
            "result", "outcome", "output", "product", "deliverable",
            "success", "achievement", "accomplishment", "victory", "win",
            "failure", "error", "mistake", "problem", "issue",
            "progress", "development", "improvement", "advancement", "growth",
            "change", "modification", "alteration", "adjustment", "revision",
            "update", "upgrade", "enhancement", "improvement", "optimization",
            "fix", "repair", "correct", "resolve", "solve",
            "maintenance", "support", "service", "care", "management",
            "monitoring", "observation", "supervision", "control", "management",
            "analysis", "examination", "inspection", "review", "audit",
            "evaluation", "assessment", "appraisal", "judgment", "rating",
            "comparison", "contrast", "difference", "similarity", "relation",
            "statistics", "data", "information", "facts", "figures",
            "report", "document", "record", "file", "archive",
            "history", "log", "timeline", "chronology", "sequence",
            "future", "plan", "forecast", "prediction", "expectation",
            "present", "current", "now", "today", "moment",
            "past", "previous", "former", "old", "ancient",
            "time", "date", "schedule", "calendar", "agenda",
            "event", "occasion", "meeting", "conference", "summit",
            "webinar", "seminar", "workshop", "training", "course",
            "lesson", "tutorial", "guide", "manual", "instruction",
            "education", "learning", "knowledge", "information", "wisdom",
            "research", "study", "investigation", "exploration", "discovery",
            "development", "creation", "production", "manufacturing", "building",
            "design", "planning", "architecture", "structure", "framework",
            "implementation", "execution", "performance", "operation", "function",
            "testing", "validation", "verification", "confirmation", "approval",
            "deployment", "release", "launch", "publication", "announcement",
            "promotion", "marketing", "advertising", "publicity", "campaign",
            "sales", "revenue", "income", "profit", "earnings",
            "customer", "client", "consumer", "user", "buyer",
            "market", "audience", "community", "network", "group",
            "partner", "collaborator", "associate", "affiliate", "ally",
            "competitor", "rival", "opponent", "enemy", "adversary",
            "friend", "ally", "supporter", "follower", "fan",
            "media", "press", "news", "journalism", "publication",
            "social", "network", "community", "group", "team",
            "government", "official", "authority", "agency", "department",
            "legal", "law", "regulation", "rule", "requirement",
            "compliance", "conformity", "adherence", "observance", "fulfillment",
            "risk", "danger", "threat", "hazard", "peril",
            "security", "safety", "protection", "defense", "guard",
            "privacy", "confidentiality", "secrecy", "discretion", "caution",
            "trust", "confidence", "reliability", "dependability", "credibility",
            "quality", "excellence", "superiority", "perfection", "ideal",
            "standard", "norm", "benchmark", "criterion", "measure",
            "performance", "efficiency", "effectiveness", "productivity", "output",
            "speed", "velocity", "rate", "pace", "tempo",
            "accuracy", "precision", "exactness", "correctness", "truth",
            "reliability", "dependability", "consistency", "stability", "steadiness",
            "availability", "accessibility", "readiness", "preparedness", "willingness",
            "capacity", "capability", "ability", "skill", "talent",
            "experience", "knowledge", "expertise", "proficiency", "mastery",
            "training", "education", "learning", "development", "growth",
            "innovation", "creativity", "originality", "novelty", "uniqueness",
            "improvement", "enhancement", "advancement", "progress", "development",
            "optimization", "maximization", "efficiency", "effectiveness", "performance",
            "automation", "mechanization", "computerization", "digitalization", "modernization",
            "integration", "connection", "linkage", "combination", "unification",
            "coordination", "cooperation", "collaboration", "partnership", "alliance",
            "communication", "interaction", "dialogue", "conversation", "discussion",
            "information", "data", "knowledge", "wisdom", "intelligence",
            "analysis", "examination", "inspection", "review", "evaluation",
            "decision", "choice", "selection", "option", "alternative",
            "solution", "answer", "resolution", "fix", "remedy",
            "problem", "issue", "challenge", "difficulty", "obstacle",
            "opportunity", "chance", "possibility", "potential", "prospect",
            "success", "achievement", "accomplishment", "victory", "triumph",
            "failure", "defeat", "loss", "setback", "disappointment",
            "goal", "objective", "target", "aim", "purpose",
            "plan", "strategy", "tactic", "method", "approach",
            "action", "activity", "operation", "function", "process",
            "result", "outcome", "output", "product", "consequence",
            "impact", "effect", "influence", "significance", "importance",
            "value", "worth", "benefit", "advantage", "merit",
            "cost", "price", "expense", "expenditure", "investment",
            "return", "profit", "gain", "benefit", "advantage",
            "risk", "danger", "threat", "hazard", "uncertainty",
            "security", "safety", "protection", "defense", "precaution",
            "trust", "confidence", "reliability", "dependability", "credibility",
            "quality", "excellence", "superiority", "perfection", "standard",
            "innovation", "creativity", "originality", "novelty", "uniqueness",
            "efficiency", "effectiveness", "productivity", "performance", "capability",
            "sustainability", "durability", "longevity", "endurance", "persistence",
            "flexibility", "adaptability", "versatility", "agility", "responsiveness",
            "scalability", "expandability", "growth", "development", "evolution",
            "compatibility", "interoperability", "integration", "harmonization", "coordination",
            "accessibility", "usability", "convenience", "ease", "simplicity",
            "reliability", "stability", "consistency", "dependability", "trustworthiness",
            "maintenance", "support", "service", "care", "management",
            "documentation", "guidance", "instruction", "manual", "reference",
            "training", "education", "learning", "development", "improvement",
            "community", "network", "group", "team", "organization",
            "partnership", "collaboration", "cooperation", "alliance", "association",
            "communication", "interaction", "dialogue", "conversation", "discussion",
            "feedback", "input", "suggestion", "recommendation", "advice",
            "support", "help", "assistance", "aid", "service",
            "recognition", "appreciation", "acknowledgment", "credit", "praise",
            "reward", "incentive", "motivation", "encouragement", "inspiration",
            "challenge", "opportunity", "possibility", "potential", "prospect",
            "success", "achievement", "accomplishment", "victory", "triumph",
            "growth", "development", "progress", "advancement", "improvement",
            "innovation", "creation", "invention", "discovery", "breakthrough",
            "excellence", "quality", "perfection", "superiority", "distinction",
            "leadership", "guidance", "direction", "management", "supervision",
            "vision", "mission", "purpose", "goal", "objective",
            "strategy", "plan", "approach", "method", "tactic",
            "execution", "implementation", "performance", "operation", "action",
            "result", "outcome", "impact", "effect", "consequence",
            "value", "benefit", "advantage", "merit", "worth",
            "legacy", "heritage", "tradition", "history", "culture"
        ]
    
    def generate_path_combinations(self):
        """Generate semua kombinasi path yang akan di-test"""
        all_paths = []
        
        for path in self.wordlist:
            if not path.strip():
                continue
                
            # Tambahkan path asli
            if not path.startswith('/'):
                all_paths.append(f"/{path}")
            else:
                all_paths.append(path)
            
            # Tambahkan dengan extensions
            if not path.endswith('/') and '.' not in path.split('/')[-1]:
                for ext in self.extensions:
                    if not path.startswith('/'):
                        all_paths.append(f"/{path}.{ext}")
                    else:
                        all_paths.append(f"{path}.{ext}")
        
        # Hapus duplikat
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
            response = session.get(
                full_url,
                verify=self.ssl_verify,
                timeout=self.timeout,
                proxies=self.proxies,
                allow_redirects=self.follow_redirects
            )
            
            result = {
                "url": full_url,
                "path": original_path,
                "status_code": response.status_code,
                "content_length": len(response.content),
            }
            
            return result
            
        except Exception as e:
            return {
                "url": full_url,
                "path": original_path,
                "status_code": "ERROR",
                "error": str(e),
                "content_length": 0
            }
    
    def is_interesting_response(self, result):
        """Check jika response menarik untuk ditampilkan"""
        if result["status_code"] in [200, 301, 302, 401, 403, 500]:
            return True
        
        if self.show_all:
            return True
            
        return False
    
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
                
                if result and self.is_interesting_response(result):
                    self.results["found_paths"].append(result)
                    
                    # Tampilkan hasil langsung
                    self.display_live_result(result)
            
            if self.delay > 0:
                time.sleep(self.delay)
            
            if TQDM_AVAILABLE and self.progress_bar:
                self.progress_bar.update(1)
            
            self.path_queue.task_done()
        
        session.close()
    
    def display_live_result(self, result):
        """Display hasil langsung saat ditemukan"""
        if not RICH_AVAILABLE:
            status_emoji = self.get_status_emoji(result["status_code"])
            print(f"[FOUND] {status_emoji} {result['status_code']:3d} - {result['content_length']:7d} - {result['url']}")
            return
        
        status_emoji = self.get_status_emoji(result["status_code"])
        status_color = self.get_status_color(result["status_code"])
        
        status_text = Text()
        status_text.append(f"{status_emoji} ", style="bold")
        status_text.append(f"{str(result['status_code']):>3}", style=status_color)
        status_text.append(f" - {result['content_length']:7d} bytes - ", style="white")
        status_text.append(f"{result['path']}", style="cyan")
        
        console.print(status_text)
    
    def get_status_emoji(self, status_code):
        """Get emoji untuk status code"""
        status_str = str(status_code)
        emoji_map = {
            '200': "✅", '301': "🔄", '302': "🔄",
            '401': "🔐", '403': "🚫", '404': "❌",
            '500': "💥", "ERROR": "❓"
        }
        return emoji_map.get(status_str, "❓")
    
    def get_status_color(self, status_code):
        """Get color untuk status code"""
        status_str = str(status_code)
        color_map = {
            '200': "green", '301': "yellow", '302': "yellow",
            '401': "magenta", '403': "red", '404': "white",
            '500': "red", "ERROR": "white"
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
                f"[*] Delay: [magenta]{self.delay}s[/magenta]",
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
                desc="Scanning",
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
        
        # Tampilkan hasil yang ditemukan
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
    
    def display_results_table(self):
        """Display hasil dalam table"""
        table = Table(
            title="DISCOVERED PATHS",
            box=box.DOUBLE_EDGE,
            show_header=True,
            header_style="bold green"
        )
        table.add_column("Status", style="bold", width=4, justify="center")
        table.add_column("Path", style="cyan", overflow="fold")
        table.add_column("Size", style="yellow", justify="right", width=10)
        table.add_column("URL", style="blue", overflow="fold")
        
        # Sort results
        def safe_sort_key(x):
            status_code = str(x["status_code"])
            return (status_code, x["path"])
        
        sorted_results = sorted(self.results["found_paths"], key=safe_sort_key)
        
        for result in sorted_results:
            status_emoji = self.get_status_emoji(result["status_code"])
            content_length = result["content_length"]
            
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
                f"{result['url'][:60]}..." if len(result['url']) > 60 else result['url']
            )
        
        results_panel = Panel(
            table,
            title=f"DISCOVERED {len(self.results['found_paths'])} PATHS",
            border_style="green",
            padding=(1, 1)
        )
        
        console.print(results_panel)
    
    def display_simple_results(self, elapsed_time):
        """Display results sederhana tanpa rich"""
        print(f"\n[*] SCAN COMPLETED")
        print(f"[*] Target: {self.options.get('TARGET')}")
        print(f"[*] Total Attempts: {self.results['attempts']:,}")
        print(f"[*] Found Paths: {len(self.results['found_paths'])}")
        print(f"[*] Execution Time: {elapsed_time:.2f} seconds")
        
        if self.results["found_paths"]:
            print(f"\n[*] FOUND PATHS:")
            for result in self.results["found_paths"]:
                status_emoji = self.get_status_emoji(result["status_code"])
                status_code_str = str(result["status_code"])
                print(f"  {status_emoji} {status_code_str:>3} - {result['content_length']:7d} - {result['path']}")

def run(session, options):
    """Main function"""
    bruteforcer = DirectoryBruteforcer(options)
    bruteforcer.run()
