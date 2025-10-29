#!/usr/bin/env python3

import requests
import threading
import time
import socket
from queue import Queue
from pathlib import Path
from urllib.parse import urlparse
import sys

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import (
        Progress, SpinnerColumn, TextColumn, BarColumn, 
        TaskProgressColumn, TimeRemainingColumn
    )
    from rich.live import Live
    from rich.layout import Layout
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False

MODULE_INFO = {
    "name": "recon/subdomain_scan",
    "description": "🔍 Advanced Subdomain Enumeration with Multi-threading"
}

OPTIONS = {
    "TARGET": {
        "required": True,
        "default": "example.com",
        "description": "Target domain to scan"
    },
    "THREADS": {
        "required": False,
        "default": "20",
        "description": "Number of threads"
    },
    "TIMEOUT": {
        "required": False,
        "default": "3",
        "description": "Request timeout in seconds"
    },
    "WORDLIST": {
        "required": False,
        "default": "",
        "description": "Path to custom wordlist"
    },
    "PROTOCOLS": {
        "required": False,
        "default": "http,https",
        "description": "Protocols to test (http,https)"
    }
}

class SubdomainScanner:
    def __init__(self, options):
        self.options = options
        self.results = []
        self.found_count = 0
        self.tested_count = 0
        self.session = requests.Session()
        self.setup_session()
        
    def setup_session(self):
        """Setup HTTP session"""
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
    
    def load_wordlist(self):
        """Load subdomain wordlist"""
        custom_wordlist = self.options.get('WORDLIST', '').strip()
        
        if custom_wordlist:
            try:
                wordlist_file = Path(custom_wordlist)
                if wordlist_file.is_file():
                    with open(wordlist_file, 'r', encoding='utf-8', errors='ignore') as f:
                        wordlist = [line.strip() for line in f if line.strip()]
                    console.print(f"[green]✅ Loaded {len(wordlist)} subdomains from wordlist[/green]")
                    return wordlist
            except Exception as e:
                console.print(f"[yellow]⚠️ Error loading custom wordlist: {e}[/yellow]")
        
        # Default wordlist
        default_wordlist = [
            'www', 'mail', 'ftp', 'localhost', 'webmail', 'smtp', 'pop', 'ns1', 'webdisk',
            'ns2', 'cpanel', 'whm', 'autodiscover', 'autoconfig', 'm', 'imap', 'test',
            'ns', 'blog', 'pop3', 'dev', 'www2', 'admin', 'forum', 'news', 'vpn',
            'api', 'apps', 'app', 'secure', 'demo', 'portal', 'shop', 'sql', 'search',
            'staging', 'files', 'email', 'web', 'support', 'cdn', 'mysql', 'remote',
            'server', 'new', 'news', 'old', 'lists', 'download', 'dns', 'media',
            'images', 'img', 'video', 'videos', 'music', 'docs', 'doc', 'wiki',
            'login', 'signin', 'signup', 'account', 'accounts', 'billing', 'pay',
            'payment', 'secure', 'ssl', 'cdn', 'cache', 'static', 'assets'
        ]
        console.print(f"[blue]ℹ️ Using default wordlist with {len(default_wordlist)} subdomains[/blue]")
        return default_wordlist
    
    def extract_title(self, html):
        """Extract page title from HTML"""
        import re
        match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        return match.group(1).strip() if match else "No Title"
    
    def check_subdomain(self, subdomain, progress, task_id, protocols):
        """Check if subdomain exists"""
        target = self.options.get('TARGET')
        full_domain = f"{subdomain}.{target}"
        
        for protocol in protocols:
            url = f"{protocol}://{full_domain}"
            try:
                response = self.session.get(
                    url, 
                    timeout=int(self.options.get('TIMEOUT', 3)),
                    allow_redirects=False,
                    allow_redirects=True
                )
                
                # Get IP address
                try:
                    ip = socket.gethostbyname(full_domain)
                except:
                    ip = "Unknown"
                
                result = {
                    'subdomain': full_domain,
                    'protocol': protocol,
                    'status_code': response.status_code,
                    'title': self.extract_title(response.text),
                    'ip': ip,
                    'url': url,
                    'content_length': len(response.content)
                }
                
                return result
                
            except requests.exceptions.RequestException:
                continue
            except Exception:
                continue
        
        return None
    
    def worker(self, queue, progress, task_id, protocols, results):
        """Worker thread for subdomain scanning"""
        while True:
            try:
                subdomain = queue.get_nowait()
            except:
                break
            
            result = self.check_subdomain(subdomain, progress, task_id, protocols)
            
            if result:
                results.append(result)
                self.found_count += 1
                
                # Display found subdomain in real-time
                status_style = "green" if result['status_code'] == 200 else "yellow"
                console.print(
                    f"[green]✅[/green] [cyan]{result['subdomain']}[/cyan] "
                    f"[{status_style}]({result['status_code']})[/{status_style}] "
                    f"[white]{result['title']}[/white]"
                )
            
            self.tested_count += 1
            progress.update(task_id, advance=1)
            queue.task_done()
    
    def display_results_table(self, results):
        """Display results in a beautiful table"""
        if not results:
            console.print(Panel(
                "[yellow]❌ No subdomains found[/yellow]",
                title="Scan Results",
                style="yellow"
            ))
            return
        
        # Summary
        console.print(Panel(
            f"[green]✅ Found {len(results)} subdomains[/green]\n"
            f"[blue]📊 Total tested: {self.tested_count}[/blue]",
            title="Scan Summary",
            style="green"
        ))
        
        # Detailed table
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Subdomain", style="cyan", width=25)
        table.add_column("IP", style="yellow", width=15)
        table.add_column("Protocol", style="green", width=8)
        table.add_column("Status", style="red", width=8)
        table.add_column("Title", style="white", width=30)
        table.add_column("Size", style="blue", width=10)
        
        for result in sorted(results, key=lambda x: x['subdomain']):
            status_style = "green" if result['status_code'] == 200 else "yellow"
            size_kb = result['content_length'] / 1024
            
            table.add_row(
                result['subdomain'],
                result['ip'],
                result['protocol'],
                f"[{status_style}]{result['status_code']}[/{status_style}]",
                result['title'][:27] + "..." if len(result['title']) > 30 else result['title'],
                f"{size_kb:.1f} KB"
            )
        
        console.print(Panel(
            table,
            title="[bold blue]🌐 Discovered Subdomains[/bold blue]",
            style="blue"
        ))
    
    def run_scan(self):
        """Main scanning function"""
        target = self.options.get('TARGET')
        threads = int(self.options.get('THREADS', 20))
        protocols = [p.strip() for p in self.options.get('PROTOCOLS', 'http,https').split(',')]
        
        console.print(Panel(
            f"[bold cyan]🎯 Target:[/bold cyan] {target}\n"
            f"[bold green]🔧 Threads:[/bold green] {threads}\n"
            f"[bold yellow]⚡ Protocols:[/bold yellow] {', '.join(protocols)}\n"
            f"[bold blue]⏱️ Timeout:[/bold blue] {self.options.get('TIMEOUT')}s",
            title="Scan Configuration",
            style="blue"
        ))
        
        # Load wordlist
        wordlist = self.load_wordlist()
        
        if not wordlist:
            console.print("[red]❌ No subdomains to test[/red]")
            return
        
        console.print("[yellow]🚀 Starting subdomain enumeration...[/yellow]")
        
        # Setup progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("•"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TimeRemainingColumn(),
        ) as progress:
            
            main_task = progress.add_task(
                f"🔍 Scanning {len(wordlist)} subdomains...", 
                total=len(wordlist)
            )
            
            # Setup queue and threads
            queue = Queue()
            for subdomain in wordlist:
                queue.put(subdomain)
            
            results = []
            thread_list = []
            
            start_time = time.time()
            
            # Start worker threads
            for i in range(min(threads, len(wordlist))):
                thread = threading.Thread(
                    target=self.worker,
                    args=(queue, progress, main_task, protocols, results)
                )
                thread.daemon = True
                thread.start()
                thread_list.append(thread)
            
            # Wait for completion
            queue.join()
            
            # Wait for threads to finish
            for thread in thread_list:
                thread.join(timeout=1)
            
            elapsed_time = time.time() - start_time
        
        # Display results
        console.print(f"\n[green]✅ Scan completed in {elapsed_time:.2f}s[/green]")
        self.display_results_table(results)

def run(session, options):
    """Main function called by framework"""
    scanner = SubdomainScanner(options)
    scanner.run_scan()
