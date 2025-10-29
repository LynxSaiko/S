#!/usr/bin/env python3

import requests
import yaml
import json
import time
import threading
from queue import Queue
from urllib.parse import urlparse, parse_qs
import re

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress
    from rich.text import Text
    from rich import box
    from rich.columns import Columns
    from rich.align import Align
    from tqdm import tqdm
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False

MODULE_INFO = {
    "name": "Advanced Vulnerability Scanner",
    "description": "Comprehensive web vulnerability scanner with multiple attack vectors",
    "author": "Lazy Framework",
    "dependencies": ["requests", "rich", "pyyaml", "tqdm"],
    "platform": "Multi-platform",
    "rank": "Excellent"
}

OPTIONS = {
    "TARGET_URL": {
        "required": True,
        "default": "",
        "description": "Target URL to scan"
    },
    "SCAN_TYPE": {
        "required": False,
        "default": "all",
        "description": "Scan type: all, sqli, xss, rce, lfi, rfi, xxe, idor, ssti, ssrf"
    },
    "METHOD": {
        "required": False,
        "default": "GET",
        "description": "HTTP method (GET/POST)"
    },
    "POST_DATA": {
        "required": False,
        "default": "",
        "description": "POST data (format: param1=value1&param2=value2 OR JSON)"
    },
    "PAYLOAD_FILE": {
        "required": False,
        "default": "payloads.yaml",
        "description": "YAML file containing payloads"
    },
    "THREADS": {
        "required": False,
        "default": "10",
        "description": "Number of threads"
    },
    "TIMEOUT": {
        "required": False,
        "default": "10",
        "description": "Request timeout"
    },
    "COOKIES": {
        "required": False,
        "default": "",
        "description": "Authentication cookies (JSON format)"
    },
    "HEADERS": {
        "required": False,
        "default": "{}",
        "description": "Custom headers (JSON format)"
    }
}

class PayloadManager:
    """Manage payloads from YAML files"""
    
    def __init__(self, payload_file="payloads.yaml"):
        self.payload_file = payload_file
        self.payloads = {}
        self.severity_levels = {
            'critical': ['🔴', 'red'],
            'high': ['🟠', 'yellow'], 
            'medium': ['🟡', 'green'],
            'low': ['🔵', 'blue'],
            'info': ['⚪', 'white']
        }
        self.load_payloads()
    
    def load_payloads(self):
        """Load payloads from YAML files"""
        try:
            with open(self.payload_file, 'r', encoding='utf-8') as f:
                self.payloads = yaml.safe_load(f) or {}
            
            if RICH_AVAILABLE:
                console.print(f"✅ [green]Loaded {self.count_payloads()} payloads[/green]")
                
        except FileNotFoundError:
            if RICH_AVAILABLE:
                console.print(f"❌ [red]Payload file not found: {self.payload_file}[/red]")
            self.payloads = self.get_default_payloads()
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"❌ [red]Error loading payloads: {e}[/red]")
            self.payloads = self.get_default_payloads()
    
    def count_payloads(self):
        """Count total number of payloads"""
        count = 0
        for category in self.payloads.values():
            for payload_list in category.values():
                count += len(payload_list)
        return count
    
    def get_payloads_by_type(self, scan_type):
        """Get payloads for specific scan type"""
        scan_type = scan_type.lower()
        type_mapping = {
            'sqli': 'sql_injection',
            'xss': 'xss',
            'rce': 'rce',
            'lfi': 'lfi',
            'rfi': 'rfi',
            'xxe': 'xxe',
            'idor': 'idor',
            'ssti': 'ssti',
            'ssrf': 'ssrf'
        }
        
        payload_category = type_mapping.get(scan_type, scan_type)
        return self.payloads.get(payload_category, {})
    
    def get_severity_for_vulnerability(self, vuln_type, payload):
        """Determine severity level for vulnerability"""
        severity_rules = {
            'sql_injection': {
                'union': 'critical',
                'stacked': 'critical',
                'rce': 'critical',
                'auth_bypass': 'high',
                'error_based': 'high',
                'time_based': 'medium',
                'blind': 'medium',
                'basic': 'low'
            },
            'xss': {
                'stored': 'high',
                'reflected': 'medium',
                'dom': 'medium',
                'basic': 'low'
            },
            'rce': {
                'code_execution': 'critical',
                'command_injection': 'critical',
                'basic': 'high'
            },
            'lfi': {
                'rce': 'critical',
                'sensitive_data': 'high',
                'basic': 'medium'
            },
            'xxe': {
                'external_entity': 'critical',
                'data_exfiltration': 'high'
            },
            'idor': {
                'data_access': 'high',
                'basic': 'medium'
            }
        }
        
        default_severity = 'medium'
        
        for category, rules in severity_rules.items():
            if category in vuln_type.lower():
                for pattern, severity in rules.items():
                    if pattern in payload.lower():
                        return severity
                return rules.get('basic', default_severity)
        
        return default_severity
    
    def get_severity_display(self, severity):
        """Get severity display with icon and color"""
        icon, color = self.severity_levels.get(severity, ['⚪', 'white'])
        return f"[{color}]{icon} {severity.upper()}[/{color}]"
    
    def get_default_payloads(self):
        """Fallback default payloads"""
        return {
            'sql_injection': {
                'basic': ["'", "''", "' OR '1'='1", "' UNION SELECT 1,2,3--"]
            },
            'xss': {
                'basic': ["<script>alert('XSS')</script>", "<img src=x onerror=alert(1)>"]
            }
        }

class VulnerabilityScanner:
    """Main vulnerability scanner class"""
    
    def __init__(self, options):
        self.options = options
        self.target_url = options.get("TARGET_URL", "")
        self.scan_type = options.get("SCAN_TYPE", "all")
        self.method = options.get("METHOD", "GET").upper()
        self.post_data = options.get("POST_DATA", "")
        self.threads = int(options.get("THREADS", 10))
        self.timeout = int(options.get("TIMEOUT", 10))
        
        self.payload_manager = PayloadManager(options.get("PAYLOAD_FILE", "payloads.yaml"))
        self.session = requests.Session()
        self.setup_session()
        
        self.vulnerabilities = []
        self.tested_payloads = 0
        self.lock = threading.Lock()
        self.severity_counts = {
            'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0
        }
    
    def setup_session(self):
        """Setup HTTP session with headers and cookies"""
        try:
            headers = json.loads(self.options.get("HEADERS", "{}"))
            self.session.headers.update(headers)
        except:
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            })
        
        try:
            cookies = json.loads(self.options.get("COOKIES", "{}"))
            self.session.cookies.update(cookies)
        except:
            pass
    
    def parse_parameters(self):
        """Parse parameters from URL (GET) or POST data"""
        parameters = {}
        
        if self.method == "GET":
            parsed_url = urlparse(self.target_url)
            query_params = parse_qs(parsed_url.query)
            for param_name, values in query_params.items():
                if values:
                    parameters[f"GET_{param_name}"] = values[0]
        
        elif self.method == "POST" and self.post_data:
            if self.post_data.strip().startswith('{'):
                try:
                    json_data = json.loads(self.post_data)
                    for key, value in json_data.items():
                        parameters[f"POST_{key}"] = str(value)
                except:
                    pass
            else:
                for pair in self.post_data.split('&'):
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        parameters[f"POST_{key.strip()}"] = value.strip()
        
        return parameters
    
    def scan(self):
        """Main scan method"""
        if RICH_AVAILABLE:
            console.print(Panel(
                "[bold cyan]🚀 STARTING VULNERABILITY SCAN[/bold cyan]",
                border_style="cyan", box=box.DOUBLE
            ))
        
        parameters = self.parse_parameters()
        
        if not parameters:
            if RICH_AVAILABLE:
                console.print(Panel(
                    "[yellow]ⓘ No parameters found to test[/yellow]",
                    border_style="yellow", box=box.ROUNDED
                ))
            return
        
        if RICH_AVAILABLE:
            console.print(f"🔍 [cyan]Found {len(parameters)} parameters to test[/cyan]")
        
        start_time = time.time()
        
        if self.scan_type == "all":
            self.scan_all_vulnerabilities(parameters)
        else:
            self.scan_specific_vulnerability(parameters, self.scan_type)
        
        elapsed_time = time.time() - start_time
        self.display_results(elapsed_time)
    
    def scan_all_vulnerabilities(self, parameters):
        """Scan for all vulnerability types"""
        scan_types = ['sqli', 'xss', 'rce', 'lfi', 'rfi', 'xxe', 'idor', 'ssti', 'ssrf']
        
        for scan_type in scan_types:
            if RICH_AVAILABLE:
                console.print(f"🔍 [yellow]Scanning for {scan_type.upper()}...[/yellow]")
            self.scan_specific_vulnerability(parameters, scan_type)
    
    def scan_specific_vulnerability(self, parameters, scan_type):
        """Scan for specific vulnerability type"""
        payloads_data = self.payload_manager.get_payloads_by_type(scan_type)
        
        if not payloads_data:
            if RICH_AVAILABLE:
                console.print(f"❌ [red]No payloads found for {scan_type}[/red]")
            return
        
        queue = Queue()
        
        for param_name, original_value in parameters.items():
            for subcategory, payload_list in payloads_data.items():
                for payload in payload_list:
                    queue.put((param_name, original_value, payload, scan_type, subcategory))
        
        total_payloads = queue.qsize()
        if RICH_AVAILABLE:
            console.print(f"📊 [cyan]Testing {total_payloads} payload combinations[/cyan]")
        
        with tqdm(total=total_payloads, desc=f"[Scanning {scan_type}]", unit="pwd", 
                 dynamic_ncols=True, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}]") as pbar:
            
            threads = []
            for i in range(min(self.threads, total_payloads)):
                thread = threading.Thread(target=self.worker, args=(queue, scan_type, pbar))
                thread.daemon = True
                thread.start()
                threads.append(thread)
            
            queue.join()
            
            for thread in threads:
                thread.join(timeout=1)
    
    def worker(self, queue, scan_type, pbar):
        """Worker thread for scanning"""
        while not queue.empty():
            try:
                param_name, original_value, payload, vuln_type, subcategory = queue.get(timeout=1)
                self.test_payload(param_name, original_value, payload, vuln_type, subcategory)
                queue.task_done()
                pbar.update(1)
            except:
                break
    
    def test_payload(self, param_name, original_value, payload, vuln_type, subcategory):
        """Test a single payload"""
        try:
            if self.method == "GET":
                response = self.send_get_request(param_name, payload)
            else:
                response = self.send_post_request(param_name, payload)
            
            if response and self.detect_vulnerability(response, payload, vuln_type):
                severity = self.payload_manager.get_severity_for_vulnerability(vuln_type, payload)
                
                with self.lock:
                    self.vulnerabilities.append({
                        'type': vuln_type.upper(),
                        'parameter': param_name,
                        'payload': payload,
                        'severity': severity,
                        'subcategory': subcategory,
                        'response_code': response.status_code,
                        'response_length': len(response.text),
                        'url': response.url
                    })
                    self.severity_counts[severity] += 1
            
            self.tested_payloads += 1
            
        except Exception as e:
            pass
    
    def send_get_request(self, param_name, payload):
        """Send GET request with injected payload"""
        parsed_url = urlparse(self.target_url)
        query_params = parse_qs(parsed_url.query)
        
        modified_params = {}
        param_key = param_name.replace('GET_', '')
        
        for key, values in query_params.items():
            if key == param_key:
                modified_params[key] = payload
            else:
                modified_params[key] = values[0] if values else ""
        
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        new_query = "&".join([f"{k}={v}" for k, v in modified_params.items()])
        target_url = f"{base_url}?{new_query}" if new_query else base_url
        
        return self.session.get(target_url, timeout=self.timeout, verify=False)
    
    def send_post_request(self, param_name, payload):
        """Send POST request with injected payload"""
        post_data = {}
        
        if self.post_data.strip().startswith('{'):
            try:
                post_data = json.loads(self.post_data)
            except:
                for pair in self.post_data.split('&'):
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        post_data[key.strip()] = value.strip()
        else:
            for pair in self.post_data.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    post_data[key.strip()] = value.strip()
        
        param_key = param_name.replace('POST_', '')
        if param_key in post_data:
            post_data[param_key] = payload
        
        headers = {}
        if self.post_data.strip().startswith('{'):
            headers['Content-Type'] = 'application/json'
            return self.session.post(
                self.target_url, 
                json=post_data, 
                timeout=self.timeout, 
                verify=False,
                headers=headers
            )
        else:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            return self.session.post(
                self.target_url, 
                data=post_data, 
                timeout=self.timeout, 
                verify=False,
                headers=headers
            )
    
    def detect_vulnerability(self, response, payload, vuln_type):
        """Detect vulnerability based on response"""
        content = response.text.lower()
        
        detection_methods = {
            'sqli': self.detect_sqli,
            'xss': self.detect_xss,
            'rce': self.detect_rce,
            'lfi': self.detect_lfi,
            'xxe': self.detect_xxe,
            'idor': self.detect_idor,
            'ssti': self.detect_ssti
        }
        
        detector = detection_methods.get(vuln_type.lower())
        if detector:
            return detector(response, payload)
        
        return False
    
    def detect_sqli(self, response, payload):
        content = response.text.lower()
        error_indicators = [
            'sql syntax', 'mysql', 'ora-', 'postgresql', 'microsoft odbc',
            'driver', 'data type', 'procedure', 'trigger', 'violation'
        ]
        return any(indicator in content for indicator in error_indicators)
    
    def detect_xss(self, response, payload):
        return payload in response.text
    
    def detect_rce(self, response, payload):
        content = response.text
        rce_indicators = ['uid=', 'gid=', 'root:', 'www-data:']
        return any(indicator in content for indicator in rce_indicators)
    
    def detect_lfi(self, response, payload):
        content = response.text
        lfi_indicators = ['root:', 'daemon:', 'etc/passwd', '[boot loader]']
        return any(indicator in content for indicator in lfi_indicators)
    
    def detect_xxe(self, response, payload):
        content = response.text
        xxe_indicators = ['root:', '/etc/passwd', '[boot loader]']
        return any(indicator in content for indicator in xxe_indicators)
    
    def detect_idor(self, response, payload):
        return response.status_code == 200 and len(response.text) > 100
    
    def detect_ssti(self, response, payload):
        content = response.text
        if '49' in content and '7*7' in payload:
            return True
        return 'config' in content or 'runtime' in content
    
    def display_results(self, elapsed_time):
        """Display scan results"""
        if not RICH_AVAILABLE:
            return
        
        console.print("\n" + "="*60)
        
        if self.vulnerabilities:
            severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
            self.vulnerabilities.sort(key=lambda x: severity_order.get(x['severity'], 5))
            
            vuln_table = Table(
                title="🚨 VULNERABILITIES DISCOVERED",
                box=box.DOUBLE_EDGE,
                header_style="bold red",
                show_lines=False
            )
            
            vuln_table.add_column("#", style="cyan", width=4, justify="center")
            vuln_table.add_column("Severity", style="bold white", width=12)
            vuln_table.add_column("Type", style="yellow", width=15)
            vuln_table.add_column("Parameter", style="magenta", width=20)
            vuln_table.add_column("Payload", style="white", width=30)
            vuln_table.add_column("Status", style="green", width=8)
            
            for i, vuln in enumerate(self.vulnerabilities, 1):
                severity_display = self.payload_manager.get_severity_display(vuln['severity'])
                
                display_payload = vuln['payload']
                if len(display_payload) > 25:
                    display_payload = display_payload[:22] + "..."
                
                vuln_table.add_row(
                    str(i),
                    severity_display,
                    vuln['type'],
                    vuln['parameter'].replace('GET_', '').replace('POST_', ''),
                    display_payload,
                    str(vuln['response_code'])
                )
            
            console.print(vuln_table)
            console.print("")
        else:
            console.print(Panel(
                "[green]✅ No vulnerabilities found[/green]",
                border_style="green",
                box=box.ROUNDED
            ))
        
        self.display_summary(elapsed_time)
    
    def display_summary(self, elapsed_time):
        """Display scan summary"""
        summary_table = Table(
            show_header=True, 
            header_style="bold green", 
            box=box.SIMPLE, 
            show_lines=False,
            width=50
        )
        summary_table.add_column("Metric", style="bold white", width=20)
        summary_table.add_column("Value", style="white", width=30)
        
        summary_table.add_row("Scan Duration", f"[yellow]{elapsed_time:.1f}s[/yellow]")
        summary_table.add_row("Payloads Tested", f"[cyan]{self.tested_payloads}[/cyan]")
        summary_table.add_row("Vulnerabilities Found", f"[red]{len(self.vulnerabilities)}[/red]")
        
        for severity, count in self.severity_counts.items():
            if count > 0:
                color = self.payload_manager.severity_levels[severity][1]
                summary_table.add_row(
                    f"{severity.title()} Vulnerabilities", 
                    f"[{color}]{count}[/{color}]"
                )
        
        console.print(Panel(
            summary_table,
            title="[bold green][*] SCAN SUMMARY [*][/bold green]",
            border_style="green",
            box=box.DOUBLE
        ))

def run(session, options):
    """Main function to run the scanner"""
    try:
        scanner = VulnerabilityScanner(options)
        scanner.scan()
    except KeyboardInterrupt:
        if RICH_AVAILABLE:
            console.print(Panel(
                "[yellow]⚠ Scan interrupted by user[/yellow]",
                border_style="yellow",
                box=box.ROUNDED
            ))
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[red]✗ Scanner error: {e}[/red]",
                border_style="red",
                box=box.ROUNDED
            ))
