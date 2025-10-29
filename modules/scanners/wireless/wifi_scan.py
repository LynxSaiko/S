#!/usr/bin/env python3

MODULE_INFO = {
    "name": "WiFi Network Scanner",
    "description": "Scan for available WiFi networks and gather information",
    "author": "Lazy Framework",
    "license": "MIT",
    "dependencies": ["scapy"],
    "platform": "Linux",
    "rank": "Normal",
}

OPTIONS = {
    "interface": {
        "description": "Wireless interface to use",
        "required": True,
        "default": "wlan0"
    },
    "timeout": {
        "description": "Scan duration in seconds",
        "required": False,
        "default": "10"
    },
    "channel": {
        "description": "Specific channel to scan (0 for all channels)",
        "required": False,
        "default": "0"
    }
}

def run(session, options):
    import subprocess
    import json
    from rich.table import Table
    from rich.console import Console
    
    console = Console()
    interface = options.get("interface", "wlan0")
    timeout = int(options.get("timeout", 10))
    channel = options.get("channel", "0")
    
    console.print(f"[bold green]Starting WiFi scan on interface {interface}...[/bold green]")
    
    try:
        # Method 1: Using iwlist (Linux)
        console.print("[yellow]Method 1: Using iwlist...[/yellow]")
        try:
            result = subprocess.run(
                ["iwlist", interface, "scan"],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                networks = parse_iwlist_output(result.stdout)
                display_networks(console, networks, "iwlist Scan Results")
            else:
                console.print("[red]iwlist scan failed[/red]")
        except Exception as e:
            console.print(f"[red]iwlist error: {e}[/red]")
        
        # Method 2: Using nmcli
        console.print("\n[yellow]Method 2: Using nmcli...[/yellow]")
        try:
            result = subprocess.run(
                ["nmcli", "-f", "SSID,BSSID,MODE,CHAN,FREQ,RATE,SIGNAL,SECURITY", "dev", "wifi"],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                display_nmcli_results(console, result.stdout)
            else:
                console.print("[red]nmcli scan failed[/red]")
        except Exception as e:
            console.print(f"[red]nmcli error: {e}[/red]")
            
    except subprocess.TimeoutExpired:
        console.print("[red]Scan timeout[/red]")
    except Exception as e:
        console.print(f"[red]Scan error: {e}[/red]")

def parse_iwlist_output(output):
    networks = []
    lines = output.split('\n')
    current_net = {}
    
    for line in lines:
        line = line.strip()
        if 'Cell' in line and 'Address' in line:
            if current_net:
                networks.append(current_net)
            current_net = {'mac': line.split('Address: ')[1]}
        elif 'ESSID:' in line:
            current_net['ssid'] = line.split('ESSID:"')[1].rstrip('"')
        elif 'Frequency:' in line:
            freq_parts = line.split('Frequency:')[1].split(' ')[1]
            current_net['channel'] = freq_parts
        elif 'Quality=' in line:
            quality = line.split('Quality=')[1].split(' ')[0]
            current_net['quality'] = quality
        elif 'Encryption key:' in line:
            encrypted = line.split('Encryption key:')[1].strip()
            current_net['encrypted'] = encrypted == 'on'
    
    if current_net:
        networks.append(current_net)
    
    return networks

def display_networks(console, networks, title):
    if not networks:
        console.print("[yellow]No networks found[/yellow]")
        return
    
    table = Table(title=title)
    table.add_column("SSID", style="cyan")
    table.add_column("MAC", style="white")
    table.add_column("Channel", style="green")
    table.add_column("Quality", style="yellow")
    table.add_column("Encrypted", style="red")
    
    for net in networks:
        ssid = net.get('ssid', 'Hidden')
        mac = net.get('mac', 'Unknown')
        channel = net.get('channel', 'Unknown')
        quality = net.get('quality', 'Unknown')
        encrypted = "Yes" if net.get('encrypted') else "No"
        
        table.add_row(ssid, mac, channel, quality, encrypted)
    
    console.print(table)

def display_nmcli_results(console, output):
    lines = output.strip().split('\n')[1:]  # Skip header
    if not lines or len(lines) == 1 and not lines[0].strip():
        console.print("[yellow]No networks found with nmcli[/yellow]")
        return
    
    table = Table(title="nmcli Scan Results")
    table.add_column("SSID", style="cyan")
    table.add_column("BSSID", style="white")
    table.add_column("Mode", style="green")
    table.add_column("Channel", style="yellow")
    table.add_column("Signal", style="red")
    table.add_column("Security", style="magenta")
    
    for line in lines:
        if line.strip():
            parts = line.split()
            if len(parts) >= 8:
                ssid = parts[0] if parts[0] != '--' else 'Hidden'
                bssid = parts[1]
                mode = parts[2]
                channel = parts[3]
                signal = parts[6]
                security = parts[7] if len(parts) > 7 else 'Unknown'
                
                table.add_row(ssid, bssid, mode, channel, signal, security)
    
    console.print(table)
