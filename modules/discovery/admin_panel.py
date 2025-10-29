#!/usr/bin/env python3

import requests
import threading
from queue import Queue
import time
import sys

# Suppress warnings
import warnings
warnings.filterwarnings("ignore")

try:
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except:
    pass

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False

MODULE_INFO = {
    "name": "discovery/admin_panel_finder",
    "description": "🚀 SUPER Admin Panel Discovery - Find Hidden Admin Interfaces"
}

OPTIONS = {
    "TARGET": {
        "required": True,
        "default": "http://localhost",
        "description": "Target website URL"
    },
    "THREADS": {
        "required": False,
        "default": "15",
        "description": "Number of threads"
    },
    "TIMEOUT": {
        "required": False,
        "default": "8",
        "description": "Request timeout"
    },
    "WORDLIST": {
        "required": False,
        "default": "",
        "description": "Custom wordlist file (optional)"
    }
}

class AdminPanelFinder:
    def __init__(self, options):
        self.options = options
        self.results = []
        self.found_panels = []
        self.lock = threading.Lock()
        self.completed = 0
        self.session = requests.Session()
        self.setup_session()
        
    def setup_session(self):
        """Setup session"""
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        
    def get_admin_wordlist(self):
        """Super comprehensive admin panel wordlist"""
        return [
            # Common admin paths
            "admin", "administrator", "login", "dashboard", "panel", "control", "manager",
            "webadmin", "sysadmin", "adminpanel", "admin_login", "adminarea",
            "admin1", "admin2", "admin4", "admin5", "admin123", "admin888",
            
            # CMS specific
            "wp-admin", "wp-login", "wordpress", "joomla-administrator", 
            "administrator/index.php", "drupal/admin", "magento/admin",
            "prestashop/admin", "opencart/admin", "blog/wp-admin",
            
            # Framework specific
            "laravel/admin", "symfony/admin", "yii/admin", "codeigniter/admin",
            "cakephp/admin", "zend/admin", "spring/admin", "django/admin",
            
            # Server management
            "cpanel", "whm", "webmin", "plesk", "directadmin", "vesta",
            "virtualmin", "portainer", "cockpit", "webmail", "roundcube",
            
            # Database admin
            "phpmyadmin", "mysql", "pma", "dbadmin", "database", "sql",
            "adminer", "phppgadmin", "myadmin", "mysql-admin",
            
            # File management
            "filemanager", "files", "upload", "uploads", "media", "images",
            "assets/admin", "static/admin", "public/admin",
            
            # API admin
            "api/admin", "api/v1/admin", "api/v2/admin", "rest/admin",
            "graphql/admin", "admin/api", "admin/rest",
            
            # Development
            "dev", "development", "test", "staging", "debug", "backend",
            "admin/dev", "admin/test", "admin/debug",
            
            # Regional variations
            "administracion", "administratie", "verwaltung", "amministrazione",
            "gestion", "beheer", "admin_es", "admin_fr", "admin_de",
            
            # Case variations
            "Admin", "ADMIN", "aDmin", "adMin", "admIn", "admiN",
            "Login", "LOGIN", "Dashboard", "DASHBOARD",
            
            # Subdirectories
            "admin/login", "admin/dashboard", "admin/control", "admin/panel",
            "admin/cp", "admin/web", "admin/system", "admin/config",
            "admin/management", "admin/manager", "admin/user",
            "admin/account", "admin/settings", "admin/configuration",
            
            # File extensions
            "admin.php", "admin.html", "admin.aspx", "admin.jsp",
            "admin.cgi", "admin.pl", "admin.py", "admin.rb",
            "admin/login.php", "admin/dashboard.php",
            
            # Backup variations
            "admin.bak", "admin.old", "admin.backup", "admin.save",
            "admin.tar", "admin.zip", "admin.7z",
            
            # Hidden variations
            ".admin", "_admin", "-admin", "admin~", "admin.txt",
            "admin/../admin", "admin/./admin", "admin//admin",
            
            # Parameter based
            "?admin=1", "?debug=1", "?login=true", "?panel=admin",
            "index.php?admin", "home.php?admin", "app.php?admin",
            
            # Port based
            ":2082", ":2083", ":2086", ":2087", ":2095", ":2096",
            ":8080", ":8443", ":8888", ":9000", ":10000",
            
            # Additional common
            "controlpanel", "useradmin", "siteadmin", "serveradmin",
            "webmaster", "operator", "moderator", "root", "superuser",
            "sysop", "config", "setup", "install", "update", "upgrade",
            "maintenance", "tools", "utility", "console", "portal",
            "manager", "management", "superadmin", "master",
            "admin1234", "admin2023", "admin2024", "admin2025",
            "redactor", "publisher", "editor", "author", "contributor",
            "staff", "employee", "operator", "service", "support",
            
            # Mobile admin
            "m/admin", "mobile/admin", "mob/admin", "m/login",
            "mobile/login", "mob/login", "app/admin",
            
            # API endpoints
            "api/v1/login", "api/v2/login", "rest/api/login",
            "graphql/auth", "oauth/admin", "auth/admin",
            
            # Single page apps
            "app", "apps", "application", "applications",
            "webapp", "webapps", "portal/admin", "platform/admin",
            
            # Cloud specific
            "cloud/admin", "aws/admin", "azure/admin", "gcp/admin",
            "kubernetes/admin", "docker/admin", "vmware/admin",
            
            # E-commerce
            "store/admin", "shop/admin", "market/admin", "cart/admin",
            "checkout/admin", "payment/admin", "order/admin",
            
            # Social media
            "social/admin", "community/admin", "forum/admin",
            "chat/admin", "message/admin", "notification/admin",
            
            # Analytics
            "analytics/admin", "stats/admin", "metrics/admin",
            "report/admin", "monitor/admin", "tracking/admin",
            
            # Security
            "security/admin", "firewall/admin", "waf/admin",
            "antivirus/admin", "malware/admin", "scan/admin",
            
            # Backup admin
            "backup/admin", "restore/admin", "recovery/admin",
            "archive/admin", "snapshot/admin",
            
            # Network admin
            "network/admin", "router/admin", "switch/admin",
            "firewall/admin", "proxy/admin", "vpn/admin",
            
            # System admin
            "system/admin", "server/admin", "host/admin",
            "cluster/admin", "node/admin", "instance/admin",
            
            # Database variations
            "mongodb/admin", "redis/admin", "postgres/admin",
            "oracle/admin", "sqlserver/admin", "mariadb/admin",
            
            # CMS variations
            "wordpress/wp-admin", "joomla/administrator",
            "drupal/admin", "magento/admin", "prestashop/admin",
            "opencart/admin", "shopify/admin", "woocommerce/admin",
            
            # Framework variations
            "laravel/admin", "symfony/admin", "yii/admin",
            "codeigniter/admin", "cakephp/admin", "zend/admin",
            "spring/admin", "django/admin", "flask/admin",
            "express/admin", "rails/admin", "aspnet/admin",
            
            # Additional extensions
            "admin.do", "admin.action", "admin.asp", "admin.aspx",
            "admin.jhtml", "admin.json", "admin.xml", "admin.config",
            
            # Authentication pages
            "signin", "signup", "register", "auth", "authentication",
            "oauth", "sso", "login", "logout", "session",
            "password", "reset", "recover", "forgot", "change",
            
            # Final comprehensive list
            "admincp", "admincpanel", "admincontrol", "adminarea",
            "admin_login", "adminlog", "administratorlogin",
            "admin4_account", "admin4_colon", "admin4_login",
            "admin5", "admin5_solar", "admin_account",
            "admin_area", "admin_login", "admin_console",
            "base_login", "bb-admin", "bb-admin/index",
            "bb-admin/login", "blogadmin", "blog/login",
            "cadmins", "ccp14admin", "admin_content",
            "cmsadmin", "content/admin", "control/admin",
            "cp", "cpadmin", "custom/admin", "database/admin",
            "direct/admin", "er/admin", "fileadmin",
            "formsadmin", "irc/admin", "liveadmin",
            "livezilla/admin", "login/admin", "login_db",
            "login1", "loginflat", "login_us", "master/admin",
            "member/admin", "members/admin", "meta/login",
            "modelsearch/admin", "moderator/admin", "moderator/login",
            "my/admin", "navSiteAdmin", "news/admin",
            "newsblog/admin", "nsw/admin/login", "pages/admin",
            "panel-administracion", "panel-administrator",
            "panel", "phppgadmin", "phpSQLiteAdmin",
            "platz_login", "power_user", "project-admins",
            "pureadmin", "radmind", "radmind-1", "rover",
            "server/admin", "server/index", "showlogin",
            "simpleLogin", "simple_admin", "siteadmin/index",
            "siteadmin/login", "sm2012", "sqladmin", "sspanel",
            "staradmin", "sub-login", "superman", "support/login",
            "sysadmin", "sysadmin2", "system_administration",
            "systemadministration", "typo3", "ur-admin",
            "useradmin", "usuario", "utility_login",
            "webadmin", "webadmin/index", "webadmin/login",
            "websql", "wizmysqladmin", "wp-login",
            "wp-login.php", "xlogin", "yonetim", "zc_admin"
        ]
    
    def test_admin_path(self, path):
        """Test a single admin path"""
        try:
            target = self.options.get("TARGET", "").rstrip('/')
            url = f"{target}/{path}"
            
            response = self.session.get(
                url,
                timeout=int(self.options.get("TIMEOUT", 8)),
                allow_redirects=True
            )
            
            # Check if this looks like an admin panel
            is_admin_panel = self.is_admin_panel(response, path)
            
            result = {
                'url': url,
                'path': path,
                'status_code': response.status_code,
                'content_length': len(response.content),
                'title': self.extract_title(response.text),
                'is_admin': is_admin_panel,
                'response_time': response.elapsed.total_seconds()
            }
            
            return result
            
        except Exception:
            return None
    
    def is_admin_panel(self, response, path):
        """Determine if response looks like an admin panel"""
        content = response.text.lower()
        
        # Status code checks
        if response.status_code not in [200, 301, 302]:
            return False
        
        # Keyword checks
        admin_keywords = [
            'admin', 'login', 'password', 'username', 'dashboard',
            'control panel', 'administrator', 'manage', 'settings',
            'configuration', 'user management', 'system',
            'wp-admin', 'cpanel', 'webmin', 'plesk'
        ]
        
        keyword_matches = sum(1 for keyword in admin_keywords if keyword in content)
        
        # Path-based detection
        path_indicators = ['admin', 'login', 'dashboard', 'panel', 'cpanel', 'webmin']
        path_match = any(indicator in path.lower() for indicator in path_indicators)
        
        # Title-based detection
        title_indicators = ['admin', 'login', 'dashboard', 'control panel']
        title = self.extract_title(response.text).lower()
        title_match = any(indicator in title for indicator in title_indicators)
        
        # Combination scoring
        score = 0
        if keyword_matches >= 2: score += 2
        if path_match: score += 1
        if title_match: score += 1
        if 'form' in content and 'password' in content: score += 2
        if response.status_code in [301, 302] and 'login' in path.lower(): score += 1
        
        return score >= 3
    
    def extract_title(self, html):
        """Extract title from HTML"""
        try:
            if '<title>' in html and '</title>' in html:
                start = html.index('<title>') + 7
                end = html.index('</title>')
                return html[start:end].strip()[:100]
        except:
            pass
        return "No Title"
    
    def worker(self, queue):
        """Worker thread"""
        while True:
            try:
                path = queue.get_nowait()
            except:
                break
            
            result = self.test_admin_path(path)
            
            with self.lock:
                self.completed += 1
                
                if result and result['status_code'] != 404:
                    self.results.append(result)
                    if result['is_admin']:
                        self.found_panels.append(result)
                    
                    self.display_result(result)
                
                # Progress update
                if self.completed % 10 == 0:
                    self.update_progress()
            
            queue.task_done()
    
    def update_progress(self):
        """Update progress display"""
        if RICH_AVAILABLE:
            total = len(self.get_admin_wordlist())
            percent = (self.completed / total) * 100
            console.print(f"\r🔍 Scanning: {self.completed}/{total} ({percent:.1f}%) | Found: {len(self.found_panels)} admin panels", end="")
    
    def display_result(self, result):
        """Display interesting results"""
        if not result['is_admin'] and result['status_code'] == 404:
            return
        
        status = result['status_code']
        
        if result['is_admin']:
            style = "bold green"
            emoji = "🎯"
        elif status in [200, 201]:
            style = "blue"
            emoji = "ℹ️"
        elif status in [301, 302]:
            style = "yellow"
            emoji = "🔄"
        elif status == 403:
            style = "red"
            emoji = "🚫"
        else:
            return
        
        if RICH_AVAILABLE:
            console.print(f"\n{emoji} [{style}]{status}[/{style}] {result['path']}")
            if result['is_admin']:
                console.print(f"   🔗 {result['url']}")
                console.print(f"   📝 {result['title']}")
                console.print(f"   📦 {result['content_length']} bytes | ⏱️ {result['response_time']:.2f}s")
    
    def run(self):
        """Main execution"""
        if RICH_AVAILABLE:
            console.print(Panel.fit(
                "[bold red]🚀 SUPER ADMIN PANEL FINDER[/bold red]\n"
                "[bold]Discover Hidden Admin Interfaces & Control Panels[/bold]",
                style="red"
            ))
        
        wordlist = self.get_admin_wordlist()
        
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[bold cyan]Target:[/bold cyan] {self.options.get('TARGET')}\n"
                f"[bold green]Paths:[/bold green] {len(wordlist):,}\n"
                f"[bold yellow]Threads:[/bold yellow] {self.options.get('THREADS')}\n"
                f"[bold blue]Timeout:[/bold blue] {self.options.get('TIMEOUT')}s",
                title="Configuration",
                style="blue"
            ))
        
        # Setup queue
        queue = Queue()
        for path in wordlist:
            queue.put(path)
        
        if RICH_AVAILABLE:
            console.print("[yellow]🔍 Starting admin panel discovery...[/yellow]")
        
        start_time = time.time()
        
        # Start threads
        threads = []
        for i in range(int(self.options.get('THREADS', 15))):
            thread = threading.Thread(target=self.worker, args=(queue,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        queue.join()
        
        # Cleanup
        for thread in threads:
            thread.join(timeout=1)
        
        # Clear progress
        if RICH_AVAILABLE:
            console.print("\r" + " " * 80 + "\r", end="")
        
        elapsed = time.time() - start_time
        if RICH_AVAILABLE:
            console.print(f"[green]✅ Scan completed in {elapsed:.2f}s[/green]")
        
        # Show results
        self.display_final_results()
    
    def display_final_results(self):
        """Display final results"""
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[bold green]🎯 Admin Panels Found: {len(self.found_panels)}[/bold green]\n"
                f"[bold blue]ℹ️  Interesting Paths: {len(self.results)}[/bold blue]\n"
                f"[bold white]📊 Total Tested: {len(self.get_admin_wordlist()):,}[/bold white]",
                title="Discovery Results",
                style="green"
            ))
            
            # Show admin panels
            if self.found_panels:
                console.print(Panel("[bold green]✅ ADMIN PANELS IDENTIFIED[/bold green]", style="green"))
                
                table = Table(show_header=True)
                table.add_column("Status", style="bold")
                table.add_column("Path", style="cyan")
                table.add_column("URL", style="green")
                table.add_column("Title", style="white")
                table.add_column("Size", style="yellow")
                
                for result in self.found_panels:
                    table.add_row(
                        str(result['status_code']),
                        result['path'],
                        result['url'][:40] + '...',
                        result['title'][:30] + '...',
                        f"{result['content_length']} bytes"
                    )
                
                console.print(table)
                
                # Recommendations
                console.print(Panel(
                    "[bold yellow]💡 RECOMMENDATIONS:[/bold yellow]\n"
                    "• Test identified admin panels for authentication bypass\n"
                    "• Check for default credentials\n"
                    "• Look for security misconfigurations\n"
                    "• Report exposed admin interfaces",
                    style="yellow"
                ))

def run(session, options):
    """Main function"""
    finder = AdminPanelFinder(options)
    finder.run()
