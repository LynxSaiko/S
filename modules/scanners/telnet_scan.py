import socket
import threading
import time
from queue import Queue
from pathlib import Path
import sys
import re
import urllib.parse

# Suppress SSL warnings (safe fallback jika ada requests dipakai di modul lain)
try:
    from urllib3.exceptions import InsecureRequestWarning
    import requests
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except Exception:
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

# Rich untuk table / progress
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
    from rich.live import Live
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False

# ---------------- METASPLOIT-STYLE MODULE INFO ----------------
MODULE_INFO = {
    "name": "scanners/telnet/ultrafast",
    "type": "scanners",            # auxiliary / exploit / post / encoder / etc.
    "platform": "multi",            # linux / windows / multi / unix
    "authors": [
        "LynxSaiko"
    ],
    "license": "MIT",
    "rank": "normal",               # excellent / great / good / average / normal / manual / low / unknown
    "description": "Ultra-fast Telnet port scanner with rich progress and results table.",
    "description_detail": (
        "Scanner Telnet ini melakukan probing port Telnet (default: 23) terhadap daftar target "
        "(single, comma-separated, atau CIDR). Menyajikan progress bar interaktif, live status panel, "
        "dan hasil akhir dalam tabel yang rapi. Dirancang untuk assessment jaringan dan discovery cepat."
    ),
    "references": [
        "https://en.wikipedia.org/wiki/Telnet",
    ],
    "dependencies": [
        "rich (optional, untuk tampilan yang lebih baik)",
        "requests (optional, untuk fungsi HTTP jika diperlukan)"
    ],
    # contoh options juga bisa disertakan di MODULE_INFO, tapi framework kamu memakai OPTIONS variabel terpisah.
    "examples": [
        "use scanner/telnet/ultrafast\nset TARGETS 192.168.1.0/28\nset PORT 23\nset THREADS 50\nrun"
    ],
}

# ---------------- OPTIONS (tetap dipertahankan agar kompatibel) ----------------
OPTIONS = {
    "TARGETS": {
        "required": True,
        "default": "127.0.0.1",
        "description": "Target IP / daftar IP (comma-separated) atau CIDR (mis. 192.168.1.0/24)."
    },
    "PORT": {
        "required": False,
        "default": "23",
        "description": "Port Telnet (default: 23)."
    },
    "THREADS": {
        "required": False,
        "default": "50",
        "description": "Jumlah thread paralel (1-200)."
    },
    "TIMEOUT": {
        "required": False,
        "default": "3",
        "description": "Timeout koneksi (detik)."
    },
    "DELAY": {
        "required": False,
        "default": "0.01",
        "description": "Delay antar percobaan (detik)."
    }
}

# ---------------- Telnet scanner implementation ----------------
class TelnetScanner:
    """Class untuk scanning Telnet dengan progress"""

    def __init__(self, targets, port, threads, timeout, delay):
        self.targets = targets
        self.port = port
        self.threads = threads
        self.timeout = timeout
        self.delay = delay
        self.found_hosts = []
        self.results = {
            "scanned": 0,
            "open_ports": 0,
            "start_time": None
        }
        self.stop_event = threading.Event()

    def scan_hosts(self):
        """Scanning hosts with Telnet"""
        targets = self.expand_targets(self.targets)
        total = len(targets)

        # jika tidak ada targets valid
        if total == 0:
            if RICH_AVAILABLE:
                console.print(Panel("❌ Tidak ada target valid ditemukan.", border_style="red"))
            else:
                print("Tidak ada target valid.")
            return []

        if RICH_AVAILABLE:
            progress_columns = [
                TextColumn("{task.description}"),
                BarColumn(bar_width=None),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
            ]

            with Progress(*progress_columns, console=console, transient=False) as progress:
                task = progress.add_task("Scanning hosts...", total=total)
                with Live(self.build_status_panel('-', 0, 0), refresh_per_second=6, console=console) as live:
                    scanned = 0
                    open_ports = 0
                    for target in targets:
                        progress.update(task, description=f"Testing: {target}", advance=1)
                        status_info = self.check_telnet(target)
                        scanned += 1
                        if status_info.get("open"):
                            self.found_hosts.append(status_info)
                            open_ports += 1

                        live.update(self.build_status_panel(target, scanned, open_ports, total))
                        time.sleep(self.delay)

            if self.found_hosts:
                self.display_scan_results()
            else:
                console.print(Panel(
                    "❌ [bold red]No open Telnet ports found![/bold red]\n"
                    f"💡 Tried {scanned} hosts.",
                    border_style="red",
                    padding=(1, 2)
                ))
        else:
            # fallback simple loop tanpa rich
            scanned = 0
            open_ports = 0
            for target in targets:
                status_info = self.check_telnet(target)
                scanned += 1
                if status_info.get("open"):
                    self.found_hosts.append(status_info)
                    open_ports += 1
                print(f"[{scanned}/{total}] {target} -> {'OPEN' if status_info.get('open') else 'closed'}")
                time.sleep(self.delay)

            if self.found_hosts:
                self.display_scan_results()
            else:
                print("No open Telnet ports found. Tried", scanned, "hosts.")

        return self.found_hosts

    def build_status_panel(self, current_target, scanned_count, open_ports_count, total_targets):
        """Build the status panel to display real-time scan info"""
        table = Table.grid(expand=True)
        table.add_column(ratio=3)
        table.add_column(ratio=1, justify="right")
        left = (
            f"🔄 Scanning: [bold]{current_target}[/bold]\n"
            f"🧭 Scanned: [cyan]{scanned_count}/{total_targets}[/cyan]\n"
            f"✅ Open Ports: [green]{open_ports_count}[/green]"
        )
        right = f"Targets: [bold]{total_targets}[/bold]"
        table.add_row(left, right)
        return Panel(table, title="📡 Scan Status", border_style="magenta", padding=(1, 2))

    def check_telnet(self, target):
        """Check status Telnet port"""
        try:
            with socket.create_connection((target, int(self.port)), timeout=self.timeout) as s:
                banner = self.get_banner(s)
                return {
                    "host": target,
                    "open": True,
                    "banner": banner
                }
        except (socket.timeout, ConnectionRefusedError, OSError):
            return {"host": target, "open": False, "banner": ""}

    def get_banner(self, s):
        """Get Telnet banner"""
        try:
            s.settimeout(1)
            banner = s.recv(1024)
            return banner.decode("utf-8", errors="replace").strip()
        except Exception:
            return "(no banner)"

    def expand_targets(self, targets_str):
        """Expand CIDR or list of comma-separated targets"""
        targets = []
        for part in str(targets_str).split(","):
            part = part.strip()
            if not part:
                continue
            if "/" in part:
                # CIDR expansion
                try:
                    import ipaddress
                    network = ipaddress.ip_network(part, strict=False)
                    for ip in network.hosts():
                        targets.append(str(ip))
                except Exception:
                    # skip invalid cidr
                    continue
            else:
                targets.append(part)
        # dedup sambil menjaga urutan
        seen = set(); out = []
        for t in targets:
            if t not in seen:
                seen.add(t); out.append(t)
        return out

    def display_scan_results(self):
        """Display scan results"""
        if not RICH_AVAILABLE:
            # simple text output fallback
            for r in self.found_hosts:
                print(f"{r['host']}:{self.port} -> OPEN  banner: {r.get('banner','(no banner)')}")
            return

        table = Table(
            title="🎯 Telnet Scan Results",
            box=box.DOUBLE_EDGE,
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("Status", style="bold", width=12, overflow="fold")
        table.add_column("Host", style="cyan", overflow="fold", width=30)
        table.add_column("Banner", style="yellow", width=50, overflow="fold")
        table.add_column("Port", style="green", justify="center", width=8)

        for result in self.found_hosts:
            status_emoji = "✅" if result["open"] else "❌"
            banner = result["banner"] if result["banner"] else "(no banner)"
            table.add_row(status_emoji, result["host"], banner, str(self.port))

        results_panel = Panel(
            table,
            title="📊 SCAN COMPLETED",
            border_style="green",
            padding=(1, 1)
        )

        console.print(results_panel)

    def run(self):
        """Run the Telnet scanner"""
        self.results["start_time"] = time.time()
        self.scan_hosts()

# ---------------- module entrypoint ----------------
def run(session, options):
    """Main function to initialize and run the Telnet scanner"""
    scanner = TelnetScanner(
        options.get("TARGETS", OPTIONS["TARGETS"]["default"]),
        options.get("PORT", OPTIONS["PORT"]["default"]),
        int(options.get("THREADS", OPTIONS["THREADS"]["default"])),
        int(options.get("TIMEOUT", OPTIONS["TIMEOUT"]["default"])),
        float(options.get("DELAY", OPTIONS["DELAY"]["default"]))
    )
    scanner.run()
