#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, shlex, importlib.util, re, platform, time, random, itertools, threading, shutil, textwrap
import socket
import select
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

BASE_DIR = Path(__file__).parent
MODULE_DIR, EXAMPLES_DIR, BANNER_DIR = BASE_DIR / "modules", BASE_DIR / "examples", BASE_DIR / "banner"
METADATA_READ_LINES = 120
_loaded_banners = []

# ========== Banner Loader (TETAP SAMA) ==========
def load_banners_from_folder():
    global _loaded_banners
    _loaded_banners = []
    BANNER_DIR.mkdir(parents=True, exist_ok=True)
    for p in sorted(BANNER_DIR.glob("*.txt")):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore").rstrip()
            if text:
                _loaded_banners.append(text + "\n\n")
        except Exception:
            pass
    if not _loaded_banners:
        _loaded_banners = ["\n"]

def colorize_banner(text):
    colors = ['red', 'green', 'yellow', 'blue', 'magenta', 'cyan']
    color = random.choice(colors)
    return f"[{color}]{text}[/{color}]"

def get_random_banner():
    if not _loaded_banners:
        load_banners_from_folder()
    banner = random.choice(_loaded_banners).rstrip("\n")
    try:
        cols = shutil.get_terminal_size(fallback=(80, 24)).columns
    except Exception:
        cols = 80
    lines = banner.splitlines()
    max_len = max((len(line) for line in lines), default=0)
    scale = min(1.0, cols / max_len) if max_len > 0 else 1.0
    new_lines = [line[:int(cols)] for line in lines] if scale < 1.0 else [line.center(cols) for line in lines]
    return colorize_banner("\n".join(new_lines)) + "\n\n"

# ========== Animation (TETAP SAMA) ==========
class SingleLineMarquee:
    def __init__(self, text="Starting the Lazy Framework Console...", text_speed: float = 6.06, spinner_speed: float = 0.06):
        self.text, self.spinner = text, itertools.cycle(['|', '/', '-', '\\'])
        self.alt_text = ''.join(c.lower() if i % 2 == 0 else c.upper() for i, c in enumerate(text))
        self.text_speed, self.spinner_speed = max(0.01, text_speed), max(0.01, spinner_speed)
        self._stop, self._pos, self._thread = threading.Event(), 0, None

    def _compose(self, pos, spin):
        return f"{self.alt_text[:pos] + self.text[pos:]} [{spin}]"

    def _run(self):
        L = len(self.text)
        last_time = time.time()
        while not self._stop.is_set():
            spin = next(self.spinner)
            now = time.time()
            if self._pos < L and (now - last_time) >= self.text_speed:
                self._pos += 1
                last_time = now
            sys.stdout.write('\r' + self._compose(self._pos, spin))
            sys.stdout.flush()
            if self._pos >= L:
                break
            time.sleep(self.spinner_speed)
        sys.stdout.write('\r' + self.text + '\n')
        sys.stdout.flush()

    def start(self):
        if not (self._thread and self._thread.is_alive()):
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
    def wait(self):
        if self._thread: self._thread.join()
    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join()

# ========== Core Framework ==========
@dataclass
class ModuleInstance:
    name: str
    module: Any
    options: Dict[str, Any] = field(default_factory=dict)
    def set_option(self, key, value):
        if key not in self.module.OPTIONS: raise KeyError(f"Unknown option '{key}'")
        self.options[key] = value
    def get_options(self):
        if hasattr(self.module, "OPTIONS"):
            return {k: {"value": self.options.get(k, v.get("default")), **v} for k, v in self.module.OPTIONS.items()}
        return {}

    def run(self, session): return self.module.run(session, self.options)

class Search:
    def __init__(self, modules, metadata): self.modules, self.metadata = modules, metadata
    def search_modules(self, keyword):
        keyword = keyword.lower(); results = []
        for key, meta in self.metadata.items():
            if keyword in key.lower() or keyword in meta.get("description","").lower():
                results.append((key, meta.get("description","(no description)")))
        return results

class LazyFramework:
    def __init__(self):
        self.modules, self.metadata = {}, {}
        self.loaded_module: Optional[ModuleInstance] = None
        self.session = {"user": os.getenv("USER", "unknown")}
        self.scan_modules()
        

    # SCAN HANYA BACA METADATA — TIDAK IMPORT!
    def scan_modules(self):
        self.modules.clear()
        self.metadata.clear()
        self.auto_run_modules()
        valid_extensions = [".py", ".cpp", ".c", ".rb", ".php"]

        for folder, prefix in ((MODULE_DIR, "modules"),):
            for p in folder.rglob("*"):
                if p.is_dir():
                    continue
                if p.suffix not in valid_extensions:
                    continue
                if p.name == "__init__.py":
                    continue
                if "__pycache__" in p.parts or p.suffix in ['.pyc', '.pyo']:
                    continue
                rel = str(p.relative_to(folder)).replace(os.sep, "/")
                key = f"{prefix}/{rel[:-len(p.suffix)]}" if p.suffix else f"{prefix}/{rel}"
                if key.endswith('.py'):
                    key = key[:-3]
                self.modules[key] = p
                self.metadata[key] = self._read_meta(p)
                # HAPUS: self.load_module(key) ← JANGAN IMPORT DI SINI!

     
            self.auto_run_modules()
     
    def auto_run_modules(self):
        if not self.modules:
            console.print("No modules found.")
            return
        console.print(f"Found {len(self.modules)} module(s):")
        for key, path in sorted(self.modules.items()):
            rel = path.relative_to(BASE_DIR)
            if path.suffix == ".py":
                try:
                    compile(path.read_bytes(), str(path), 'exec')
                    console.print(f"  OK  {rel}")
                except Exception as e:
                    console.print(f"  ERR {rel} → {e}")
            else:
                console.print(f"  FILE {rel}")

    def _read_meta(self, path):
        data = {"description": "(No description available)", "options": [], "dependencies": [], "rank": "Normal"}
        try:
            text = "".join(path.open("r", encoding="utf-8", errors="ignore").readlines()[:METADATA_READ_LINES])
            if (m_info := re.search(r"MODULE_INFO\s*=\s*{([^}]+)}", text, re.DOTALL)):
                content = m_info.group(1)
                if (m_desc := re.search(r"(?:'description'|\"description\")\s*:\s*['\"]([^'\"]+)['\"]", content)):
                    data["description"] = m_desc.group(1).strip()
                if (m_rank := re.search(r"(?:'rank'|\"rank\")\s*:\s*['\"]([^'\"]+)['\"]", content)):
                    data["rank"] = m_rank.group(1).strip()
                if (m_deps := re.search(r"(?:'dependencies'|\"dependencies\")\s*:\s*\[([^\]]+)\]", content)):
                    deps_str = m_deps.group(1)
                    dependencies = re.findall(r"['\"]([^'\"]+)['\"]", deps_str)
                    data["dependencies"] = [dep.strip() for dep in dependencies if dep.strip()]
            if (mo := re.search(r"OPTIONS\s*=\s*{([^}]*)}", text, re.DOTALL)):
                data["options"] = re.findall(r"['\"]([A-Za-z0-9_]+)['\"]\s*:", mo.group(1))
        except Exception:
            pass
        return data

    # CEK DEPENDENCIES — pyinstaller via PATH
    def _check_dependencies(self, dependencies: List[str]) -> Dict[str, bool]:
        results = {}
        for dep in dependencies:
            clean_dep = re.split(r'[><=!]', dep)[0].strip().lower()
            if clean_dep == "pyinstaller":
                results[dep] = shutil.which("pyinstaller") is not None
                continue
            import_names = self._generate_import_names(clean_dep)
            success = False
            for name in import_names:
                if importlib.util.find_spec(name) is not None:
                    results[dep] = True
                    success = True
                    break
            if not success:
                results[dep] = False
        return results

    def _generate_import_names(self, package_name: str) -> List[str]:
        names = [package_name]
        if '-' in package_name: names.append(package_name.replace('-', '_'))
        if '.' in package_name: names.append(package_name.replace('.', '_'))
        mappings = {
            'beautifulsoup4': ['bs4'], 'pillow': ['PIL'], 'pyyaml': ['yaml'], 'opencv-python': ['cv2'],
            'requests': ['requests'], 'scapy': ['scapy'], 'cryptography': ['cryptography']
        }
        if package_name in mappings: names.extend(mappings[package_name])
        return list(dict.fromkeys(names))

    # IMPORT HANYA SAAT use
    def cmd_use(self, args):
        if not args:
            console.print("Usage: use <module>", style="bold red")
            return
        user_key = args[0].strip()
        if user_key.lower().endswith('.py'): user_key = user_key[:-3]
        variations = [user_key, f"modules/{user_key}"]
        if user_key.startswith('modules/'): variations.insert(0, user_key); variations.append(user_key[8:])
        key = next((v for v in variations if v in self.modules), None)
        if not key:
            frag = user_key.split('/')[-1].lower()
            candidates = [k for k in self.modules.keys() if frag in k.lower() or k.lower().endswith('/' + frag)]
            if candidates:
                console.print(f"Module '{user_key}' not found. Did you mean:", style="yellow")
                for c in candidates[:8]: console.print("  " + c)
            else:
                console.print(f"Module '{user_key}' not found.", style="red")
            return

        path = self.modules[key]
        try:
            module_dir = path.parent
            pycache_path = module_dir / "__pycache__"
            self._delete_pycache_folder(pycache_path, "Pre-cleanup")

            spec = importlib.util.spec_from_file_location(key.replace('/', '_'), path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            self._delete_pycache_folder(pycache_path, "Post-cleanup")

            meta = getattr(mod, "MODULE_INFO", {})
            dependencies = meta.get("dependencies", [])
            if dependencies:
                dep_results = self._check_dependencies(dependencies)
                missing_deps = [dep for dep, available in dep_results.items() if not available]
                if missing_deps:
                    console.print(f"[yellow]Warning: Missing dependencies for module '{key}':[/yellow]")
                    for dep in missing_deps:
                        console.print(f"  [red]{dep}[/red] - not installed")
                    console.print(f"\n[yellow]Install missing dependencies with: pip install {' '.join(missing_deps)}[/yellow]")

            inst = ModuleInstance(key, mod)
            for k, meta_opt in getattr(mod, "OPTIONS", {}).items():
                if "default" in meta_opt:
                    inst.options[k] = meta_opt["default"]
            self.loaded_module = inst
            console.print(Panel(f"Loaded module [bold]{key}[/bold]", style="green"))
        except Exception as e:
            console.print(f"Load error: {e}", style="bold red")

    def _delete_pycache_folder(self, pycache_path: Path, action_name: str):
        if pycache_path.is_dir():
            try:
                for item in pycache_path.iterdir():
                    if item.is_file(): os.unlink(item)
                os.rmdir(pycache_path)
                console.print(f"[dim]{action_name}: Removed __pycache__ at[/dim] {pycache_path.relative_to(BASE_DIR)}", style="dim green")
            except Exception as e:
                console.print(f"[dim red]Warning[/dim red]: {action_name} failed: {e}", style="dim")

    # RUN: Cek deps sebelum jalankan
    def cmd_run(self, args):
        if not self.loaded_module:
            console.print("No module loaded.", style="red")
            return
        mod = self.loaded_module.module
        meta = getattr(mod, "MODULE_INFO", {})
        dependencies = meta.get("dependencies", [])
        if dependencies:
            dep_results = self._check_dependencies(dependencies)
            missing_deps = [dep for dep, available in dep_results.items() if not available]
            if missing_deps:
                console.print(f"[red]Error: Missing dependencies: {', '.join(missing_deps)}[/red]")
                console.print(f"[yellow]Install with: pip install {' '.join(missing_deps)}[/yellow]")
                return
        try:
            self.loaded_module.run(self.session)
        except Exception as e:
            console.print(f"Run error: {e}", style="red")

    # === SEMUA COMMAND LAIN TETAP SAMA (TAMPILAN TIDAK DIUBAH) ===
    # cmd_help, cmd_payloads, cmd_show, _show_all_modules, _show_modules_by_category, dll
    # → DIBIARKAN 100% SAMA SEPERTI ASLI

    def cmd_help(self, args):
        commands = [
            ("show modules", "Show all available modules"),
            ("show payloads", "Show available payload modules"),
            ("show modules/<category>", "Show modules by category (e.g., discovery, exploit)"),
            ("payloads", "Show available payload modules"),
            ("use <module>", "Load a module by name"),
            ("info", "Show information about the current module"),
            ("options", "Show options for current module"),
            ("set <option> <value>", "Set module option"),
            ("run", "Run current module"),
            ("back", "Unload module"),
            ("search <keyword>", "Search modules"),
            ("scan", "Rescan modules"),
            ("banner reload|list", "Reload/list banner files"),
            ("multi <payload>", "Start multi handler for payload"),
            ("multi sessions", "Show active multi handler sessions"),
            ("multi stop", "Stop multi handler"),
            ("cd <dir>", "Change working directory"),
            ("ls", "List current directory"),
            ("clear", "Clear terminal screen"),
            ("exit / quit", "Exit the program"),
        ]
        table = Table(title="Core Commands", box=box.SIMPLE_HEAVY)
        table.add_column("Command", style="bold white")
        table.add_column("Description", style="white")
        for cmd, desc in commands:
            table.add_row(cmd, desc)
        panel = Panel(table, title="", border_style="white", expand=True)
        console.print(panel)

    def cmd_payloads(self, args):
        payload_modules = {}
        for key, path in self.modules.items():
            if not key.startswith("modules/"): continue
            parts = key.split('/')
            if not (("payload" in parts) or ("payloads" in parts)): continue
            payload_modules[key] = self.metadata.get(key, {})
        if not payload_modules:
            console.print("No payload modules found under 'modules/'.", style="yellow")
            return
        table = Table(title="Available Payloads", box=box.SIMPLE_HEAVY, expand=True)
        table.add_column("Payload", style="bold cyan", width=30)
        table.add_column("Type", style="yellow", width=15)
        table.add_column("Platform", style="green", width=12)
        table.add_column("Arch", style="magenta", width=10)
        table.add_column("Rank", style="red", width=8)
        table.add_column("Description", style="white", min_width=20)
        for key, meta in sorted(payload_modules.items()):
            display_name = key[len("modules/"):]
            kl = key.lower()
            payload_type = "unknown"
            if "meterpreter" in kl: payload_type = "meterpreter"
            elif "shell" in kl: payload_type = "shell"
            elif "reverse" in kl: payload_type = "reverse"
            elif "bind" in kl: payload_type = "bind"
            elif "staged" in kl: payload_type = "staged"
            elif "stageless" in kl: payload_type = "stageless"
            platform_info = meta.get("platform", "multi")
            if isinstance(platform_info, str): platform_info = platform_info.capitalize()
            arch = meta.get("arch", "multi")
            rank = meta.get("rank", "Normal")
            description = meta.get("description", "No description available")
            table.add_row(display_name, payload_type, str(platform_info), str(arch), str(rank), description)
        total_payloads = len(payload_modules)
        payload_types = {}
        platforms = {}
        for key in payload_modules.keys():
            kl = key.lower()
            if "/windows/" in kl: platforms["Windows"] = platforms.get("Windows", 0) + 1
            elif "/linux/" in kl: platforms["Linux"] = platforms.get("Linux", 0) + 1
            elif "/android/" in kl: platforms["Android"] = platforms.get("Android", 0) + 1
            elif "/mac" in kl or "/osx" in kl: platforms["macOS"] = platforms.get("macOS", 0) + 1
            else: platforms["Multi"] = platforms.get("Multi", 0) + 1
            if "reverse" in kl: payload_types["Reverse"] = payload_types.get("Reverse", 0) + 1
            elif "bind" in kl: payload_types["Bind"] = payload_types.get("Bind", 0) + 1
            elif "meterpreter" in kl: payload_types["Meterpreter"] = payload_types.get("Meterpreter", 0) + 1
            elif "shell" in kl: payload_types["Shell"] = payload_types.get("Shell", 0) + 1
        console.print(table)
        console.print(f"\n[bold]Payload Statistics:[/bold]")
        console.print(f"  • Total Payloads: [cyan]{total_payloads}[/cyan]")
        if payload_types:
            type_stats = " | ".join([f"{k}: {v}" for k, v in payload_types.items()])
            console.print(f"  • Types: {type_stats}")
        if platforms:
            platform_stats = " | ".join([f"{k}: {v}" for k, v in platforms.items()])
            console.print(f"  • Platforms: {platform_stats}")
        console.print(f"\n[bold]Multi Handler Usage:[/bold]")
        console.print(f"  • [dim]multi reverse_tcp LHOST=192.168.1.100 LPORT=4444[/dim]")
        console.print(f"  • [dim]multi meterpreter/reverse_tcp LHOST=0.0.0.0 LPORT=5555[/dim]")
        console.print(f"  • [dim]multi sessions[/dim]")
        console.print(f"  • [dim]multi stop[/dim]")

    def cmd_show(self, args):
        if not args:
            console.print("Usage: show modules|payloads|modules/<category>", style="red")
            return
        subcommand = args[0].lower()
        if subcommand == "modules":
            self._show_all_modules()
        elif subcommand == "payloads":
            self.cmd_payloads([])
        elif subcommand.startswith("modules/"):
            category = subcommand[8:]
            self._show_modules_by_category(category)
        else:
            console.print(f"Unknown show subcommand: {subcommand}", style="red")
            console.print("Usage: show modules|payloads|modules/<category>", style="yellow")

    def _show_all_modules(self):
        terminal_width = shutil.get_terminal_size((80, 20)).columns
        MAX_MODULE_WIDTH = terminal_width // 4
        MAX_RANK_WIDTH = terminal_width // 6
        MAX_DESC_WIDTH = terminal_width // 4
        table = Table(box=box.SIMPLE_HEAVY, expand=True)
        table.add_column("Module", style="bold white", width=MAX_MODULE_WIDTH, overflow="fold", justify="left")
        table.add_column("Rank", style="bold yellow", width=MAX_RANK_WIDTH, justify="center")
        table.add_column("Description", style="white", min_width=10, overflow="fold", justify="left")
        for k, v in sorted(self.metadata.items()):
            display_key = k.replace("modules/", "", 1)
            if "__pycache__" in display_key:
                match = re.search(r"/(.+?)\/__pycache__/", "/" + k)
                if match:
                    display_key = re.sub(r"\/__pycache__\/.*$", "", display_key)
                    display_key = re.sub(r"(\.cpython-\d+)?$", "", display_key)
            if display_key.endswith('.py'):
                display_key = display_key[:-3]
            meta = self.metadata.get(k, {}) or {}
            rank = meta.get("rank", "Normal")
            desc = v.get("description", "(no description)")
            table.add_row(display_key, rank, desc)
        panel = Panel(table, title="All Modules", border_style="white", expand=True)
        console.print(panel)

    def _show_modules_by_category(self, category):
        category_modules = {}
        for key, path in self.modules.items():
            if not key.startswith("modules/"): continue
            if key.startswith(f"modules/{category}"):
                category_modules[key] = self.metadata.get(key, {})
        if not category_modules:
            console.print(f"No modules found in category: {category}", style="yellow")
            available_categories = self._get_available_categories()
            if available_categories:
                console.print("Available categories:", style="yellow")
                for cat in sorted(available_categories):
                    console.print(f"  • {cat}", style="dim")
            return
        table = Table(title=f"Modules in {category}", box=box.SIMPLE_HEAVY, expand=True)
        table.add_column("Module", style="bold cyan", width=35)
        table.add_column("Type", style="yellow", width=15)
        table.add_column("Platform", style="green", width=12)
        table.add_column("Rank", style="red", width=8)
        table.add_column("Description", style="white", min_width=25)
        for key, meta in sorted(category_modules.items()):
            display_name = key[len("modules/"):]
            kl = key.lower()
            module_type = "unknown"
            if "exploit" in kl: module_type = "exploit"
            elif "scanner" in kl or "discovery" in kl: module_type = "scanner"
            elif "auxiliary" in kl: module_type = "auxiliary"
            elif "post" in kl: module_type = "post"
            elif "payload" in kl: module_type = "payload"
            elif "encoder" in kl: module_type = "encoder"
            platform_info = meta.get("platform", "multi")
            if isinstance(platform_info, str): platform_info = platform_info.capitalize()
            rank = meta.get("rank", "Normal")
            description = meta.get("description", "No description available")
            table.add_row(display_name, module_type, str(platform_info), str(rank), description)
        total_modules = len(category_modules)
        module_types = {}
        platforms = {}
        for key in category_modules.keys():
            kl = key.lower()
            if "/windows/" in kl: platforms["Windows"] = platforms.get("Windows", 0) + 1
            elif "/linux/" in kl: platforms["Linux"] = platforms.get("Linux", 0) + 1
            elif "/android/" in kl: platforms["Android"] = platforms.get("Android", 0) + 1
            elif "/mac" in kl or "/osx" in kl: platforms["macOS"] = platforms.get("macOS", 0) + 1
            else: platforms["Multi"] = platforms.get("Multi", 0) + 1
            if "exploit" in kl: module_types["Exploit"] = module_types.get("Exploit", 0) + 1
            elif "scanner" in kl or "discovery" in kl: module_types["Scanner"] = module_types.get("Scanner", 0) + 1
            elif "auxiliary" in kl: module_types["Auxiliary"] = module_types.get("Auxiliary", 0) + 1
            elif "payload" in kl: module_types["Payload"] = module_types.get("Payload", 0) + 1
        console.print(table)
        console.print(f"\n[bold]Category Statistics:[/bold]")
        console.print(f"  • Total Modules: [cyan]{total_modules}[/cyan]")
        if module_types:
            type_stats = " | ".join([f"{k}: {v}" for k, v in module_types.items()])
            console.print(f"  • Types: {type_stats}")
        if platforms:
            platform_stats = " | ".join([f"{k}: {v}" for k, v in platforms.items()])
            console.print(f"  • Platforms: {platform_stats}")

    def _get_available_categories(self):
        categories = set()
        for key in self.modules.keys():
            if key.startswith("modules/"):
                rel_path = key[8:]
                if '/' in rel_path:
                    category = rel_path.split('/')[0]
                    categories.add(category)
        return categories

    def cmd_info(self, args):
        if not self.loaded_module:
            console.print("No module loaded. Use 'use <module>' first.", style="red")
            return
        mod = self.loaded_module.module
        meta = getattr(mod, "MODULE_INFO", {}) or {}
        name = meta.get("name", self.loaded_module.name.split('/')[-1])
        mod_type = self._get_module_type_from_path(mod.__file__).upper()
        authors = meta.get("author", meta.get("authors", "Unknown"))
        description = meta.get("description", "No description provided.")
        license_ = meta.get("license", "Unknown")
        references = meta.get("references", [])
        dependencies = meta.get("dependencies", [])
        dep_status = {}
        if dependencies:
            dep_status = self._check_dependencies(dependencies)
        console.print(f"\n[bold white]       Name: [/bold white][bold cyan]{name}[/bold cyan]")
        console.print(f"[bold white]     Module: [/bold white]{self.loaded_module.name}")
        console.print(f"[bold white]       Type: [/bold white]{mod_type}")
        console.print(f"[bold white]   Platform: [/bold white]{meta.get('platform', 'All')}")
        console.print(f"[bold white]       Arch: [/bold white]{meta.get('arch', 'All')}")
        console.print(f"[bold white]     Author: [/bold white]{authors}")
        console.print(f"[bold white]    License: [/bold white]{license_}")
        console.print(f"[bold white]       Rank: [/bold white]{meta.get('rank', 'Normal')}")
        console.print(f"\n[bold white]Description:[/bold white]")
        desc_lines = textwrap.fill(description, width=80)
        console.print(Panel(desc_lines, border_style="blue", box=box.SQUARE))
        if dependencies:
            console.print(f"\n[bold white]Dependencies:[/bold white]")
            deps_table = Table(show_header=True, header_style="bold white", box=box.SIMPLE, show_edge=False)
            deps_table.add_column("Package", style="white", width=25)
            deps_table.add_column("Status", style="white", width=15)
            deps_table.add_column("Action", style="white", width=30)
            for dep in dependencies:
                status = dep_status.get(dep, False)
                status_text = "[green]Available[/green]" if status else "[red]Missing[/red]"
                action_text = "[green]Ready[/green]" if status else f"[yellow]pip install {dep}[/yellow]"
                deps_table.add_row(dep, status_text, action_text)
            console.print(deps_table)
        if references:
            console.print(f"\n[bold white]References:[/bold white]")
            for i, ref in enumerate(references, 1):
                console.print(f"  [bold white]{i}.[/bold white] {ref}")
        if hasattr(mod, "OPTIONS") and isinstance(getattr(mod, "OPTIONS"), dict):
            opts = self.loaded_module.get_options()
            if opts:
                console.print(f"\n[bold yellow]Module options ({self.loaded_module.name}):[/bold yellow]")
                console.print("")
                table = Table(show_header=True, header_style="bold yellow", box=box.SIMPLE, show_edge=False)
                table.add_column("Name", style="white", width=25, no_wrap=True)
                table.add_column("Current", style="cyan", width=25, no_wrap=True)
                table.add_column("Required", style="white", width=25, justify="center")
                table.add_column("Description", style="white", width=30)
                for name, info in opts.items():
                    current = str(info.get('value', '')).strip()
                    if not current: current = info.get('default', '')
                    if not current: current = ""
                    required = "yes" if info.get('required') else "no"
                    desc = info.get('description', 'No description')
                    table.add_row(name, current, required, desc)
                console.print(table)
            else:
                console.print(f"\n[bold yellow]This module has no options.[/bold yellow]")
        else:
            console.print(f"\n[bold yellow]This module has no options.[/bold yellow]")
        console.print("")

    def _get_module_type_from_path(self, module_file_path):
        folder_name = os.path.basename(os.path.dirname(module_file_path))
        if folder_name in ['scanner', 'auxiliary']: return 'auxiliary'
        elif folder_name in ['exploit']: return 'exploit'
        elif folder_name in ['post']: return 'post'
        elif folder_name in ['payload']: return 'payload'
        elif folder_name in ['encoder']: return 'encoder'
        else: return 'auxiliary'

    def cmd_options(self, args):
        if not self.loaded_module:
            console.print("No module loaded.", style="red")
            return
        if hasattr(self.loaded_module.module, "OPTIONS"):
            table = Table(show_header=True, header_style="bold white", box=box.SIMPLE)
            table.add_column("Name", width=30, no_wrap=True)
            table.add_column("Current", justify="center", width=30)
            table.add_column("Required", justify="center", width=15)
            table.add_column("Description", width=50)
            for k, v in self.loaded_module.get_options().items():
                current_setting = str(v['value']) if 'value' in v else "Not Set"
                required = "Yes" if v.get('required') else "No"
                description = v.get('description', "No description available.")
                table.add_row(k, current_setting, required, description)
            panel = Panel(table, title="Module Options", border_style="white", expand=False)
            console.print(panel)
        else:
            console.print(f"Module '{self.loaded_module.name}' has no configurable options.", style="yellow")

    def cmd_set(self, args):
        if not self.loaded_module: 
            console.print("No module loaded.", style="red")
            return
        if len(args) < 2: 
            console.print("Usage: set <option> <value>", style="red")
            return
        opt, val = args[0], " ".join(args[1:])
        try:
            self.loaded_module.set_option(opt, val)
            console.print(f"{opt} => {val}", style="green")
        except Exception as e:
            console.print(str(e), style="red")

    def cmd_back(self, args):
        if self.loaded_module: 
            console.print(f"Unloaded {self.loaded_module.name}", style="yellow")
            self.loaded_module = None
        else: 
            console.print("No module loaded.", style="red")

    def cmd_scan(self, args):
        self.scan_modules()
        console.print(f"Scanned {len(self.modules)} modules.", style="green")

    def cmd_search(self, args):
        if not args:
            return console.print("Usage: search <keyword>", style="red")
        keyword = " ".join(args).strip()
        results = Search(self.modules, self.metadata).search_modules(keyword)
        if not results:
            return console.print(f"No modules matching '{keyword}'", style="yellow")
        table = Table(box=box.SIMPLE)
        table.add_column("Module", style="bold red", overflow="fold")
        table.add_column("Description")
        for key, desc in sorted(results):
            display_key = key.replace("modules/", "", 1)
            table.add_row(display_key, desc or "(no description)")
        panel = Panel(table, title=f"Module for: {keyword}", border_style="white", expand=True)
        console.print(panel)

    def cmd_banner(self, args):
        if not args: 
            return console.print("Usage: banner reload|list", style="red")
        if args[0] == "reload": 
            load_banners_from_folder()
            console.print(get_random_banner())
        elif args[0] == "list":
            files = [f.name for f in BANNER_DIR.glob("*.txt")]
            if files:
                for f in files: 
                    console.print(f)
            else:
                console.print("No banner files.")

    def cmd_cd(self, args):
        if not args: return
        try: 
            os.chdir(args[0])
            console.print("Changed Directory to: " + os.getcwd())
        except Exception as e: 
            console.print("Error: " + str(e), style="red")
    def cmd_pwd(self, args):
           try:
               """Print current working directory"""
               console.print(f"[bold cyan]Current Directory:[/bold cyan] [white]{os.getcwd()}[/white]")
           except Exception as e:
               console.print(f"[red]Error:[/red] {e}", style="red")

    def cmd_ls(self, args):
        try:
            for f in os.listdir(): 
                console.print(f)
        except Exception as e: 
            console.print("Error: " + str(e), style="red")

    def cmd_clear(self, args): 
        os.system("cls" if platform.system().lower() == "windows" else "clear")

    def repl(self):
        console.print("Lazy Framework - type 'help' for commands", style="bold cyan")
        console.print(get_random_banner())
        while True:
            try:
                prompt = f"lzf(\x1b[41m\x1b[97m{self.loaded_module.name}\x1b[0m)> " if self.loaded_module else "lzf> "
                line = input(prompt)
            except (EOFError, KeyboardInterrupt):
                console.print("\n[bold green]Exiting Lazy Framework...[/bold green]")
                console.print("[bold cyan]Thank you for using Lazy Framework. We hope to see you again soon![/bold cyan]")
                break
            if not line.strip(): continue
            parts = shlex.split(line)
            cmd, args = parts[0], parts[1:]
            if cmd in ("exit", "quit"): 
                console.print("\n[bold green]Exiting Lazy Framework...[/bold green]")
                console.print("[bold cyan]Thank you for using Lazy Framework. We hope to see you again soon![/bold cyan]")
                break
            getattr(self, f"cmd_{cmd}", lambda a: console.print("Unknown command", style="red"))(args)

# ========== Main ==========
def main():
    anim = SingleLineMarquee("Starting the Lazy Framework Console...", 0.60, 0.06)
    anim.start()
    anim.wait()
    time.sleep(0.6)
    os.system("cls" if platform.system().lower() == "windows" else "clear")
    load_banners_from_folder()
    LazyFramework().repl()

if __name__ == "__main__":
    main()
