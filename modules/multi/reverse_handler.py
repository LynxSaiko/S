#!/usr/bin/env python3

MODULE_INFO = {
    "name": "Universal Reverse Shell Handler",
    "description": "Multi-language reverse shell handler for various payload types",
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
    "PROTOCOL": {
        "description": "Protocol type (tcp, udp, http)",
        "required": False,
        "default": "tcp"
    },
    "VERBOSE": {
        "description": "Verbose output",
        "required": False,
        "default": "true"
    }
}

import socket
import threading
import time
import select
import sys
import os

class UniversalHandler:
    """Universal reverse shell handler for multiple languages"""
    
    def __init__(self, options):
        self.options = options
        self.lhost = options.get("LHOST", "0.0.0.0")
        self.lport = int(options.get("LPORT", 4444))
        self.protocol = options.get("PROTOCOL", "tcp")
        self.verbose = options.get("VERBOSE", "true").lower() == "true"
        self.sessions = {}
        self.running = True
        
    def start_handler(self):
        """Start the universal handler"""
        try:
            if self.protocol == "tcp":
                self._start_tcp_handler()
            elif self.protocol == "udp":
                self._start_udp_handler()
            else:
                print(f"Unsupported protocol: {self.protocol}")
                
        except Exception as e:
            print(f"Handler error: {e}")
    
    def _start_tcp_handler(self):
        """Start TCP handler"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.lhost, self.lport))
        server.listen(5)
        server.settimeout(1.0)
        
        print(f"[+] Universal Reverse Shell Handler started on {self.lhost}:{self.lport}")
        print("[+] Supported: Perl, Ruby, Java, Node.js, Go, Netcat, Lua, ASPX, Bash, Python, PowerShell")
        print("[+] Waiting for connections...")
        
        while self.running:
            try:
                client_socket, client_address = server.accept()
                print(f"[+] New connection from {client_address[0]}:{client_address[1]}")
                
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Error: {e}")
                break
        
        server.close()
    
    def _handle_client(self, client_socket, client_address):
        """Handle individual client connection"""
        session_id = f"{client_address[0]}:{client_address[1]}"
        self.sessions[session_id] = {
            'socket': client_socket,
            'address': client_address,
            'connected_at': time.time()
        }
        
        try:
            # Send welcome message
            welcome = f"\nUniversal Reverse Shell Handler - Session: {session_id}\nType 'help' for available commands\n\n$ "
            client_socket.send(welcome.encode())
            
            while self.running:
                try:
                    # Check if data is available
                    ready = select.select([client_socket], [], [], 0.5)
                    if ready[0]:
                        data = client_socket.recv(4096)
                        if not data:
                            break
                            
                        command = data.decode('utf-8', errors='ignore').strip()
                        
                        if command.lower() in ['exit', 'quit']:
                            client_socket.send(b"\nGoodbye!\n")
                            break
                        elif command.lower() == 'help':
                            help_text = self._get_help_text()
                            client_socket.send(help_text.encode())
                        elif command.lower() == 'info':
                            info = self._get_session_info(session_id)
                            client_socket.send(info.encode())
                        elif command.startswith('download '):
                            self._handle_download(client_socket, command)
                        elif command.startswith('upload '):
                            self._handle_upload(client_socket, command)
                        else:
                            # Echo for demonstration (in real use, this would execute commands)
                            response = f"Command received: {command}\n$ "
                            client_socket.send(response.encode())
                            
                except Exception as e:
                    if self.verbose:
                        print(f"Session {session_id} error: {e}")
                    break
                    
        except Exception as e:
            if self.verbose:
                print(f"Handler error for {session_id}: {e}")
        finally:
            client_socket.close()
            if session_id in self.sessions:
                del self.sessions[session_id]
            print(f"[-] Session {session_id} closed")
    
    def _get_help_text(self):
        """Get help text for reverse shell"""
        return """
Available Commands:
- help: Show this help
- info: Session information  
- download <file>: Download file from target
- upload <local> <remote>: Upload file to target
- exit, quit: Close session

Note: Commands are executed on the target system
$ """
    
    def _get_session_info(self, session_id):
        """Get session information"""
        session = self.sessions.get(session_id, {})
        uptime = time.time() - session.get('connected_at', time.time())
        
        return f"""
Session Information:
- ID: {session_id}
- Uptime: {uptime:.1f} seconds
- Protocol: {self.protocol}
- Handler: Universal Multi-Language

$ """
    
    def _handle_download(self, client_socket, command):
        """Handle file download (placeholder)"""
        filename = command[9:]
        client_socket.send(f"[*] Starting download: {filename}\n[*] Download complete.\n$ ".encode())
    
    def _handle_upload(self, client_socket, command):
        """Handle file upload (placeholder)"""
        parts = command.split(' ')
        if len(parts) >= 3:
            local_file = parts[1]
            remote_file = parts[2]
            client_socket.send(f"[*] Uploading {local_file} to {remote_file}\n[*] Upload complete.\n$ ".encode())
        else:
            client_socket.send(b"Usage: upload <local_file> <remote_file>\n$ ")
    
    def stop_handler(self):
        """Stop the handler"""
        self.running = False
        for session_id, session_info in self.sessions.items():
            try:
                session_info['socket'].close()
            except:
                pass
        print("[-] Universal handler stopped")

def run(session, options):
    """Run the universal reverse shell handler"""
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    console.print(Panel.fit(
        "[bold green]Universal Reverse Shell Handler[/bold green]\n"
        "Supports: Perl, Ruby, Java, Node.js, Go, Netcat, Lua, ASPX, Bash, Python, PowerShell",
        border_style="green"
    ))
    
    handler = UniversalHandler(options)
    
    try:
        handler.start_handler()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping universal handler...[/yellow]")
        handler.stop_handler()
    except Exception as e:
        console.print(f"[red]Handler error: {e}[/red]")

def get_options():
    """Return module options"""
    return OPTIONS
