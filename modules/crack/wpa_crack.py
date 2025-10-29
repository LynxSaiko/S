#!/usr/bin/env python3

MODULE_INFO = {
    "name": "WPA Password Cracker", 
    "description": "Crack WPA/WPA2 passwords using wordlist attacks",
    "author": "Lazy Framework",
    "license": "MIT",
    "dependencies": ["hashcat", "aircrack-ng"],
    "platform": "Linux",
    "rank": "Normal",
}

OPTIONS = {
    "handshake_file": {
        "description": "Capture file containing handshake (.pcap or .cap)",
        "required": True,
        "default": ""
    },
    "wordlist": {
        "description": "Path to wordlist file",
        "required": True, 
        "default": "/usr/share/wordlists/rockyou.txt"
    },
    "tool": {
        "description": "Cracking tool to use (aircrack/hashcat)",
        "required": False,
        "default": "aircrack"
    },
    "bssid": {
        "description": "Target BSSID (for aircrack-ng)",
        "required": False,
        "default": ""
    }
}

def run(session, options):
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    import subprocess
    import os
    
    console = Console()
    handshake_file = options.get("handshake_file", "")
    wordlist = options.get("wordlist", "")
    tool = options.get("tool", "aircrack")
    bssid = options.get("bssid", "")
    
    if not handshake_file or not os.path.exists(handshake_file):
        console.print("[red]Error: Handshake file not found[/red]")
        return
    
    if not wordlist or not os.path.exists(wordlist):
        console.print("[red]Error: Wordlist file not found[/red]")
        return
    
    console.print(Panel.fit(
        f"[bold]WPA Password Cracker[/bold]\n"
        f"Handshake: [cyan]{handshake_file}[/cyan]\n"
        f"Wordlist: [yellow]{wordlist}[/yellow]\n"
        f"Tool: [green]{tool}[/green]"
    ))
    
    try:
        if tool.lower() == "aircrack":
            crack_with_aircrack(console, handshake_file, wordlist, bssid)
        elif tool.lower() == "hashcat":
            crack_with_hashcat(console, handshake_file, wordlist)
        else:
            console.print("[red]Error: Unknown tool. Use 'aircrack' or 'hashcat'[/red]")
            
    except Exception as e:
        console.print(f"[red]Cracking error: {e}[/red]")

def crack_with_aircrack(console, handshake_file, wordlist, bssid):
    console.print("[yellow]Starting aircrack-ng attack...[/yellow]")
    
    cmd = ["aircrack-ng", handshake_file, "-w", wordlist]
    if bssid:
        cmd.extend(["-b", bssid])
    
    console.print(f"[cyan]Command: {' '.join(cmd)}[/cyan]")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Cracking password...", total=None)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
        
        if "KEY FOUND" in result.stdout:
            # Extract the key
            for line in result.stdout.split('\n'):
                if "KEY FOUND" in line:
                    key = line.split('KEY FOUND! [ ')[1].split(' ]')[0]
                    console.print(Panel.fit(
                        f"[bold green]✓ PASSWORD CRACKED![/bold green]\n"
                        f"Password: [cyan]{key}[/cyan]",
                        border_style="green"
                    ))
                    break
        else:
            console.print(Panel.fit(
                "[bold red]✗ Password not found in wordlist[/bold red]",
                border_style="red"
            ))
            
    except subprocess.TimeoutExpired:
        console.print("[yellow]Cracking timeout reached[/yellow]")
    except Exception as e:
        console.print(f"[red]Aircrack error: {e}[/red]")

def crack_with_hashcat(console, handshake_file, wordlist):
    console.print("[yellow]Starting hashcat attack...[/yellow]")
    console.print("[yellow]Note: First convert handshake to hashcat format[/yellow]")
    
    # Convert to hashcat format
    hccapx_file = handshake_file + ".hccapx"
    
    try:
        # Use cap2hccapx if available
        convert_cmd = ["cap2hccapx", handshake_file, hccapx_file]
        result = subprocess.run(convert_cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(hccapx_file):
            hashcat_cmd = [
                "hashcat", "-m", "2500", hccapx_file, wordlist,
                "--force", "-O", "-w", "3"
            ]
            
            console.print(f"[cyan]Command: {' '.join(hashcat_cmd)}[/cyan]")
            
            result = subprocess.run(
                hashcat_cmd,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode == 0:
                # Get cracked password
                show_cmd = ["hashcat", "-m", "2500", hccapx_file, "--show"]
                show_result = subprocess.run(show_cmd, capture_output=True, text=True)
                
                if show_result.stdout:
                    console.print(Panel.fit(
                        f"[bold green]✓ PASSWORD CRACKED![/bold green]\n"
                        f"Results:\n[cyan]{show_result.stdout}[/cyan]",
                        border_style="green"
                    ))
                else:
                    console.print("[red]No password found[/red]")
            else:
                console.print("[red]Hashcat execution failed[/red]")
        else:
            console.print("[red]Failed to convert handshake to hashcat format[/red]")
            
    except Exception as e:
        console.print(f"[red]Hashcat error: {e}[/red]")
