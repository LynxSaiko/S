#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import yaml
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tqdm import tqdm
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()

MODULE_INFO = {
    "name": "Directory Brute Force",
    "description": "High-speed directory and file discovery with TQDM progress",
    "author": "Lazy Framework Team",
    "license": "MIT",
    "platform": "Multi",
    "rank": "Excellent",
    "dependencies": ["requests", "pyyaml", "rich", "tqdm"]
}

OPTIONS = {
    "TARGET": {
        "description": "Target URL (http:// or https://)",
        "required": True,
        "default": "https://example.com"
    },
    "WORDLIST": {
        "description": "Path to wordlist YAML file",
        "required": True,
        "default": "wordlists/directories.yaml"
    },
    "THREADS": {
        "description": "Number of concurrent threads (1-100)",
        "required": False,
        "default": "20"
    },
    "TIMEOUT": {
        "description": "Request timeout in seconds",
        "required": False,
        "default": "5"
    },
    "USER_AGENT": {
        "description": "Custom User-Agent string",
        "required": False,
        "default": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }
}

def run(session, options):
    """Main function called by framework"""
    
    # Get options
    target = options.get("TARGET", "").strip().rstrip('/')
    wordlist_path = options.get("WORDLIST", "")
    threads = max(1, min(100, int(options.get("THREADS", 20))))
    timeout = int(options.get("TIMEOUT", 5))
    user_agent = options.get("USER_AGENT", "Mozilla/5.0")
    
    # Validate target
    if not target:
        console.print(Panel(
            "[red]❌ ERROR: TARGET is required[/red]\n\n"
            "[yellow]Usage:[/yellow]\n"
            "  set TARGET https://example.com\n"
            "  set WORDLIST path/to/wordlist.yaml\n"
            "  run",
            title="Configuration Error",
            border_style="red"
        ))
        return
        
    if not target.startswith(('http://', 'https://')):
        console.print(Panel(
            "[red]❌ ERROR: Invalid target URL[/red]\n"
            "URL must start with http:// or https://",
            title="Configuration Error", 
            border_style="red"
        ))
        return
    
    # Load wordlist
    try:
        with open(wordlist_path, 'r', encoding='utf-8') as f:
            wordlist_data = yaml.safe_load(f) or {}
            directories = wordlist_data.get('paths', [])
        
        if not directories:
            console.print(Panel(
                "[red]❌ ERROR: Wordlist is empty[/red]",
                border_style="red"
            ))
            return
            
    except FileNotFoundError:
        console.print(Panel(
            f"[red]❌ ERROR: Wordlist not found[/red]\n{wordlist_path}",
            border_style="red"
        ))
        return
    except Exception as e:
        console.print(Panel(
            f"[red]❌ ERROR: Failed to load wordlist[/red]\n{str(e)}",
            border_style="red"
        ))
        return
    
    # Display startup information
    console.print(Panel(
        f"[bold cyan]Directory Brute Force[/bold cyan]\n\n"
        f"[white]Target:[/white] [yellow]{target}[/yellow]\n"
        f"[white]Wordlist:[/white] [green]{wordlist_path}[/green]\n"
        f"[white]Paths:[/white] [blue]{len(directories):,}[/blue]\n"
        f"[white]Threads:[/white] [magenta]{threads}[/magenta]\n"
        f"[white]Timeout:[/white] [cyan]{timeout}s[/cyan]",
        title="SCAN CONFIGURATION",
        border_style="white",
        padding=(1, 2)
    ))
    
    # Initialize results
    results = []
    found_count = 0
    lock = threading.Lock()
    start_time = time.time()
    
    def check_path(path):
        """Check if a path exists on target"""
        nonlocal found_count
        
        url = f"{target}/{path.lstrip('/')}"
        
        try:
            # Use session with disabled warnings for cleaner output
            session = requests.Session()
            session.verify = False
            
            response = session.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={'User-Agent': user_agent}
            )
            
            # Check if this is an interesting response
            if response.status_code in [200, 301, 302, 403, 401, 500]:
                with lock:
                    result = {
                        'path': path,
                        'status': response.status_code,
                        'url': response.url,
                        'size': len(response.content),
                        'title': extract_title(response.text)
                    }
                    results.append(result)
                    found_count += 1
                    
                    # Display found paths in real-time
                    status_color = {
                        200: "green", 301: "yellow", 302: "yellow",
                        403: "red", 401: "red", 500: "magenta"
                    }.get(response.status_code, "white")
                    
                    console.print(
                        f"[{status_color}]{response.status_code:>3}[/] "
                        f"[dim]|[/dim] {result['size']:>6} bytes [dim]|[/dim] {path}"
                    )
                    
        except requests.exceptions.RequestException:
            pass
        except Exception:
            pass
    
    def extract_title(html):
        """Extract page title from HTML content"""
        import re
        match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    # Start brute force
    console.print(Panel(
        "[bold yellow]🔍 Starting directory brute force...[/bold yellow]",
        border_style="yellow",
        padding=(1, 1)
    ))
    
    # TQDM progress bar
    with tqdm(
        total=len(directories),
        desc="Scanning",
        unit="path",
        position=0,
        leave=True,
        #ncols=80,
        bar_format="{l_bar}{bar:30}{r_bar} {percentage:3.0f}%",
        colour='green'
    ) as pbar:
        
        # Threaded execution
        with ThreadPoolExecutor(max_workers=threads) as executor:
            # Submit all tasks
            futures = {executor.submit(check_path, path): path for path in directories}
            
            # Update progress as tasks complete
            for future in futures:
                future.add_done_callback(lambda x: pbar.update(1))
    
    # Calculate statistics
    scan_time = time.time() - start_time
    requests_per_second = len(directories) / scan_time if scan_time > 0 else 0
    
    # Display results
    console.print()  # Empty line
    
    if results:
        # Create results table
        table = Table(
            title=f"[*] Scan Results - {len(results)} Paths Found",
            box=box.ROUNDED,
            show_header=True,
            header_style="white"
        )
        
        table.add_column("Status", style="bold", width=30, justify="center")
        table.add_column("Size", style="cyan", width=30, justify="right")
        table.add_column("Path", style="green", width=30)
        table.add_column("Title", style="yellow", width=30)
        
        for result in sorted(results, key=lambda x: x['status']):
            status_color = {
                200: "green", 301: "yellow", 302: "yellow",
                403: "red", 401: "red", 500: "magenta"
            }.get(result['status'], "white")
            
            title = result['title']
            if len(title) > 27:
                title = title[:24] + "..."
                
            table.add_row(
                f"[{status_color}]{result['status']}[/{status_color}]",
                f"{result['size']:,}",
                result['path'],
                title or "-"
            )
        
        console.print(table)
        
        # Summary statistics
        status_counts = {}
        for result in results:
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        status_summary = " | ".join([
            f"{code}: {count}" for code, count in sorted(status_counts.items())
        ])
        
        console.print(Panel(
            f"[bold green][*] Scan completed successfully! [*][/bold green]\n\n"
            f"[white]Total paths scanned:[/white] [cyan]{len(directories):,}[/cyan]\n"
            f"[white]Paths found:[/white] [green]{len(results)}[/green]\n"
            f"[white]Status codes:[/white] {status_summary}\n"
            f"[white]Scan duration:[/white] [yellow]{scan_time:.2f}s[/yellow]\n"
            f"[white]Requests per second:[/white] [magenta]{requests_per_second:.1f}[/magenta]\n"
            f"[white]Success rate:[/white] [blue]{(len(results)/len(directories)*100):.2f}%[/blue]",
            border_style="white",
            padding=(1, 2)
        ))
        
    else:
        console.print(Panel(
            f"[yellow]⚠️ No paths discovered[/yellow]\n\n"
            f"Scanned: [cyan]{len(directories):,}[/cyan] paths\n"
            f"Target: [blue]{target}[/blue]\n"
            f"Duration: [yellow]{scan_time:.2f}s[/yellow]\n"
            f"Speed: [magenta]{requests_per_second:.1f} req/s[/magenta]",
            border_style="white",
            padding=(1, 2)
        ))

if __name__ == "__main__":
    console.print(Panel(
        "[bold green][*] Directory Brute Force Module [*][/bold green]\n\n"
        "[yellow]Usage in Lazy Framework:[/yellow]\n"
        "  use scanner/dirbrute\n"
        "  set TARGET https://example.com\n" 
        "  set WORDLIST wordlists/directories.yaml\n"
        "  run\n\n"
        "[dim]Note: SSL warnings are suppressed for cleaner output[/dim]",
        title="MODULE READY",
        border_style="white"
    ))
