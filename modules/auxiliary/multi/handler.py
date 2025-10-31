# modules/auxiliary/multi_handler.py
import socket
import threading
import select
import time
import os
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

MODULE_INFO = {
    "name": "Multi Handler",
    "description": "Universal multi-session reverse payload handler (Meterpreter-like)",
    "author": "LazyFramework",
    "rank": "Excellent",
    "dependencies": []
}

OPTIONS = {
    "PAYLOAD": {
        "description": "Payload to handle (e.g. python/meterpreter/reverse_tcp)",
        "required": True,
        "default": "python/meterpreter/reverse_tcp"
    },
    "LHOST": {
        "description": "Listener IP address",
        "required": True,
        "default": "0.0.0.0"
    },
    "LPORT": {
        "description": "Listener port",
        "required": True,
        "default": 4444
    }
}

# === Session Manager ===
class Session:
    def __init__(self, id: int, sock: socket.socket, addr):
        self.id = id
        self.sock = sock
        self.addr = addr
        self.alive = True
        self.info = f"{addr[0]}:{addr[1]}"
        self.thread = None

    def send(self, data: bytes):
        try:
            self.sock.sendall(data)
        except:
            self.alive = False

    def recv(self, size=1024) -> bytes:
        try:
            return self.sock.recv(size)
        except:
            self.alive = False
            return b""

    def close(self):
        self.alive = False
        try:
            self.sock.close()
        except:
            pass

class MultiHandler:
    def __init__(self, lhost: str, lport: int, payload: str):
        self.lhost = lhost
        self.lport = lport
        self.payload = payload
        self.server = None
        self.sessions: Dict[int, Session] = {}
        self.next_id = 1
        self.running = False
        self.listener_thread = None

    def start(self):
        if self.running:
            console.print("[yellow]Handler already running![/yellow]")
            return

        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.lhost, self.lport))
            self.server.listen(5)
            self.running = True

            console.print(f"[bold green][*] Starting multi handler for {self.payload}[/bold green]")
            console.print(f"[bold green][*] Listening on {self.lhost}:{self.lport}[/bold green]")

            self.listener_thread = threading.Thread(target=self._listener, daemon=True)
            self.listener_thread.start()

        except Exception as e:
            console.print(f"[red][!] Failed to start handler: {e}[/red]")

    def _listener(self):
        while self.running:
            try:
                readable, _, _ = select.select([self.server], [], [], 1)
                if not readable:
                    continue
                client_sock, addr = self.server.accept()
                session = Session(self.next_id, client_sock, addr)
                self.next_id += 1
                self.sessions[session.id] = session

                console.print(f"[bold cyan][+] New session {session.id} from {session.info}[/bold cyan]")

                # Start session handler
                session.thread = threading.Thread(target=self._handle_session, args=(session,), daemon=True)
                session.thread.start()

            except:
                break

    def _handle_session(self, session: Session):
        while self.running and session.alive:
            try:
                data = session.recv(1024)
                if not data:
                    break
                # Simulate Meterpreter TLV or raw shell
                if data.startswith(b"session:"):
                    pass  # stageless marker
                elif b"\n" in data:
                    # Echo back for stageless shell
                    session.send(data)
            except:
                break

        session.alive = False
        console.print(f"[bold red][-] Session {session.id} closed[/bold red]")
        self.cleanup_session(session.id)

    def stop(self):
        if not self.running:
            return
        self.running = False
        for sess in list(self.sessions.values()):
            sess.close()
        if self.server:
            self.server.close()
        console.print("[bold yellow][*] Multi handler stopped.[/bold yellow]")

    def list_sessions(self):
        if not self.sessions:
            console.print("[yellow]No active sessions[/yellow]")
            return

        table = Table(title="Active Sessions", box=None)
        table.add_column("ID", style="bold cyan")
        table.add_column("Type", style="green")
        table.add_column("Info", style="white")
        table.add_column("Status", style="yellow")

        for sess in self.sessions.values():
            if sess.alive:
                table.add_row(str(sess.id), "meterpreter", sess.info, "Active")
            else:
                table.add_row(str(sess.id), "meterpreter", sess.info, "Dead")

        console.print(table)

    def interact(self, session_id: int):
        sess = self.sessions.get(session_id)
        if not sess or not sess.alive:
            console.print(f"[red]Session {session_id} not found or dead[/red]")
            return

        console.print(f"[bold green][*] Interacting with session {session_id}[/bold green]")
        console.print("[dim]Type 'background' to return, 'exit' to kill[/dim]")

        try:
            while sess.alive:
                cmd = input(f"meterpreter({session_id}) > ")
                if cmd.strip() == "":
                    continue
                if cmd == "background":
                    console.print("[yellow]Session backgrounded[/yellow]")
                    break
                if cmd in ["exit", "kill"]:
                    sess.send(b"exit\n")
                    sess.close()
                    console.print(f"[red]Session {session_id} killed[/red]")
                    break

                sess.send(cmd.encode() + b"\n")
                time.sleep(0.3)
                response = sess.recv(4096)
                if response:
                    console.print(response.decode(errors='ignore').rstrip())

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Returning to handler...[/yellow]")

    def cleanup_session(self, sid: int):
        if sid in self.sessions:
            del self.sessions[sid]

# === Global Handler Instance ===
_handler: Optional[MultiHandler] = None

def run(session, options):
    global _handler

    payload = options.get("PAYLOAD", "unknown")
    lhost = options.get("LHOST", "0.0.0.0")
    lport = int(options.get("LPORT", 4444))

    if _handler and _handler.running:
        console.print("[yellow]Handler already running. Use 'multi sessions' or 'multi stop'[/yellow]")
        return

    _handler = MultiHandler(lhost, lport, payload)
    _handler.start()

    # === Interactive REPL for Handler ===
    try:
        while _handler.running:
            line = input("multi(handler) > ").strip()
            if not line:
                continue

            parts = line.split()
            cmd = parts[0].lower()

            if cmd == "sessions" or cmd == "list":
                _handler.list_sessions()

            elif cmd == "interact" and len(parts) > 1:
                try:
                    sid = int(parts[1])
                    _handler.interact(sid)
                except:
                    console.print("[red]Invalid session ID[/red]")

            elif cmd == "stop" or cmd == "exit":
                _handler.stop()
                break

            elif cmd == "help":
                console.print("[bold]Multi Handler Commands:[/bold]")
                console.print("  sessions      - List active sessions")
                console.print("  interact <id> - Interact with session")
                console.print("  stop          - Stop handler")
                console.print("  help          - Show this help")

            else:
                console.print(f"[red]Unknown command: {cmd}[/red]")

    except (KeyboardInterrupt, EOFError):
        _handler.stop()
