#!/usr/bin/python3

import socket
import threading
import ipaddress
import time
import re
import os
import platform
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from tqdm import tqdm
except ImportError:
    print("Error: Required libraries (requests, rich, tqdm) not found.")
    print("Please install them: pip install requests rich tqdm")
    exit(1)

# Nonaktifkan warning SSL dari Requests
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

MODULE_INFO = {
    "name": "Router Network Scanner",
    "description": "Advanced network scanning for router discovery and service detection",
    "author": "Lazy Framework",
    "license": "MIT",
    "dependencies": ["requests", "rich", "tqdm"],
    "platform": "Multi",
    "rank": "Normal",
}

OPTIONS = {
    "target": {
        "description": "Target IP, range or subnet (e.g., 192.168.1.0/24, 192.168.1.1-100)",
        "required": True,
        "default": "192.168.1.1"
    },
    "ports": {
        "description": "Ports to scan (common, http, https, all, or custom: 80,443,8080)",
        "required": False,
        "default": "router"
    },
    "timeout": {
        "description": "Scan timeout per host in seconds",
        "required": False,
        "default": "4"
    },
    "threads": {
        "description": "Number of concurrent threads",
        "required": False,
        "default": "10"
    },
    "ping_check": {
        "description": "Enable ping check before port scanning",
        "required": False,
        "default": "false"
    }
}

class NetworkScanner:
    """Advanced network scanner with OOP design"""
    PORT_PROFILES = {
        "common": [21, 22, 23, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443],
        "http": [80, 443, 8080, 8443, 8000, 8888],
        "https": [443, 8443],
        "router": [23, 80, 443, 7547, 8080, 8291, 8443],
        "all": list(range(1, 1001))
    }
    ROUTER_BRANDS = {
        "Juniper": {
            "keywords": [r"juniper", r"junos", r"srx"],
            "http_keywords": [r"junos", r"juniper networks", r"web management"],
            "ports": [22, 80, 443, 3000],
            "paths": ["/", "/login"],
            "server_patterns": [r"Juniper", r"ScreenOS"],
            "favicon_hashes": [],
            "min_score": 3
        },
        "Fortinet": {
            "keywords": [r"fortinet", r"fortigate"],
            "http_keywords": [r"fortigate", r"fortinet web interface", r"fortios"],
            "ports": [22, 80, 443, 8080],
            "paths": ["/", "/login"],
            "server_patterns": [r"FortiOS"],
            "favicon_hashes": [],
            "min_score": 3
        },
        "TP-Link": {
            "keywords": [r"tp-link", r"tplink", r"archer"],
            "http_keywords": [r"tp-link login", r"tplink wireless", r"lighttpd", r"tplink management"],
            "ports": [23, 80, 443, 8080],
            "paths": ["/", "/userRpm/LoginRpm.htm", "/login.asp"],
            "server_patterns": [r"TP-LINK", r"lighttpd"],
            "favicon_hashes": ["d41d8cd98f00b204e9800998ecf8427e"],
            "min_score": 2
        },
        "Netgear": {
            "keywords": [r"netgear", r"r7000", r"nighthawk"],
            "http_keywords": [r"netgear genie", r"nighthawk", r"netgear router login"],
            "ports": [23, 80, 443, 8080],
            "paths": ["/", "/login"],
            "server_patterns": [r"Netgear"],
            "favicon_hashes": ["7b0d4bc0ca1659d54469e5013a08d240"],
            "min_score": 2
        },
        "Asus": {
            "keywords": [r"asus", r"rt-", r"rog"],
            "http_keywords": [r"asus wireless router", r"asuswrt"],
            "ports": [23, 80, 443],
            "paths": ["/", "/login.asp"],
            "server_patterns": [r"Asus"],
            "favicon_hashes": [],
            "min_score": 2
        },
        "Mikrotik": {
            "keywords": [r"mikrotik", r"routeros"],
            "http_keywords": [r"routeros", r"mikrotik configuration", r"winbox"],
            "ports": [22, 80, 443, 8291],
            "paths": ["/", "/webfig"],
            "server_patterns": [r"Mikrotik"],
            "favicon_hashes": [],
            "min_score": 2
        },
        "Ubiquiti": {
            "keywords": [r"ubiquiti", r"unifi", r"airmax"],
            "http_keywords": [r"ubiquiti networks", r"unifi controller", r"edgeos"],
            "ports": [22, 80, 443, 8443],
            "paths": ["/", "/login"],
            "server_patterns": [r"Ubiquiti"],
            "favicon_hashes": ["6dcab71e60f0242907940f0fcda69ea5", "09a1e50dc3369e031b97f38abddd10c8"],
            "min_score": 2
        },
        "Huawei": {
            "keywords": [r"huawei", r"hg", r"echolife"],
            "http_keywords": [r"huawei router", r"echolife", r"gpon", r"ont"],
            "ports": [23, 80, 443, 7547],
            "paths": ["/", "/login.asp"],
            "server_patterns": [r"Huawei"],
            "favicon_hashes": [],
            "min_score": 3
        },
        "ZTE": {
            "keywords": [r"zte", r"f6", r"zxhn"],
            "http_keywords": [r"zte router", r"zxhn", r"gpon management"],
            "ports": [23, 80, 443, 7547],
            "paths": ["/", "/login.asp"],
            "server_patterns": [r"ZTE"],
            "favicon_hashes": [],
            "min_score": 2
        },
        "Indihome (Telkom)": {
            "keywords": [r"indihome", r"telkom", r"zte", r"fiberhome"],
            "http_keywords": [r"indihome", r"modem configuration", r"fibrehome", r"zte gpon ont", r"telkom indonesia"],
            "ports": [80, 443, 8080, 7547],
            "paths": ["/", "/login.asp", "/gpon"],
            "server_patterns": [r"ZTE", r"FiberHome"],
            "favicon_hashes": [],
            "min_score": 2
        },
        "MyRepublic": {
            "keywords": [r"myrepublic", r"sagemcom", r"technicolor", r"tg389ac", r"2744r", r"fast", r"hg8245", r"eg8141a5"],
            "http_keywords": [r"myrepublic", r"router setup", r"sagemcom fast", r"technicolor gateway", r"tg389ac", r"myrepublic home", r"sagemcom", r"telecomadmin", r"myrepublic broadband-\w+"],
            "ports": [80, 443, 8080],
            "paths": ["/", "/login.html", "/gateway", "/html/index.html", "/menu.html"],
            "server_patterns": [r"Sagemcom", r"Technicolor", r"Huawei"],
            "favicon_hashes": [],
            "min_score": 2
        },
        "First Media": {
            "keywords": [r"first media", r"docsis"],
            "http_keywords": [r"first media", r"docsis cable modem", r"arris", r"hitron"],
            "ports": [80, 443, 8080],
            "paths": ["/", "/login"],
            "server_patterns": [r"Arris", r"Hitron"],
            "favicon_hashes": [],
            "min_score": 2
        },
        "Cisco": {
            "keywords": [r"cisco", r"ios", r"meraki"],
            "http_keywords": [r"cisco systems", r"cisco ios", r"cisco-sccp", r"secure device manager", r"meraki"],
            "ports": [22, 23, 80, 443, 2000],
            "paths": ["/", "/login"],
            "server_patterns": [r"Cisco"],
            "favicon_hashes": [],
            "min_score": 2
        },
        "ISP Router (TR-069)": {
            "keywords": [r"tr-069", r"acs", r"gpon"],
            "http_keywords": [r"tr069", r"cpe management", r"broadband forum"],
            "ports": [7547],
            "paths": ["/", "/tr069"],
            "server_patterns": [],
            "favicon_hashes": [],
            "min_score": 2
        },
        "Embedded Device": {
            "keywords": [r"boa", r"goahead", r"micro_httpd"],
            "http_keywords": [r"boa/0\.94", r"goahead-webserver", r"embedded http server", r"rompager"],
            "ports": [80, 443, 8080],
            "paths": ["/"],
            "server_patterns": [r"Boa", r"GoAhead", r"RomPager"],
            "favicon_hashes": [],
            "min_score": 1
        },
    }
    SERVICE_DB = {
        21: "ftp", 22: "ssh", 23: "telnet", 53: "dns", 80: "http",
        443: "https", 7547: "tr-069", 8080: "http-proxy", 8291: "winbox",
        8443: "https-alt", 2000: "cisco-sccp"
    }
    FIRMWARE_PATTERNS = [
        r"firmware[:\s]*v?([\d\w\.\-]+)",
        r"fw[_\- ]?ver[:\s]*v?([\d\w\.\-]+)",
        r"version[:\s]*v?([\d\w\.\-]+)",
        r"software version[:\s]*v?([\d\w\.\-]+)",
        r"build[:\s]*([A-Za-z0-9\.\-_/]+)",
        r"build/([\d\.\-a-zA-Z]+)",
        r"sysVersion[:\s]*([^\s<]+)",
        r"sw_ver[:\s]*v?([\d\w\.\-]+)",
        r"firmware version[:\s]*v?([\d\w\.\-]+)",
        r"HW Version[:\s]*([^\s<]+)",
        r"Rom-0|ROM-0|rom-0",
        r"TP-LINK\s+Firmware\s+Ver[:\s]*v?([\d\w\.\-]+)",
        r"Device\s+Version[:\s]*v?([\d\w\.\-]+)",
        r"Firmware:\s*<b>([^<]+)</b>",
    ]

    def __init__(self, console, target, ports="router", timeout=4, max_threads=10, ping_check=False):
        self.console = console
        self.target = target
        self.ports = self._resolve_port_profile(ports)
        try:
            self.timeout = float(timeout)
        except Exception:
            self.timeout = 4.0
        try:
            self.max_threads = int(max_threads)
        except Exception:
            self.max_threads = 10
        self.ping_check = ping_check
        self.discovered_hosts = []
        self.scan_stats = {
            'total_hosts': 0, 'active_hosts': 0, 'open_ports': 0,
            'scan_duration': 0, 'routers_found': 0
        }

    def _resolve_port_profile(self, ports_config):
        if isinstance(ports_config, str) and ports_config in self.PORT_PROFILES:
            return self.PORT_PROFILES[ports_config]
        else:
            try:
                ports = []
                for part in str(ports_config).split(','):
                    part = part.strip()
                    if not part:
                        continue
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        ports.extend(range(start, end + 1))
                    else:
                        ports.append(int(part))
                return ports
            except Exception:
                return self.PORT_PROFILES["common"]

    def generate_ip_list(self):
        ip_list = []
        try:
            if '/' in self.target:
                network = ipaddress.ip_network(self.target, strict=False)
                ip_list = [str(ip) for ip in network.hosts()]
            elif '-' in self.target:
                start_ip, end_ip = self.target.split('-')
                start = ipaddress.ip_address(start_ip.strip())
                end_ip = end_ip.strip()
                if '.' in end_ip:
                    end = ipaddress.ip_address(end_ip)
                else:
                    parts = start_ip.split('.')
                    end = ipaddress.ip_address(f"{'.'.join(parts[:-1])}.{end_ip}")
                current = start
                while current <= end:
                    ip_list.append(str(current))
                    current += 1
            else:
                ip_list = [self.target]
        except Exception as e:
            raise Exception(f"Invalid target format: {e}")

        self.scan_stats['total_hosts'] = len(ip_list)
        return ip_list

    def ping_host(self, ip):
        try:
            param = "-n 1 -w 1000" if platform.system().lower() == "windows" else "-c 1 -W 1"
            response = os.system(f"ping {param} {ip} > /dev/null 2>&1")
            return response == 0
        except:
            return False

    def scan_port(self, ip, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _extract_myrepublic_firmware(self, html_content, page_path):
        """Extract firmware info khusus untuk router MyRepublic"""
        firmware_patterns = [
            r'firmware\s*version[^>]*>([^<]+)',
            r'software\s*version[^>]*>([^<]+)',
            r'fw_ver[^>]*>([^<]+)',
            r'sw_ver[^>]*>([^<]+)',
            r'<td[^>]*>firmware[^<]*</td>\s*<td[^>]*>([^<]+)',
            r'<td[^>]*>software[^<]*</td>\s*<td[^>]*>([^<]+)',
            r'<td[^>]*>version[^<]*</td>\s*<td[^>]*>([^<]+)',
        ]
        
        for pattern in firmware_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match and len(match.strip()) > 3:
                    clean_match = re.sub(r'<[^>]+>', '', match).strip()
                    if clean_match:
                        return clean_match
        return ""

    def get_service_fingerprint(self, ip, port):
        if port in {21, 22, 23, 25, 110, 143, 8291}:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect((ip, port))
                banner = sock.recv(256).decode('utf-8', errors='ignore').strip()
                sock.close()
                firmware = ""
                for pat in self.FIRMWARE_PATTERNS:
                    m = re.search(pat, banner, re.IGNORECASE)
                    if m:
                       firmware = m.group(1) if m.groups() else m.group(0)
                       break
                return {"type": "L4", "banner": banner[:200], "firmware": firmware}
            except:
                return {"type": "L4", "banner": "", "firmware": ""}

        elif port in {80, 443, 7547, 8080, 8443}:
            scheme = "https" if port in {443, 8443} else "http"
            http_data = {
                "type": "HTTP", 
                "banner": "", 
                "title": "", 
                "auth_header": "", 
                "status_code": None, 
                "body_samples": [], 
                "favicon_hash": "", 
                "firmware": ""
            }
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; RouterScanner/1.0)'}
            
            # Prioritaskan path MyRepublic untuk firmware detection
            myrepublic_paths = [
                "/menu.html", "/login.html", "/gateway", "/html/index.html", 
                "/html/menu.html", "/deviceinfo.html", "/status.html",
                "/", "/login"
            ]
            
            combined_body = ""
            firmware_found = ""
            
            for path in myrepublic_paths:
                url = f"{scheme}://{ip}:{port}{path}"
                try:
                    response = requests.get(url, timeout=self.timeout, verify=False, allow_redirects=True, headers=headers)
                    http_data['banner'] = (response.headers.get('Server') or "").strip()
                    http_data['auth_header'] = (response.headers.get('WWW-Authenticate') or "").strip()
                    http_data['status_code'] = response.status_code
                    
                    if response.text:
                        match = re.search(r'<title\b[^>]*>(.*?)</title>', response.text[:8000], re.IGNORECASE | re.DOTALL)
                        if match:
                            http_data['title'] = match.group(1).strip()
                        body_sample = re.sub(r'\s+', ' ', response.text[:2000]).lower()
                        http_data['body_samples'].append(body_sample)
                        combined_body += body_sample + " "
                        
                        # Cari firmware khusus di MyRepublic pages
                        if not firmware_found and any(x in path for x in ['menu.html', 'deviceinfo', 'status']):
                            firmware_found = self._extract_myrepublic_firmware(response.text, path)
                    
                    # Favicon hash
                    if not http_data['favicon_hash']:
                        favicon_url = f"{scheme}://{ip}:{port}/favicon.ico"
                        try:
                            fav_resp = requests.get(favicon_url, timeout=1, verify=False, headers=headers)
                            if fav_resp.status_code == 200:
                                http_data['favicon_hash'] = hashlib.md5(fav_resp.content).hexdigest()
                        except:
                            pass
                            
                except requests.exceptions.RequestException:
                    continue
            
            # Jika belum ketemu firmware, cari di combined body dengan patterns umum
            if not firmware_found:
                search_text = " ".join([http_data.get('banner',''), http_data.get('title',''), combined_body]).strip()
                sources_to_check = [
                    http_data.get('banner', ''),
                    http_data.get('auth_header', ''),
                    search_text
                ]
                
                for source in sources_to_check:
                    if firmware_found:
                        break
                    for pat in self.FIRMWARE_PATTERNS:
                        m = re.search(pat, source, re.IGNORECASE)
                        if m:
                            firmware_found = m.group(1) if m.groups() else m.group(0)
                            break
            
            http_data['firmware'] = firmware_found
            return http_data

        return {"type": "Generic", "banner": "", "firmware": ""}

    def detect_router_brand(self, open_ports):
        port_numbers = {p['port'] for p in open_ports}
        all_l7_text = ""
        all_l4_text = ""
        all_fav_hashes = set()

        for p in open_ports:
            if p.get('type') == 'HTTP' and p.get('http_data'):
                hd = p['http_data']
                server = (hd.get('banner') or "").lower()
                title = (hd.get('title') or "").lower()
                auth = (hd.get('auth_header') or "").lower()
                bodies = " ".join(hd.get('body_samples', []))
                all_l7_text += f" {server} {title} {auth} {bodies}"
                if hd.get('favicon_hash'):
                    all_fav_hashes.add(hd['favicon_hash'])
            elif p.get('type') == 'L4':
                all_l4_text += f" {(p.get('banner') or '').lower()}"
        
        combined_text = (all_l7_text + " " + all_l4_text).strip()

        # Fast paths
        if 8291 in port_numbers:
            return "Mikrotik"
        if 7547 in port_numbers:
            isp_candidates = ["myrepublic", "indihome", "telkom", "sagemcom", "technicolor", "first media"]
            for k in isp_candidates:
                if k in combined_text:
                    if "myrepublic" in combined_text:
                        return "MyRepublic"
                    if "zte" in combined_text:
                        return "ZTE"
                    if "indihome" in combined_text or "telkom" in combined_text:
                        return "Indihome (Telkom)"
                    if "first media" in combined_text:
                        return "First Media"
            return "ISP Router (TR-069)"
        
        # Prioritaskan ISP brands
        isp_brands = ["MyRepublic", "Indihome (Telkom)", "First Media", "ZTE"]
        for brand in isp_brands:
            data = self.ROUTER_BRANDS.get(brand, {})
            score = 0
            
            # Check keywords
            for kw in data.get("keywords", []) + data.get("http_keywords", []):
                if re.search(kw, combined_text, re.IGNORECASE):
                    score += 2 if kw in data.get("http_keywords", []) else 1
            
            # Check server patterns
            for pattern in data.get("server_patterns", []):
                if re.search(pattern, all_l7_text, re.IGNORECASE):
                    score += 3
            
            # Check port matches
            score += len(set(data.get("ports", [])) & port_numbers)
            
            # Check favicon hashes
            for fh in data.get("favicon_hashes", []):
                if fh in all_fav_hashes:
                    score += 2
            
            if score >= data.get("min_score", 2):
                return brand

        # General brand scoring
        brand_scores = {}
        for brand, data in self.ROUTER_BRANDS.items():
            if brand in isp_brands:
                continue
            score = 0
            
            for kw in data.get("keywords", []) + data.get("http_keywords", []):
                if re.search(kw, combined_text, re.IGNORECASE):
                    score += 2 if kw in data.get("http_keywords", []) else 1
            
            for pattern in data.get("server_patterns", []):
                if re.search(pattern, all_l7_text, re.IGNORECASE):
                    score += 3
            
            score += len(set(data.get("ports", [])) & port_numbers)
            
            for fh in data.get("favicon_hashes", []):
                if fh in all_fav_hashes:
                    score += 2
            
            if score >= data.get("min_score", 2):
                brand_scores[brand] = score

        if brand_scores:
            best_brand = max(brand_scores.items(), key=lambda x: x[1])[0]
            return best_brand

        if 80 in port_numbers or 443 in port_numbers or 8080 in port_numbers or 8443 in port_numbers:
            return "Generic Web Device"

        return ""

    def _get_hostname(self, ip):
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            # Fallback yang lebih simple
            if ip.endswith('.1'):
               return "Router"
        else:
               return "Device"
    def _is_router_like(self, open_ports):
        port_numbers = {p['port'] for p in open_ports}
        router_ports = {23, 80, 443, 7547, 8080, 8291}
        return 7547 in port_numbers or len(router_ports.intersection(port_numbers)) >= 2

    def scan_host(self, ip):
        if self.ping_check and not self.ping_host(ip):
            return None

        open_ports = []
        max_threads_per_host = min(5, max(1, len(self.ports) * 2))
        
        with ThreadPoolExecutor(max_workers=max_threads_per_host) as executor:
            # Scan ports
            future_to_port = {executor.submit(self.scan_port, ip, port): port for port in self.ports}
            successful_ports = {}
            
            for future in as_completed(future_to_port):
                port = future_to_port[future]
                try:
                    if future.result():
                        successful_ports[port] = True
                except Exception:
                    pass

            # Get fingerprints for open ports
            future_to_fp = {executor.submit(self.get_service_fingerprint, ip, port): port for port in successful_ports.keys()}
            
            for future in as_completed(future_to_fp):
                port = future_to_fp[future]
                try:
                    fingerprint = future.result()
                    service_name = self.SERVICE_DB.get(port, "unknown")
                    
                    open_ports.append({
                        'port': port,
                        'service': service_name,
                        'type': fingerprint.get('type', 'Generic'),
                        'banner': fingerprint.get('banner', ''),
                        'http_data': fingerprint if fingerprint.get('type') == 'HTTP' else None,
                        'firmware': fingerprint.get('firmware', '')
                    })
                except Exception:
                    pass

        hostname = self._get_hostname(ip)
        router_brand = self.detect_router_brand(open_ports)
        is_router = self._is_router_like(open_ports)
        
        if router_brand and router_brand != "Generic Web Device":
            is_router = True
            
        if is_router and router_brand:
            self.scan_stats['routers_found'] += 1

        total_hosts = self.scan_stats.get('total_hosts', 0)
        if open_ports or (not self.ping_check) or total_hosts == 1:
            return {
                'ip': ip,
                'hostname': hostname,
                'open_ports': open_ports,
                'is_router': is_router,
                'router_brand': router_brand if is_router else ""
            }
        return None

    def run_scan(self):
        try:
            ip_list = self.generate_ip_list()
        except Exception as e:
            self.console.print(f"[bold red]✗ Error: {e}[/bold red]")
            return

        start_time = time.time()
        lock = threading.Lock()

        with tqdm(total=len(ip_list), desc="[Scanning network]", unit="host", dynamic_ncols=True, 
                 bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}]") as pbar:
            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                future_to_ip = {executor.submit(self.scan_host, ip): ip for ip in ip_list}
                
                for future in as_completed(future_to_ip):
                    host_data = None
                    try:
                        host_data = future.result()
                    except Exception:
                        pass
                    
                    with lock:
                        if host_data:
                            self.discovered_hosts.append(host_data)
                            self.scan_stats['active_hosts'] += 1
                            self.scan_stats['open_ports'] += len(host_data['open_ports'])
                        
                        pbar.set_postfix({
                            "hosts_found": self.scan_stats['active_hosts'], 
                            "routers": self.scan_stats['routers_found']
                        })
                        pbar.update(1)

        self.scan_stats['scan_duration'] = time.time() - start_time

    def display_results(self):
        if not self.discovered_hosts:
            self.console.print(Panel("[yellow]ⓘ No active hosts discovered[/yellow]", 
                                   border_style="yellow", box=box.ROUNDED))
            return

        self.discovered_hosts.sort(key=lambda x: (x['is_router'], len(x['open_ports'])), reverse=True)

        self.console.print(Panel("[bold cyan]🌐 NETWORK DISCOVERY RESULTS[/bold cyan]", 
                               border_style="cyan", box=box.DOUBLE))

        hosts_table = Table(border_style="cyan", show_header=True, header_style="bold white", 
                          box=box.HEAVY, show_lines=False)
        hosts_table.add_column("#", style="cyan", width=4, justify="center")
        hosts_table.add_column("IP Address", style="bold white", width=30, overflow="fold")
        hosts_table.add_column("Hostname", style="white", width=30, overflow="fold")
        hosts_table.add_column("Status", style="white", width=30, justify="center", overflow="fold")
        hosts_table.add_column("Brand", style="yellow", width=30, overflow="fold")
        hosts_table.add_column("Open Ports", style="green", width=30, overflow="fold")

        for i, host in enumerate(self.discovered_hosts, 1):
            router_brand = host.get('router_brand', '')
            if router_brand == "Generic Web Device" and not host['is_router']:
                display_brand = "[dim]-[/dim]"
            elif router_brand:
                display_brand = router_brand
            else:
                display_brand = "[dim]-[/dim]"

            status = "[bold red]ROUTER[/bold red]" if host['is_router'] else "[bold cyan]HOST[/bold cyan]"

            if host['open_ports']:
                ports_text = ", ".join([f"{p['port']}/{p['service']}" for p in host['open_ports'][:3]])
                if len(host['open_ports']) > 3:
                    ports_text += f" [+{len(host['open_ports'])-3}]"
            else:
                ports_text = "[dim]none[/dim]"

            hosts_table.add_row(
                str(i), 
                host['ip'], 
                host['hostname'] or "[dim]-[/dim]", 
                status, 
                display_brand, 
                ports_text
            )

        self.console.print(hosts_table)
        self.console.print("")

        router_count = sum(1 for host in self.discovered_hosts if host['is_router'])
        router_brands = set(
            h['router_brand'] for h in self.discovered_hosts 
            if h['is_router'] and h['router_brand'] and h['router_brand'] != "Generic Web Device"
        )

        summary_table = Table(show_header=True, header_style="bold green", box=box.SIMPLE, show_lines=False)
        summary_table.add_column("Metric", style="bold white", width=20)
        summary_table.add_column("Output", style="white", width=30)
        summary_table.add_row("Hosts Discovered", f"[cyan]{self.scan_stats['active_hosts']}[/cyan]/[dim]{self.scan_stats['total_hosts']}[/dim]")
        summary_table.add_row("Open Ports", f"[green]{self.scan_stats['open_ports']}[/green]")
        summary_table.add_row("Routers Found", f"[red]{router_count}[/red]")
        summary_table.add_row("Scan Duration", f"[yellow]{self.scan_stats['scan_duration']:.1f}s[/yellow]")

        if router_brands:
            brands_text = ", ".join(router_brands)
            summary_table.add_row("Router Brands", f"[magenta]{brands_text}[/magenta]")

        self.console.print(Panel(summary_table, 
                               title="[bold green][*] SCAN COMPLETE [*][/bold green]", 
                               border_style="green", box=box.DOUBLE))

def run(session, options):
    console = Console()
    target = options.get("target", "192.168.1.1")
    ports_config = options.get("ports", "router")
    timeout = options.get("timeout", "4")
    max_threads = options.get("threads", "10")
    ping_check = str(options.get("ping_check", "false")).lower() == "true"

    console.print(Panel(
        "[bold cyan]⚡ ROUTER NETWORK SCANNER[/bold cyan]\n[white]Advanced Network Discovery Tool[/white]",
        border_style="cyan", box=box.DOUBLE
    ))

    config_table = Table(show_header=True, header_style="bold blue", box=box.SIMPLE, show_lines=False, width=50)
    config_table.add_column("Setting", style="bold white", width=15)
    config_table.add_column("Output", style="white", width=35)
    config_table.add_row("Target", f"[cyan]{target}[/cyan]")
    config_table.add_row("Ports", f"[yellow]{ports_config}[/yellow]")
    config_table.add_row("Threads", f"[green]{max_threads}[/green]")
    config_table.add_row("Timeout", f"[magenta]{timeout}s[/magenta]")
    
    console.print(Panel(config_table, 
                       title="[bold blue][*] SCAN CONFIGURATION [*][/bold blue]", 
                       border_style="blue", box=box.ROUNDED))
    console.print("")

    scanner = NetworkScanner(
        console=console, 
        target=target, 
        ports=ports_config, 
        timeout=timeout,
        max_threads=max_threads, 
        ping_check=ping_check
    )

    try:
        scanner.run_scan()
        console.print("")
        scanner.display_results()
    except KeyboardInterrupt:
        console.print(Panel("[yellow]⚠ Scan interrupted by user[/yellow]", 
                          border_style="yellow", box=box.ROUNDED))
    except Exception as e:
        console.print(Panel(f"[red]✗ Error: {e}[/red]", 
                          border_style="red", box=box.ROUNDED))

if __name__ == "__main__":
    test_options = {
        "target": "192.168.1.1",
        "ports": "router",
        "timeout": "4",
        "threads": "10",
        "ping_check": "false"
    }
    
    class DummySession:
        pass
    
    run(DummySession(), test_options)
