import subprocess
import threading
import time
from pathlib import Path
import sys
import re
import select
from queue import Queue
import os
import struct
import hashlib
import hmac
import binascii
import platform

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
    "name": "Python WiFi Bruteforce",
    "description": "WPA/WPA2 bruteforce pure Python tanpa tools eksternal",
    "author": "Lazy Framework",
    "dependencies": ["rich", "tqdm", "cryptography"],
    "platform": "Linux",
    "rank": "Excellent"
}

OPTIONS = {
    "INTERFACE": {
        "required": True,
        "default": "wlan0",
        "description": "Wireless interface (monitor mode akan dibuat otomatis)"
    },
    "BSSID": {
        "required": True,
        "default": "",
        "description": "BSSID target (MAC address router)"
    },
    "ESSID": {
        "required": True,
        "default": "",
        "description": "ESSID/Nama WiFi target"
    },
    "CHANNEL": {
        "required": True,
        "default": "1",
        "description": "Channel WiFi target"
    },
    "WORDLIST": {
        "required": True,
        "default": "/usr/share/wordlists/rockyou.txt",
        "description": "Path ke wordlist password"
    },
    "HANDSHAKE_FILE": {
        "required": False,
        "default": "handshake.pcap",
        "description": "File untuk menyimpan handshake"
    },
    "TIMEOUT": {
        "required": False,
        "default": "30",
        "description": "Timeout deauth attack (detik)"
    },
    "THREADS": {
        "required": False,
        "default": "5",
        "description": "Jumlah threads untuk bruteforce"
    }
}

def detect_environment():
    """
    Detect current execution environment dengan metode yang lebih reliable
    """
    env_info = {
        'is_android': False,
        'is_termux': False,
        'is_smartphone': False,
        'is_linux': False,
        'is_root': os.geteuid() == 0,
        'platform': platform.system()
    }
    
    # Check Android
    android_indicators = [
        '/system/bin/adb',
        '/system/bin/app_process',
        '/system/bin/dalvikvm',
        '/system/build.prop',
        '/system/etc/hosts',
        '/data/data/com.termux',
        '/apex/com.android.runtime',
    ]
    
    # Check environment variables
    android_env_vars = ['ANDROID_ROOT', 'ANDROID_DATA', 'ANDROID_STORAGE']
    for var in android_env_vars:
        if var in os.environ:
            env_info['is_android'] = True
            env_info['is_smartphone'] = True
    
    # Check file indicators
    for indicator in android_indicators:
        if os.path.exists(indicator):
            env_info['is_android'] = True
            env_info['is_smartphone'] = True
            if 'termux' in indicator:
                env_info['is_termux'] = True
    
    # Check Termux specifically
    termux_indicators = [
        '/data/data/com.termux/files/usr',
        '/data/data/com.termux/files/home',
        '/usr/bin/termux-setup-storage'
    ]
    
    for indicator in termux_indicators:
        if os.path.exists(indicator):
            env_info['is_termux'] = True
            env_info['is_android'] = True
            env_info['is_smartphone'] = True
    
    # Check Linux
    if platform.system() == 'Linux':
        env_info['is_linux'] = True
        
        # Check if it's actually Android pretending to be Linux
        if not env_info['is_android']:
            # Additional checks for Android on Linux
            try:
                # Check kernel version for Android indicators
                with open('/proc/version', 'r') as f:
                    kernel_info = f.read().lower()
                    if 'android' in kernel_info or 'lineageos' in kernel_info:
                        env_info['is_android'] = True
                        env_info['is_smartphone'] = True
            except:
                pass
    
    # Check processor architecture for mobile devices
    arch = platform.machine().lower()
    mobile_archs = ['armv7', 'armv8', 'aarch64', 'arm64']
    if any(mobile_arch in arch for mobile_arch in mobile_archs):
        # Additional check to confirm it's actually mobile
        if not os.path.exists('/proc/sys/kernel/osrelease') or 'android' in arch:
            env_info['is_smartphone'] = True
    
    return env_info

def display_environment_warnings(env_info):
    """
    Display appropriate warnings based on detected environment
    """
    if not RICH_AVAILABLE:
        return
    
    warnings = []
    
    if env_info['is_smartphone']:
        if env_info['is_android'] and env_info['is_termux']:
            warnings.append(Panel(
                "📱 [bold yellow]ANDROID TERMUX ENVIRONMENT DETECTED[/bold yellow]\n\n"
                "🚫 [red]CRITICAL LIMITATIONS:[/red]\n"
                "• Monitor mode not available without root access\n"
                "• Packet capture functionality disabled\n"
                "• Deauthentication attacks not possible\n"
                "• Raw socket access restricted by Android security\n\n"
                "✅ [green]AVAILABLE FUNCTIONALITY:[/green]\n"
                "• WPA handshake analysis from existing .pcap files\n"
                "• Password bruteforce with pre-captured handshakes\n"
                "• Cryptographic verification only\n\n"
                "💡 [cyan]WORKFLOW RECOMMENDATION:[/cyan]\n"
                "1. Capture handshake on Linux system with monitor mode\n"
                "2. Transfer .pcap file to Android device\n"
                "3. Use this tool for password analysis",
                title="⚠️ ANDROID PLATFORM ADVISORY",
                border_style="yellow",
                padding=(1, 2)
            ))
        elif env_info['is_android']:
            warnings.append(Panel(
                "📱 [bold yellow]ANDROID ENVIRONMENT DETECTED[/bold yellow]\n\n"
                "This appears to be a standard Android environment.\n"
                "For best results, use Termux application with pkg install python.",
                border_style="yellow",
                padding=(1, 2)
            ))
        else:
            warnings.append(Panel(
                "📱 [bold yellow]MOBILE DEVICE DETECTED[/bold yellow]\n\n"
                "Running on mobile platform with limited capabilities.",
                border_style="yellow",
                padding=(1, 2)
            ))
    
    if not env_info['is_root'] and env_info['is_linux']:
        warnings.append(Panel(
            "🔐 [bold yellow]NON-ROOT EXECUTION DETECTED[/bold yellow]\n\n"
            "Limited functionality available:\n"
            "• Network scanning may fail\n"
            "• Monitor mode operations disabled\n"
            "• Packet capture restricted\n"
            "• Administrative operations unavailable\n\n"
            "Run with 'sudo' for full functionality.",
            border_style="yellow",
            padding=(1, 2)
        ))
    
    if not env_info['is_linux']:
        warnings.append(Panel(
            f"💻 [bold yellow]NON-LINUX PLATFORM: {env_info['platform']}[/bold yellow]\n\n"
            "This tool is optimized for Linux systems.\n"
            "Some features may not work correctly.",
            border_style="yellow",
            padding=(1, 2)
        ))
    
    # Display all warnings
    for warning in warnings:
        console.print(warning)
        time.sleep(1)  # Give user time to read each warning
    
    return len(warnings) > 0

def display_header():
    """Display header panel"""
    if not RICH_AVAILABLE:
        return
    
    header_text = Text()
    header_text.append("📶 ", style="bold red")
    header_text.append("PYTHON WiFi ", style="bold yellow")
    header_text.append("BRUTEFORCE", style="bold cyan")
    
    sub_text = Text()
    sub_text.append("⚡ ", style="bold yellow")
    sub_text.append("Pure Python • No External Tools • Cryptography-based", style="bold white")
    
    header_panel = Panel(
        Align.center(header_text + "\n" + sub_text),
        border_style="bright_blue",
        padding=(1, 2),
        style="bold"
    )
    
    console.print(header_panel)

# ... (Classes WiFiScanner, MonitorModeManager, PCAPWriter, WPAHandshake, HandshakeCapture, WPABruteforce remain the same) ...

class WiFiScanner:
    """Class untuk scanning WiFi networks menggunakan Python pure"""
    
    @staticmethod
    def scan_networks(interface="wlan0"):
        """Scan available WiFi networks menggunakan iwlist"""
        # Check if running without root
        if os.geteuid() != 0:
            if RICH_AVAILABLE:
                console.print("❌ [red]Root access required for network scanning[/red]")
            return []
            
        try:
            result = subprocess.run(
                ['iwlist', interface, 'scan'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            networks = WiFiScanner.parse_iwlist_output(result.stdout)
            return networks
            
        except subprocess.TimeoutExpired:
            if RICH_AVAILABLE:
                console.print("❌ [red]Scan timeout[/red]")
            return []
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"❌ [red]Scan error: {e}[/red]")
            return []
    
    @staticmethod
    def parse_iwlist_output(output):
        """Parse output iwlist"""
        networks = []
        current_network = {}
        
        for line in output.split('\n'):
            line = line.strip()
            
            # ESSID
            if 'ESSID:' in line:
                essid = line.split('ESSID:')[1].strip().strip('"')
                if essid and essid != '""':
                    current_network['essid'] = essid
            
            # MAC Address
            elif 'Address:' in line:
                mac = line.split('Address:')[1].strip()
                current_network['bssid'] = mac
            
            # Channel
            elif 'Channel:' in line:
                channel = line.split('Channel:')[1].strip()
                current_network['channel'] = channel
            
            # Encryption
            elif 'Encryption key:' in line:
                encryption = line.split('Encryption key:')[1].strip()
                current_network['encryption'] = 'WPA' if encryption == 'on' else 'Open'
            
            # Signal level
            elif 'Signal level=' in line:
                signal_match = re.search(r'Signal level=(-?\d+)', line)
                if signal_match:
                    current_network['signal'] = signal_match.group(1)
            
            # End of network block
            elif line == '' and current_network:
                if all(k in current_network for k in ['essid', 'bssid', 'channel']):
                    networks.append(current_network.copy())
                current_network = {}
        
        return networks
    
    @staticmethod
    def display_networks(networks):
        """Display networks in table"""
        if not RICH_AVAILABLE or not networks:
            return
        
        table = Table(
            title="📶 Available WiFi Networks",
            box=box.DOUBLE_EDGE,
            header_style="bold magenta"
        )
        table.add_column("ESSID", style="cyan")
        table.add_column("BSSID", style="yellow")
        table.add_column("Channel", style="green")
        table.add_column("Encryption", style="red")
        table.add_column("Signal", style="white")
        
        for network in networks[:20]:
            table.add_row(
                network.get('essid', 'Unknown'),
                network.get('bssid', 'Unknown'),
                network.get('channel', 'Unknown'),
                network.get('encryption', 'Unknown'),
                network.get('signal', 'Unknown')
            )
        
        console.print(table)

class MonitorModeManager:
    """Class untuk manage monitor mode dengan Python"""
    
    @staticmethod
    def enable_monitor_mode(interface):
        """Enable monitor mode pada interface"""
        # Check root privileges
        if os.geteuid() != 0:
            if RICH_AVAILABLE:
                console.print("❌ [red]Root access required for monitor mode[/red]")
            return None
            
        try:
            # Ciptakan monitor interface baru
            subprocess.run(['sudo', 'iw', 'dev', interface, 'interface', 'add', f'{interface}mon', 'type', 'monitor'], check=True)
            subprocess.run(['sudo', 'ip', 'link', 'set', f'{interface}mon', 'up'], check=True)
            
            if RICH_AVAILABLE:
                console.print(f"✅ [green]Monitor mode enabled on {interface}mon[/green]")
            return f"{interface}mon"
            
        except subprocess.CalledProcessError as e:
            if RICH_AVAILABLE:
                console.print(f"❌ [red]Failed to enable monitor mode: {e}[/red]")
            return None
    
    @staticmethod
    def disable_monitor_mode(interface):
        """Disable monitor mode"""
        if os.geteuid() != 0:
            return False
            
        try:
            if interface.endswith('mon'):
                subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'down'], check=True)
                subprocess.run(['sudo', 'iw', 'dev', interface, 'del'], check=True)
                
                if RICH_AVAILABLE:
                    console.print(f"✅ [green]Monitor mode disabled on {interface}[/green]")
            return True
            
        except subprocess.CalledProcessError as e:
            if RICH_AVAILABLE:
                console.print(f"❌ [red]Failed to disable monitor mode: {e}[/red]")
            return False

# ... (Other classes remain the same as your original code) ...

class WiFiBruteforce:
    """Main class untuk WiFi bruteforce"""
    
    def __init__(self, options):
        self.options = options
        self.interface = options.get("INTERFACE", "wlan0")
        self.bssid = options.get("BSSID", "")
        self.essid = options.get("ESSID", "")
        self.channel = options.get("CHANNEL", "1")
        self.wordlist = options.get("WORDLIST", "")
        self.handshake_file = options.get("HANDSHAKE_FILE", "handshake.pcap")
        self.timeout = int(options.get("TIMEOUT", "30"))
        self.threads = int(options.get("THREADS", "5"))
        
        self.monitor_interface = None
        self.handshake_captured = False
        self.env_info = detect_environment()
        
    def run(self):
        """Main execution flow"""
        display_header()
        
        # Display environment warnings
        has_limitations = display_environment_warnings(self.env_info)
        
        if RICH_AVAILABLE:
            console.print(Panel(
                f"🎯 [bold green]WiFi TARGET CONFIGURATION[/bold green]\n"
                f"📶 Interface: [cyan]{self.interface}[/cyan]\n"
                f"🔗 BSSID: [yellow]{self.bssid}[/yellow]\n"
                f"📡 ESSID: [magenta]{self.essid}[/magenta]\n"
                f"📊 Channel: [green]{self.channel}[/green]\n"
                f"📁 Wordlist: [red]{self.wordlist}[/red]",
                border_style="green",
                padding=(1, 2)
            ))
        
        # If running without root or on smartphone, skip to bruteforce only
        if has_limitations or self.env_info['is_smartphone'] or not self.env_info['is_root']:
            if RICH_AVAILABLE:
                console.print(Panel(
                    "🔓 [bold yellow]LIMITED MODE: BRUTEFORCE ONLY[/bold yellow]\n\n"
                    "Skipping handshake capture phase due to platform restrictions.\n"
                    "Using existing handshake file for password analysis.",
                    border_style="yellow",
                    padding=(1, 2)
                ))
            
            # Directly proceed to bruteforce if handshake file exists
            if os.path.exists(self.handshake_file):
                self.run_bruteforce_only()
            else:
                if RICH_AVAILABLE:
                    console.print(Panel(
                        "❌ [bold red]HANDSHAKE FILE NOT FOUND[/bold red]\n\n"
                        "To use this tool on smartphone/non-root environment:\n\n"
                        "📋 [cyan]RECOMMENDED WORKFLOW:[/cyan]\n"
                        "1. Capture handshake on Linux system with:\n"
                        "   → sudo python3 wifi_bruteforce.py wlan0 TARGET_BSSID\n\n"
                        "2. Transfer .pcap file to this device via:\n"
                        "   → USB cable → Cloud storage → Email → WiFi Direct\n\n"
                        "3. Place handshake.pcap in current directory\n\n"
                        "4. Run this tool again\n\n"
                        "💡 [green]ALTERNATIVE:[/green] Use built-in demo mode",
                        border_style="red",
                        padding=(1, 2)
                    ))
                    
                    # Offer demo mode
                    if RICH_AVAILABLE:
                        console.print("\n" + "="*50)
                        console.print("🎮 [bold cyan]DEMO MODE AVAILABLE[/bold cyan]")
                        console.print("="*50)
                        
                        demo_choice = input("Run in demo mode with sample data? (y/N): ").strip().lower()
                        if demo_choice == 'y':
                            self.run_demo_mode()
            return
        
        # Full functionality for root users on Linux
        # ... (rest of your original run method) ...

    def run_demo_mode(self):
        """Run in demo mode for testing without real handshake"""
        if RICH_AVAILABLE:
            console.print(Panel(
                "🎮 [bold cyan]STARTING DEMO MODE[/bold cyan]\n\n"
                "Using sample data for demonstration purposes.\n"
                "This will simulate a real bruteforce attack.",
                border_style="cyan",
                padding=(1, 2)
            ))
        
        # Create a temporary wordlist for demo
        demo_wordlist = "demo_wordlist.txt"
        with open(demo_wordlist, 'w') as f:
            f.write("password123\n")
            f.write("admin123\n")
            f.write("wifipassword\n")
            f.write("12345678\n")
            f.write("mysupersecretpassword\n")
            f.write("demo1234\n")
            f.write("testpassword\n")
        
        # Run bruteforce with demo data
        bruteforcer = WPABruteforcer(
            "demo_handshake.pcap",  # Non-existent file, will use dummy data
            self.essid or "DemoWiFi",
            demo_wordlist,
            min(self.threads, 2)  # Use fewer threads for demo
        )
        
        found_password = bruteforcer.run_bruteforce()
        
        # Cleanup
        if os.path.exists(demo_wordlist):
            os.remove(demo_wordlist)
        
        if RICH_AVAILABLE:
            if found_password:
                console.print(Panel(
                    f"🎉 [bold green]DEMO COMPLETED - Password found: {found_password}[/bold green]\n"
                    f"📊 Attempts: {bruteforcer.attempts:,}",
                    border_style="bright_green",
                    padding=(1, 2)
                ))
            else:
                console.print(Panel(
                    f"🔍 [yellow]DEMO COMPLETED - No password found[/yellow]\n"
                    f"📊 Attempts: {bruteforcer.attempts:,}",
                    border_style="yellow",
                    padding=(1, 2)
                ))

    def run_bruteforce_only(self):
        """Run only the bruteforce part (for limited environments)"""
        if RICH_AVAILABLE:
            console.print(Panel(
                "🔥 [bold red]STARTING BRUTEFORCE ATTACK...[/bold red]",
                border_style="red",
                padding=(1, 2)
            ))
        
        bruteforcer = WPABruteforcer(
            self.handshake_file, self.essid, self.wordlist, self.threads
        )
        
        found_password = bruteforcer.run_bruteforce()
        
        # Display results
        if found_password:
            if RICH_AVAILABLE:
                console.print("\n" + "="*60)
                console.print(Panel(
                    f"🎉 [bold green]PASSWORD CRACKED SUCCESSFULLY![/bold green]\n\n"
                    f"📶 WiFi: [cyan]{self.essid}[/cyan]\n"
                    f"🔑 Password: [red]{found_password}[/red]\n"
                    f"📊 Attempts: [yellow]{bruteforcer.attempts:,}[/yellow]",
                    title="💎 WIFI CRACKED",
                    border_style="bright_green",
                    padding=(2, 3)
                ))
                console.print("="*60)
        else:
            if RICH_AVAILABLE:
                console.print(Panel(
                    f"❌ [bold red]PASSWORD NOT FOUND[/bold red]\n"
                    f"💡 Tested {bruteforcer.attempts:,} passwords",
                    border_style="red",
                    padding=(1, 2)
                ))

def run(session, options):
    """Main function"""
    # Detect environment first
    env_info = detect_environment()
    
    if not env_info['is_linux'] and not env_info['is_android']:
        if RICH_AVAILABLE:
            console.print(Panel(
                f"❌ [bold red]PLATFORM NOT SUPPORTED: {env_info['platform']}[/bold red]\n\n"
                "This tool is designed for Linux and Android (Termux) platforms.\n"
                "Some features may not work on other operating systems.",
                border_style="red",
                padding=(1, 2)
            ))
        return
    
    # Check minimal dependencies only on Linux
    if env_info['is_linux'] and env_info['is_root']:
        dependencies = ['iw', 'tcpdump']
        missing_deps = []
        
        for dep in dependencies:
            try:
                subprocess.run(['which', dep], capture_output=True, check=True)
            except subprocess.CalledProcessError:
                missing_deps.append(dep)
        
        if missing_deps:
            if RICH_AVAILABLE:
                console.print(Panel(
                    f"❌ [red]Missing dependencies: {', '.join(missing_deps)}[/red]\n"
                    f"💡 Install with: sudo apt-get install {' '.join(missing_deps)}",
                    border_style="red",
                    padding=(1, 2)
                ))
            return
    
    bruteforcer = WiFiBruteforce(options)
    bruteforcer.run()

if __name__ == "__main__":
    # Display initial environment info
    env_info = detect_environment()
    
    if RICH_AVAILABLE:
        console.print(f"🔍 [cyan]Platform: {env_info['platform']}[/cyan]")
        console.print(f"🔍 [cyan]Architecture: {platform.machine()}[/cyan]")
        console.print(f"🔍 [cyan]Root: {env_info['is_root']}[/cyan]")
        console.print(f"🔍 [cyan]Android: {env_info['is_android']}[/cyan]")
        console.print(f"🔍 [cyan]Termux: {env_info['is_termux']}[/cyan]")
        console.print(f"🔍 [cyan]Smartphone: {env_info['is_smartphone']}[/cyan]")
        console.print()
    
    if len(sys.argv) > 1:
        options = {
            "INTERFACE": sys.argv[1] if len(sys.argv) > 1 else "wlan0",
            "BSSID": sys.argv[2] if len(sys.argv) > 2 else "",
            "ESSID": sys.argv[3] if len(sys.argv) > 3 else "",
            "CHANNEL": sys.argv[4] if len(sys.argv) > 4 else "1",
            "WORDLIST": sys.argv[5] if len(sys.argv) > 5 else "/usr/share/wordlists/rockyou.txt",
        }
        run(None, options)
    else:
        print("Usage: python wifi_bruteforce.py <interface> [bssid] [essid] [channel] [wordlist]")
        print("Example: python wifi_bruteforce.py wlan0 00:11:22:33:44:55 MyWiFi 1 passwords.txt")
        print("\n📱 Smartphone/Non-Root Note:")
        print("This tool has limited functionality on smartphones and non-root environments.")
        print("Handshake capture requires root privileges and monitor mode capability.")
        print("Bruteforce analysis can be performed with pre-captured handshake files.")
