#!/usr/bin/env python3

MODULE_INFO = {
    "name": "Universal Auto Multi Payload Handler",
    "description": "Advanced multi-payload handler that automatically detects and uses payload modules",
    "author": "Lazy Framework Team",
    "license": "MIT",
    "platform": "multi",
    "arch": "multi",
    "type": "handler",
    "rank": "Excellent",
    "references": [],
    "dependencies": []
}

OPTIONS = {
    "LHOST": {
        "description": "Local IP address to listen on",
        "required": True,
        "default": "0.0.0.0"
    },
    "LPORT": {
        "description": "Local port to listen on",
        "required": True,
        "default": "4444"
    },
    "PAYLOAD": {
        "description": "Payload type to handle (auto-detected from modules/payloads/)",
        "required": False,
        "default": "auto"
    },
    "SESSION_TIMEOUT": {
        "description": "Session timeout in seconds",
        "required": False,
        "default": "300"
    },
    "MAX_SESSIONS": {
        "description": "Maximum number of concurrent sessions",
        "required": False,
        "default": "10"
    },
    "VERBOSE": {
        "description": "Verbose output",
        "required": False,
        "default": "true"
    },
    "AUTO_MIGRATE": {
        "description": "Auto migrate to stable process (Windows)",
        "required": False,
        "default": "false"
    },
    "EXIT_FUNC": {
        "description": "Exit function (process, thread, seh)",
        "required": False,
        "default": "process"
    }
}

import socket
import threading
import time
import select
import os
import sys
import importlib.util
from pathlib import Path

class AutoMultiHandlerSession:
    def __init__(self, session_id, client_socket, client_address, payload_module):
        self.session_id = session_id
        self.socket = client_socket
        self.address = client_address
        self.payload_module = payload_module
        self.payload_name = payload_module['key'].replace('modules/payloads/', '')
        self.platform = payload_module['platform']
        self.start_time = time.time()
        self.active = True
        self.last_activity = time.time()
        
    def close(self):
        self.active = False
        try:
            self.socket.close()
        except:
            pass

class AutoMultiHandlerManager:
    def __init__(self, framework, options):
        self.framework = framework
        self.options = options
        self.sessions = {}
        self.session_counter = 1
        self.running = True
        self.listener_socket = None
        self.lock = threading.Lock()
        self.current_payload_module = None
        
    def start_handler(self):
        """Start auto multi handler listener"""
        lhost = self.options.get("LHOST", "0.0.0.0")
        lport = int(self.options.get("LPORT", 4444))
        payload_type = self.options.get("PAYLOAD", "auto")
        verbose = self.options.get("VERBOSE", "true").lower() == "true"
        
        # Auto-detect payload module
        payload_module = self._auto_detect_payload_module(payload_type)
        if not payload_module:
            print(f"[-] No payload module found for type: {payload_type}")
            return
        
        self.current_payload_module = payload_module
        
        try:
            self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listener_socket.bind((lhost, lport))
            self.listener_socket.listen(10)
            self.listener_socket.settimeout(1.0)
            
            print(f"[+] Auto Multi Handler Started on {lhost}:{lport}")
            print(f"[+] Payload: {payload_module['name']}")
            print(f"[+] Platform: {payload_module['platform']}")
            print(f"[+] Type: {payload_module['type']}")
            print("[+] Waiting for incoming connections...")
            print("[+] Press Ctrl+C to stop handler")
            
            while self.running:
                try:
                    client_socket, client_address = self.listener_socket.accept()
                    if verbose:
                        print(f"[+] New connection from {client_address[0]}:{client_address[1]}")
                    self._handle_new_connection(client_socket, client_address, payload_module)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[-] Listener error: {e}")
                    break
                    
        except Exception as e:
            print(f"[-] Failed to start handler: {e}")
        finally:
            self.stop_handler()
    
    def _auto_detect_payload_module(self, payload_type):
        """Auto-detect payload module from modules/payloads/"""
        payload_modules = self._get_all_payload_modules()
        
        if payload_type == "auto":
            # Return first available payload module
            return payload_modules[0] if payload_modules else None
        
        # Find matching payload module
        for module in payload_modules:
            display_name = module['key'].replace('modules/payloads/', '')
            if (payload_type.lower() in display_name.lower() or 
                payload_type.lower() in module['name'].lower()):
                return module
        
        return None
    
    def _get_all_payload_modules(self):
        """Get all payload modules from modules/payloads/"""
        payload_modules = []
        payloads_dir = Path("modules/payloads")
        
        if not payloads_dir.exists():
            print("[-] modules/payloads/ directory not found")
            return payload_modules
        
        for py_file in payloads_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            try:
                # Import the payload module
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                
                # Get module info
                meta = getattr(mod, "MODULE_INFO", {})
                key = f"modules/payloads/{py_file.relative_to(payloads_dir).with_suffix('')}"
                
                # Determine payload type
                payload_type = self._detect_payload_type(key, meta)
                platform = self._detect_platform(key, meta)
                arch = self._detect_architecture(key, meta)
                
                payload_modules.append({
                    'key': str(key).replace('\\', '/'),
                    'path': py_file,
                    'module': mod,
                    'name': meta.get('description', py_file.stem),
                    'type': payload_type,
                    'platform': platform,
                    'arch': arch,
                    'meta': meta
                })
                
            except Exception as e:
                print(f"[-] Failed to load payload module {py_file}: {e}")
        
        return payload_modules
    
    def _detect_payload_type(self, key, meta):
        """Detect payload type from key and metadata"""
        key_lower = key.lower()
        
        if 'meterpreter' in key_lower:
            return 'meterpreter'
        elif 'shell' in key_lower:
            return 'shell'
        elif 'reverse' in key_lower:
            return 'reverse'
        elif 'bind' in key_lower:
            return 'bind'
        elif 'staged' in key_lower:
            return 'staged'
        elif 'stageless' in key_lower:
            return 'stageless'
        else:
            return 'generic'
    
    def _detect_platform(self, key, meta):
        """Detect platform from key and metadata"""
        platform = meta.get('platform', '').lower()
        if platform:
            return platform.capitalize()
        
        key_lower = key.lower()
        if 'windows' in key_lower:
            return 'Windows'
        elif 'linux' in key_lower:
            return 'Linux'
        elif 'android' in key_lower:
            return 'Android'
        elif 'mac' in key_lower or 'osx' in key_lower:
            return 'macOS'
        else:
            return 'Multi'
    
    def _detect_architecture(self, key, meta):
        """Detect architecture from key and metadata"""
        arch = meta.get('arch', '').lower()
        if arch:
            return arch
        
        key_lower = key.lower()
        if 'x64' in key_lower or 'x86_64' in key_lower:
            return 'x64'
        elif 'x86' in key_lower or 'i386' in key_lower:
            return 'x86'
        elif 'arm64' in key_lower or 'aarch64' in key_lower:
            return 'arm64'
        elif 'arm' in key_lower:
            return 'arm'
        else:
            return 'multi'
    
    def _handle_new_connection(self, client_socket, client_address, payload_module):
        """Handle new incoming connection with auto payload module"""
        with self.lock:
            session_id = self.session_counter
            self.session_counter += 1
            
        session = AutoMultiHandlerSession(session_id, client_socket, client_address, payload_module)
        self.sessions[session_id] = session
        
        print(f"\n[+] New Session {session_id} from {client_address[0]}:{client_address[1]}")
        print(f"[+] Payload: {payload_module['name']}")
        print(f"[+] Platform: {payload_module['platform']}")
        print(f"[+] Type: {payload_module['type']}")
        
        # Start session handler thread using the payload module's handler
        session_thread = threading.Thread(
            target=self._handle_auto_session,
            args=(session, payload_module),
            daemon=True
        )
        session_thread.start()
    
    def _handle_auto_session(self, session, payload_module):
        """Handle session using the payload module's handler function"""
        try:
            # Check if payload module has a run_handler function
            if hasattr(payload_module['module'], 'run_handler'):
                # Use the payload module's handler
                payload_module['module'].run_handler(session, self.options)
            else:
                # Fallback to default handler
                self._default_session_handler(session)
                
        except Exception as e:
            print(f"[-] Auto session handler error: {e}")
        finally:
            self._close_session(session.session_id)
    
    def _default_session_handler(self, session):
        """Default session handler"""
        try:
            # Send welcome message
            welcome_msg = f"Lazy Framework - {session.payload_module['name']}\nSession ID: {session.session_id}\n> "
            session.socket.send(welcome_msg.encode())
            
            # Command loop
            while session.active and self.running:
                try:
                    ready = select.select([session.socket], [], [], 0.5)
                    if ready[0]:
                        data = session.socket.recv(1024)
                        if not data:
                            break
                            
                        command = data.decode('utf-8', errors='ignore').strip()
                        if not command:
                            continue
                            
                        # Handle commands
                        response = self._process_session_command(command, session)
                        session.socket.send(response.encode())
                            
                except socket.error:
                    break
                except Exception as e:
                    print(f"[-] Session {session.session_id} error: {e}")
                    break
                    
        except Exception as e:
            print(f"[-] Default session handler error: {e}")
    
    def _process_session_command(self, command, session):
        """Process session command"""
        cmd_lower = command.lower()
        
        if cmd_lower in ['exit', 'quit']:
            session.active = False
            return "Closing session...\n"
        
        elif cmd_lower == 'info':
            uptime = time.time() - session.start_time
            return f"\nSession Info:\n- ID: {session.session_id}\n- Address: {session.address[0]}:{session.address[1]}\n- Payload: {session.payload_name}\n- Platform: {session.platform}\n- Uptime: {uptime:.1f}s\n> "
        
        elif cmd_lower == 'help':
            return "\nAvailable Commands:\n- help: Show this help\n- info: Session information\n- exit: Close session\n- whoami: Current user\n- pwd: Current directory\n> "
        
        elif cmd_lower == 'whoami':
            return f"user_{session.session_id}\n> "
        
        elif cmd_lower == 'pwd':
            if session.platform == 'Windows':
                return f"C:\\Windows\\Temp\\session_{session.session_id}\n> "
            else:
                return f"/tmp/session_{session.session_id}\n> "
        
        else:
            return f"Command executed: {command}\n> "
    
    def _close_session(self, session_id):
        """Close and remove session"""
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.close()
                del self.sessions[session_id]
                print(f"[-] Session {session_id} closed")
    
    def stop_handler(self):
        """Stop auto multi handler and all sessions"""
        self.running = False
        
        with self.lock:
            for session_id in list(self.sessions.keys()):
                self._close_session(session_id)
        
        if self.listener_socket:
            try:
                self.listener_socket.close()
            except:
                pass
            self.listener_socket = None
            
        print("[-] Auto Multi Handler Stopped")

def run(session, options):
    """Main function called by framework"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    
    console = Console()
    
    console.print(Panel.fit(
        "[bold green]Universal Auto Multi Handler[/bold green]\n"
        "Advanced multi-payload handler with auto-detection",
        border_style="green"
    ))
    
    console.print("[yellow]Scanning modules/payloads/ for available payloads...[/yellow]")
    
    # Create handler manager
    handler = AutoMultiHandlerManager(None, options)
    
    try:
        handler.start_handler()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping auto multi handler...[/yellow]")
        handler.stop_handler()
    except Exception as e:
        console.print(f"[red]Handler error: {e}[/red]")

def list_payloads():
    """List all available payload modules"""
    handler = AutoMultiHandlerManager(None, {})
    payload_modules = handler._get_all_payload_modules()
    
    if not payload_modules:
        print("No payload modules found in modules/payloads/")
        return
    
    console = Console()
    table = Table(title="Available Payload Modules", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan", width=30)
    table.add_column("Type", style="green")
    table.add_column("Platform", style="yellow")
    table.add_column("Arch", style="blue")
    table.add_column("Description", style="white")
    
    for module in payload_modules:
        table.add_row(
            module['name'],
            module['type'],
            module['platform'],
            module['arch'],
            module['meta'].get('description', 'No description')
        )
    
    console.print(table)
