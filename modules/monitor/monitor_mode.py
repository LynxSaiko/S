#!/usr/bin/env python3

MODULE_INFO = {
    "name": "Monitor Mode Manager",
    "description": "Manage wireless interface monitor mode",
    "author": "Lazy Framework", 
    "license": "MIT",
    "dependencies": ["aircrack-ng"],
    "platform": "Linux",
    "rank": "Normal",
}

OPTIONS = {
    "interface": {
        "description": "Wireless interface name",
        "required": True,
        "default": "wlan0"
    },
    "action": {
        "description": "Action to perform (enable/disable/check)",
        "required": True,
        "default": "check"
    },
    "channel": {
        "description": "Channel for monitor mode",
        "required": False,
        "default": "6"
    }
}

def run(session, options):
    from rich.console import Console
    from rich.panel import Panel
    import subprocess
    import time
    
    console = Console()
    interface = options.get("interface", "wlan0")
    action = options.get("action", "check")
    channel = options.get("channel", "6")
    
    console.print(Panel.fit(
        f"[bold]Monitor Mode Manager[/bold]\n"
        f"Interface: [cyan]{interface}[/cyan]\n"
        f"Action: [yellow]{action}[/yellow]"
    ))
    
    try:
        if action == "check":
            check_monitor_mode(console, interface)
        elif action == "enable":
            enable_monitor_mode(console, interface, channel)
        elif action == "disable":
            disable_monitor_mode(console, interface)
        else:
            console.print("[red]Error: Unknown action. Use enable/disable/check[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def check_monitor_mode(console, interface):
    console.print("[yellow]Checking interface status...[/yellow]")
    
    try:
        # Check if interface exists
        result = subprocess.run(
            ["iwconfig", interface],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            if "Mode:Monitor" in result.stdout:
                console.print(Panel.fit(
                    f"[bold green]✓ {interface} is in monitor mode[/bold green]",
                    border_style="green"
                ))
                
                # Show channel info
                for line in result.stdout.split('\n'):
                    if "Frequency" in line or "Channel" in line:
                        console.print(f"[cyan]{line.strip()}[/cyan]")
            else:
                console.print(Panel.fit(
                    f"[bold yellow]● {interface} is in managed mode[/bold yellow]",
                    border_style="yellow"
                ))
        else:
            console.print(f"[red]Interface {interface} not found[/red]")
            
    except Exception as e:
        console.print(f"[red]Error checking interface: {e}[/red]")

def enable_monitor_mode(console, interface, channel):
    console.print(f"[yellow]Enabling monitor mode on {interface}...[/yellow]")
    
    try:
        # Kill conflicting processes
        console.print("[dim]Killing conflicting processes...[/dim]")
        subprocess.run(["sudo", "airmon-ng", "check", "kill"], capture_output=True)
        
        # Start monitor mode
        console.print("[dim]Starting monitor mode...[/dim]")
        result = subprocess.run(
            ["sudo", "airmon-ng", "start", interface, channel],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Find monitor interface
            monitor_iface = None
            for line in result.stdout.split('\n'):
                if "monitor mode" in line and "enabled" in line:
                    parts = line.split()
                    for part in parts:
                        if "mon" in part:
                            monitor_iface = part
                            break
            
            if monitor_iface:
                console.print(Panel.fit(
                    f"[bold green]✓ Monitor mode enabled![/bold green]\n"
                    f"Interface: [cyan]{monitor_iface}[/cyan]",
                    border_style="green"
                ))
            else:
                console.print("[green]Monitor mode enabled[/green]")
        else:
            console.print("[red]Failed to enable monitor mode[/red]")
            
    except Exception as e:
        console.print(f"[red]Error enabling monitor mode: {e}[/red]")

def disable_monitor_mode(console, interface):
    console.print(f"[yellow]Disabling monitor mode on {interface}...[/yellow]")
    
    try:
        result = subprocess.run(
            ["sudo", "airmon-ng", "stop", interface],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            console.print(Panel.fit(
                f"[bold green]✓ Monitor mode disabled![/bold green]\n"
                f"Interface: [cyan]{interface}[/cyan]",
                border_style="green"
            ))
            
            # Restart network manager
            console.print("[dim]Restarting network manager...[/dim]")
            subprocess.run(["sudo", "systemctl", "restart", "NetworkManager"], capture_output=True)
        else:
            console.print("[red]Failed to disable monitor mode[/red]")
            
    except Exception as e:
        console.print(f"[red]Error disabling monitor mode: {e}[/red]")
