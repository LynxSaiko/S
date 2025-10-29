#!/usr/bin/env python3

import os, sys, shlex, importlib.util, re, platform, time, random, itertools, threading, shutil, textwrap
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

# Use Rich for nicer terminal UI
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich import box

console = Console()

# Paths
BASE_DIR = Path(__file__).parent
MODULE_DIR, EXAMPLES_DIR, BANNER_DIR = BASE_DIR / "modules", BASE_DIR / "examples", BASE_DIR / "banner"
METADATA_READ_LINES = 120
_loaded_banners = []

# ========== Banner Loader ==========
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

    if scale < 1.0:
        new_lines = [line[:int(cols)] for line in lines]
    else:
        new_lines = [line.center(cols) for line in lines]

    return colorize_banner("\n".join(new_lines)) + "\n\n"

# ========== One-line Animation ==========
class SingleLineMarquee:
    def __init__(self, text="Starting the Lazy Framework Console...",
                 text_speed: float = 6.06, spinner_speed: float = 0.06):
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
        self._stop.set();
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
        else:
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
        
    def _ensure_dirs(self):
        for d in (MODULE_DIR, EXAMPLES_DIR, BANNER_DIR):
            d.mkdir(parents=True, exist_ok=True)

    def scan_modules(self):
        self._ensure_dirs()
        self.modules.clear()
        self.metadata.clear()
        for folder, prefix in ((MODULE_DIR, "modules"),):
            for p in folder.rglob("*"):
                rel = str(p.relative_to(folder)).replace(os.sep, "/")
                key = f"{prefix}/{rel[:-3]}"
                self.modules[key] = p
                self.metadata[key] = self._read_meta(p)
    def _read_meta(self, path):
        data = {"description": "", "options": []}
        try:
            text = "".join(path.open("r", encoding="utf-8", errors="ignore").readlines()[:METADATA_READ_LINES])
            if (m := re.search(r"['\"]description['\"]\s*:\s*['\"]([^'\"]+)['\"]", text)):
                data["description"] = m.group(1)
            if (mo := re.search(r"OPTIONS\s*=\s*{([^}]*)}", text, re.DOTALL)):
                data["options"] = re.findall(r"['\"]([A-Za-z0-9_]+)['\"]\s*:", mo.group(1))
        except: pass
        return data

    def import_module(self, key):
        path = self.modules[key]
        spec = importlib.util.spec_from_file_location(key.replace('/', '_'), path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    # -------- Commands (Rich-powered) --------
    def cmd_help(self, args):
        """Responsive help (Rich table)."""
        commands = [
            ("show modules", "Show available modules"),
            ("use <module>", "Load a module by name"),
            ("options", "Show options for current module"),
            ("set <option> <value>", "Set module option"),
            ("run", "Run current module"),
            ("back", "Unload module"),
            ("search <keyword>", "Search modules"),
            ("scan", "Rescan modules"),
            ("banner reload|list", "Reload/list banner files"),
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

    def cmd_show(self, args):
        """Show available modules using Rich table inside a box."""
        table = Table(box=box.SIMPLE_HEAVY, expand=False)
        table.add_column("Module", style="bold white", no_wrap=True, width=50, justify="left")
        table.add_column("Description", style="white", overflow="fold", justify="left")

        for k, v in sorted(self.metadata.items()):
            desc = v.get("description", "(no description)")
            table.add_row(k, desc)

        panel = Panel(table, title="Modules List", border_style="white", expand=True)
        console.print(panel)

    def display_module_info(self, inst: ModuleInstance):
        """
        Display module info using Rich: Panel + Table for options.
        """
        title = f"Module: {inst.name}"
        opts = inst.get_options()

        table = Table(show_header=True, header_style="bold red", box=box.SIMPLE)
        table.add_column("Name", style="bold")
        table.add_column("Current", justify="center")
        table.add_column("Required", justify="center")
        table.add_column("Description", justify="center")

        for name, info in opts.items():
            cur = str(info.get("value", ""))
            req = "yes" if info.get("required") else "no"
            desc = info.get("description", "")
            table.add_row(name, cur, req, desc)

        panel = Panel(table, title=title, border_style="blue", expand=True)
        console.print(panel)

    def cmd_use(self, args):
        if not args:
            console.print("Usage: use <module>", style="bold red")
            return

        user_key = args[0].strip()
        if user_key.lower().endswith('.py'):
            user_key = user_key[:-3]

        variations = [user_key, f"modules/{user_key}"]
        if user_key.startswith('modules/'):
            variations.insert(0, user_key)
            variations.append(user_key[8:])

        key = None
        for variation in variations:
            if variation in self.modules:
                key = variation
                break

        if not key:
            frag = user_key.split('/')[-1].lower()
            candidates = []
            for k in self.modules.keys():
                module_name = k.split('/')[-1].lower()
                if (frag == module_name or frag in k.lower() or k.lower().endswith('/' + frag)):
                    candidates.append(k)
            if candidates:
                console.print(f"Module '{user_key}' not found. Did you mean:", style="yellow")
                for c in candidates[:8]:
                    console.print("  " + c)
                return
            else:
                console.print(f"Module '{user_key}' not found.", style="red")
                category = '/'.join(user_key.split('/')[:-1])
                if category:
                    console.print(f"Available modules in '{category}':")
                    for k in sorted(self.modules.keys()):
                        if k.startswith(category):
                            console.print("  ", k)
                return

        try:
            path = self.modules[key]
            spec = importlib.util.spec_from_file_location(key.replace('/', '_'), path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            inst = ModuleInstance(key, mod)
            for k, meta in getattr(mod, "OPTIONS", {}).items():
                if "default" in meta:
                    inst.options[k] = meta["default"]

            self.loaded_module = inst
            console.print(Panel(f"Loaded module [bold]{key}[/bold]", style="green"))
            #self.display_module_info(inst)

        except Exception as e:
            console.print(f"Load error: {e}", style="bold red")

    def cmd_options(self, args):
        if not self.loaded_module:
            console.print("No module loaded.", style="red"); return
        if hasattr(self.loaded_module.module, "OPTIONS"):

            table = Table(title=f"Options for {self.loaded_module.name}", box=box.SIMPLE, expand=True)
            table.add_column("Name", no_wrap=True)
            table.add_column("Current", justify="left")
            table.add_column("Required", justify="center")
            table.add_column("Description")
            for k, v in self.loaded_module.get_options().items():
               table.add_row(k, str(v['value']), 'yes' if v.get('required') else 'no', v.get('description',''))
            panel = Panel(table, border_style="white", expand=True)
            console.print(panel)
        else:
            console.print(f"Module '{self.loaded_module.name}' has no configurable options.", style="yellow")


    def cmd_set(self, args):
        if not self.loaded_module: console.print("No module loaded.", style="red"); return
        if len(args) < 2: console.print("Usage: set <option> <value>", style="red"); return
        opt, val = args[0], " ".join(args[1:])
        try:
            self.loaded_module.set_option(opt, val)
            console.print(f"{opt} => {val}", style="green")
        except Exception as e:
            console.print(str(e), style="red")

    def cmd_run(self, args):
        if not self.loaded_module: console.print("No module loaded.", style="red"); return
        try: self.loaded_module.run(self.session)
        except Exception as e: console.print(f"Run error: {e}", style="red")

    def cmd_back(self, args):
        if self.loaded_module: console.print(f"Unloaded {self.loaded_module.name}", style="yellow"); self.loaded_module = None
        else: console.print("No module loaded.", style="red")

    def cmd_scan(self, args):
        self.scan_modules(); console.print(f"Scanned {len(self.modules)} modules.", style="green")

    def cmd_search(self, args):
        if not args:
            return console.print("Usage: search <keyword>", style="red")
        keyword = " ".join(args).strip()
        results = Search(self.modules, self.metadata).search_modules(keyword)
        if not results:
            return console.print(f"No modules matching '{keyword}'", style="yellow")

        table = Table(title=f"Search results for: {keyword}", box=box.SIMPLE)
        table.add_column("Module", style="bold red", no_wrap=True)
        table.add_column("Description")
        for key, desc in sorted(results):
            table.add_row(key, desc or "(no description)")

        panel = Panel(table, title=f"{self.loaded_module}", border_style="white", expand=True)
        console.print(panel)
        console.print(f"{len(results)} result(s) found.")

    def cmd_banner(self, args):
        if not args: return console.print("Usage: banner reload|list", style="red")
        if args[0] == "reload": load_banners_from_folder(); console.print(get_random_banner())
        elif args[0] == "list":
            files = [f.name for f in BANNER_DIR.glob("*.txt")]
            if files:
                for f in files: console.print(f)
            else:
                console.print("No banner files.")

    def cmd_cd(self, args):
        if not args: return
        try: os.chdir(args[0]); console.print("Changed Directory to: " + os.getcwd())
        except Exception as e: console.print("Error: " + str(e), style="red")

    def cmd_ls(self, args):
        try:
            for f in os.listdir(): console.print(f)
        except Exception as e: console.print("Error: " + str(e), style="red")

    def cmd_clear(self, args): os.system("cls" if platform.system().lower() == "windows" else "clear")

    def repl(self):
        console.print("Lazy Framework - type 'help' for commands", style="bold cyan")
        console.print(get_random_banner())
        while True:
            try:
                prompt = f"lzf(\x1b[41m\x1b[97m{self.loaded_module.name}\x1b[0m)> " if self.loaded_module else "lzf> "
                line = input(prompt)
            except (EOFError, KeyboardInterrupt):
                console.print(); break
            if not line.strip(): continue
            parts = shlex.split(line); cmd, args = parts[0], parts[1:]
            if cmd in ("exit", "quit"): break
            getattr(self, f"cmd_{cmd}", lambda a: console.print("Unknown command", style="red"))(args)

# ========== Example Modules ==========
EXAMPLES = {
    "recon/sysinfo.py": '''import platform
MODULE_INFO={"name":"recon/sysinfo","description":"Print local system info"}
OPTIONS={"VERBOSE":{"required":False,"default":"true","description":"Verbose output"}}
def run(session, options):
    print("System info:")
    print("  User:", session.get("user"))
    print("  Platform:", platform.platform())''',
    "aux/echo.py": '''MODULE_INFO={"name":"aux/echo","description":"Echo string back (safe)"}
OPTIONS={"MSG":{"required":True,"default":"","description":"Message to echo"}}
def run(session,options):
    print("ECHO:",options.get("MSG",""))'''
}

def ensure_examples():
    EXAMPLES_DIR.mkdir(exist_ok=True, parents=True)
    for rel, content in EXAMPLES.items():
        p = EXAMPLES_DIR / rel; p.parent.mkdir(exist_ok=True, parents=True)
        if not p.exists(): p.write_text(content)

# ========== Main ==========
def main():
    anim = SingleLineMarquee("Starting the Lazy Framework Console...", 0.60, 0.06)
    anim.start(); anim.wait()
    time.sleep(0.6)
    os.system("cls" if platform.system().lower() == "windows" else "clear")
    ensure_examples(); load_banners_from_folder()
    LazyFramework().repl()
    console.print("Goodbye.")

if __name__ == "__main__":
    main()
