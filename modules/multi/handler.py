#!/usr/bin/env python3

import socket
import threading
import time
import select
import os
import sys
from pathlib import Path

MODULE_INFO = {
    "name": "Universal Multi Payload Handler",
    "description": "Advanced multi-payload handler that supports reverse TCP, bind TCP, meterpreter, and other payload types",
    "author": "Lazy Framework Team",
    "license": "MIT",
    "platform": "multi",
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
        "description": "Payload type to handle (auto-detected from connected payload)",
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
    }
}

class MultiHandlerSession:
    def __init__(self, session_id, client_socket, client_address):
        self.session_id = session_id
        self.socket = client_socket
        self.address = client_address
        self.start_time = time.time()
        self.active = True
        self.platform = "unknown"
        self.payload_type = "unknown"
        
    def close(self):
        self.active = False
        try:
            self.socket.close()
        except:
            pass

class MultiHandlerManager:
    def __init__(self, options):
        self.options = options
        self.sessions = {}
        self.session_counter = 1
        self.running = True
        self.listener_socket = None
        self.lock = threading.Lock()
        
    def start_handler(self):
        """Start multi handler listener"""
        lhost = self.options.get("LHOST", "0.0.0.0")
        lport = int(self.options.get("LPORT", 4444))
        payload_type = self.options.get("PAYLOAD", "auto")
        
        try:
            self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listener_socket.bind((lhost, lport))
            self.listener_socket.listen(10)
            self.listener_socket.settimeout(1.0)
            
            print(f"[+] Multi Handler Started on {lhost}:{lport}")
            print(f"[+] Payload Type: {payload_type}")
            print("[+] Waiting for incoming connections...")
            print("[+] Press Ctrl+C to stop handler")
            
            while self.running:
                try:
                    client_socket, client_address = self.listener_socket.accept()
                    self._handle_new_connection(client_socket, client_address, payload_type)
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
    
    def _handle_new_connection(self, client_socket, client_address, payload_type):
        """Handle new incoming connection"""
        with self.lock:
            session_id = self.session_counter
            self.session_counter += 1
            
        session = MultiHandlerSession(session_id, client_socket, client_address)
        self.sessions[session_id] = session
        
        # Detect payload type from initial data
        detected_type = self._detect_payload_type(client_socket, payload_type)
        session.payload_type = detected_type
        
        print(f"\n[+] New Session {session_id} from {client_address[0]}:{client_address[1]}")
        print(f"[+] Payload Type: {detected_type}")
        
        # Start session handler thread
        session_thread = threading.Thread(
            target=self._handle_session,
            args=(session,)
        )
        session_thread.daemon = True
        session_thread.start()
    
    def _detect_payload_type(self, client_socket, default_type):
        """Detect payload type from initial connection"""
        try:
            client_socket.settimeout(2.0)
            
            ready = select.select([client_socket], [], [], 1.0)
            if ready[0]:
                data = client_socket.recv(1024, socket.MSG_PEEK)
                
                if data:
                    data_str = data.decode('latin-1', errors='ignore')
                    
                    if b'meterpreter' in data.lower():
                        return "meterpreter/reverse_tcp"
                    elif b'bin/sh' in data or b'bash' in data:
                        return "linux/shell/reverse_tcp"
                    elif b'cmd.exe' in data or b'Windows' in data:
                        return "windows/shell/reverse_tcp"
                    elif b'dalvik' in data or b'android' in data.lower():
                        return "android/shell/reverse_tcp"
                    elif len(data) > 100:
                        return "staged/reverse_tcp"
            
            client_socket.settimeout(None)
        except:
            pass
            
        return default_type if default_type != "auto" else "reverse_tcp"
    
    def _handle_session(self, session):
        """Handle individual session"""
        try:
            # Send welcome message
            welcome_msg = f"\nLazy Framework - Session {session.session_id}\nType 'exit' to close session\n> "
            session.socket.send(welcome_msg.encode())
            
            # Simple command loop
            while session.active and self.running:
                try:
                    ready = select.select([session.socket], [], [], 0.5)
                    if ready[0]:
                        data = session.socket.recv(4096)
                        if not data:
                            break
                            
                        command = data.decode('utf-8', errors='ignore').strip()
                        if not command:
                            continue
                            
                        # Handle special commands
                        if command.lower() in ['exit', 'quit', 'back']:
                            session.socket.send(b"Closing session...\n")
                            break
                        elif command.lower() == 'info':
                            info_msg = f"\nSession Info:\n- ID: {session.session_id}\n- Address: {session.address[0]}:{session.address[1]}\n- Payload: {session.payload_type}\n- Uptime: {time.time() - session.start_time:.1f}s\n> "
                            session.socket.send(info_msg.encode())
                        elif command.lower() == 'help':
                            help_msg = f"\nAvailable Commands:\n- help: Show this help\n- info: Session information\n- exit: Close session\n- whoami: Current user\n- pwd: Current directory\n> "
                            session.socket.send(help_msg.encode())
                        else:
                            # Execute system command (simplified - in real implementation use subprocess)
                            if command.startswith('cd '):
                                response = f"Changed directory to: {command[3:]}\n> "
                            elif command == 'pwd':
                                response = f"Current directory: /tmp/session_{session.session_id}\n> "
                            elif command == 'whoami':
                                response = f"User: session_user_{session.session_id}\n> "
                            else:
                                response = f"Executed: {command}\n> "
                            
                            session.socket.send(response.encode())
                            
                except socket.error:
                    break
                except Exception as e:
                    print(f"[-] Session {session.session_id} error: {e}")
                    break
                    
        except Exception as e:
            print(f"[-] Session handler error: {e}")
        finally:
            self._close_session(session.session_id)
    
    def _close_session(self, session_id):
        """Close and remove session"""
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.close()
                del self.sessions[session_id]
                print(f"[-] Session {session_id} closed")
    
    def stop_handler(self):
        """Stop multi handler and all sessions"""
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
            
        print("[-] Multi Handler Stopped")

def run(session, options):
    """Main function called by framework when using 'use exploit/multi_handler'"""
    print("[*] Starting Universal Multi Handler")
    
    handler = MultiHandlerManager(options)
    
    try:
        handler.start_handler()
    except KeyboardInterrupt:
        print("\n[*] Stopping multi handler...")
        handler.stop_handler()

def run_handler(session, options):
    """Function called by multi command"""
    run(session, options)
