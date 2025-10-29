"""
FTP Service Scanner - OOP Version with Comprehensive Scanning
"""

MODULE_INFO = {
    "description": "FTP service scanner"
}

OPTIONS = {
    "host": {
        "type": "str", 
        "description": "Target host IP address or hostname",
        "required": True,
        "default": ""
    },
    "port": {
        "type": "int",
        "description": "FTP port to scan",
        "required": False,
        "default": 21
    },
    "timeout": {
        "type": "int",
        "description": "Connection timeout in seconds", 
        "required": False,
        "default": 10
    },
    "scan_version": {
        "type": "bool",
        "description": "Perform version detection",
        "required": False,
        "default": True
    },
    "check_vulnerabilities": {
        "type": "bool",
        "description": "Check for common vulnerabilities",
        "required": False, 
        "default": True
    },
    "scan_range": {
        "type": "str",
        "description": "Port range to scan (e.g., 20-25)",
        "required": False,
        "default": ""
    }
}

import socket
import re
from typing import Dict, List, Tuple, Optional

class FTPScanner:
    """FTP Service Scanner Class"""
    
    def __init__(self, host: str, port: int = 21, timeout: int = 10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.results = {}
        
    def check_connectivity(self) -> bool:
        """Check basic connectivity to target"""
        try:
            socket.create_connection((self.host, self.port), self.timeout)
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
    
    def get_banner(self) -> Tuple[bool, str]:
        """Retrieve FTP service banner"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            
            # Receive banner
            banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
            sock.close()
            
            return True, banner
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def analyze_banner(self, banner: str) -> Dict[str, str]:
        """Analyze banner for service identification"""
        analysis = {
            'service': 'Unknown',
            'version': 'Unknown', 
            'vendor': 'Unknown',
            'vulnerable': 'Unknown'
        }
        
        # vsFTPd detection
        if 'vsFTPd' in banner:
            analysis['service'] = 'vsFTPd'
            version_match = re.search(r'vsFTPd\s+([\d.]+)', banner)
            if version_match:
                analysis['version'] = version_match.group(1)
                # Check for vulnerable version
                if analysis['version'] == '2.3.4':
                    analysis['vulnerable'] = 'YES - Backdoor vulnerability'
        
        # ProFTPD detection
        elif 'ProFTPD' in banner:
            analysis['service'] = 'ProFTPD'
            version_match = re.search(r'ProFTPD\s+([\d.]+)', banner)
            if version_match:
                analysis['version'] = version_match.group(1)
        
        # Pure-FTPd detection
        elif 'Pure-FTPd' in banner:
            analysis['service'] = 'Pure-FTPd'
            version_match = re.search(r'Pure-FTPd\s+([\d.]+)', banner)
            if version_match:
                analysis['version'] = version_match.group(1)
        
        # Microsoft FTP Service
        elif 'Microsoft FTP Service' in banner:
            analysis['service'] = 'Microsoft FTP'
            analysis['vendor'] = 'Microsoft'
        
        return analysis
    
    def check_anonymous_login(self) -> Tuple[bool, str]:
        """Check if anonymous login is allowed"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            
            # Read banner
            sock.recv(1024)
            
            # Try anonymous login
            sock.send(b"USER anonymous\r\n")
            user_response = sock.recv(1024).decode('utf-8', errors='ignore')
            
            if "331" in user_response:  # Password required
                sock.send(b"PASS anonymous@\r\n")
                pass_response = sock.recv(1024).decode('utf-8', errors='ignore')
                
                if "230" in pass_response:  # Login successful
                    sock.close()
                    return True, "Anonymous login allowed"
            
            sock.close()
            return False, "Anonymous login not allowed"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def scan_port_range(self, start_port: int, end_port: int) -> List[Tuple[int, str]]:
        """Scan a range of ports for FTP services"""
        open_ports = []
        
        print(f"[*] Scanning ports {start_port}-{end_port}...")
        for port in range(start_port, end_port + 1):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((self.host, port))
                
                if result == 0:
                    # Quick banner grab
                    try:
                        banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
                        if 'FTP' in banner or '220' in banner:
                            open_ports.append((port, banner[:100]))  # First 100 chars
                    except:
                        open_ports.append((port, "No banner"))
                
                sock.close()
                
            except Exception:
                continue
        
        return open_ports
    
    def check_common_vulnerabilities(self, service: str, version: str) -> List[str]:
        """Check for common vulnerabilities based on service and version"""
        vulnerabilities = []
        
        # vsFTPd vulnerabilities
        if service == 'vsFTPd':
            if version == '2.3.4':
                vulnerabilities.append("CVE-2011-2523 - Backdoor command execution")
            
            if version.startswith('2.'):
                vulnerabilities.append("Potential buffer overflow vulnerabilities")
                vulnerabilities.append("Potential directory traversal issues")
        
        # ProFTPD vulnerabilities  
        elif service == 'ProFTPD':
            if version.startswith('1.3'):
                vulnerabilities.append("Potential mod_copy vulnerability")
                vulnerabilities.append("Potential command injection issues")
        
        # General FTP vulnerabilities
        vulnerabilities.append("Anonymous login should be disabled")
        vulnerabilities.append("FTP traffic is unencrypted (consider SFTP/FTPS)")
        vulnerabilities.append("Brute force attacks possible")
        
        return vulnerabilities
    
    def comprehensive_scan(self, scan_version: bool = True, check_vuln: bool = True) -> Dict:
        """Perform comprehensive FTP scan"""
        print(f"[*] Starting comprehensive FTP scan for {self.host}:{self.port}")
        
        # 1. Basic connectivity check
        print("[*] Step 1: Checking connectivity...")
        if not self.check_connectivity():
            return {"error": f"Cannot connect to {self.host}:{self.port}"}
        print("[+] Target is reachable")
        
        # 2. Banner grabbing
        print("[*] Step 2: Retrieving service banner...")
        banner_success, banner = self.get_banner()
        if not banner_success:
            return {"error": f"Failed to retrieve banner: {banner}"}
        
        print(f"[+] Banner retrieved: {banner}")
        self.results['banner'] = banner
        
        # 3. Banner analysis
        print("[*] Step 3: Analyzing banner...")
        analysis = self.analyze_banner(banner)
        self.results['analysis'] = analysis
        
        print(f"    Service: {analysis['service']}")
        print(f"    Version: {analysis['version']}")
        print(f"    Vulnerable: {analysis['vulnerable']}")
        
        # 4. Anonymous login check
        print("[*] Step 4: Checking anonymous login...")
        anonymous_allowed, anonymous_msg = self.check_anonymous_login()
        self.results['anonymous_login'] = {
            'allowed': anonymous_allowed,
            'message': anonymous_msg
        }
        print(f"    Anonymous Login: {anonymous_msg}")
        
        # 5. Vulnerability assessment
        if check_vuln and scan_version:
            print("[*] Step 5: Vulnerability assessment...")
            vulnerabilities = self.check_common_vulnerabilities(
                analysis['service'], 
                analysis['version']
            )
            self.results['vulnerabilities'] = vulnerabilities
            
            for i, vuln in enumerate(vulnerabilities, 1):
                print(f"    {i}. {vuln}")
        
        # 6. Port range scanning if specified
        if hasattr(self, 'scan_range') and self.scan_range:
            print("[*] Step 6: Scanning additional ports...")
            start, end = map(int, self.scan_range.split('-'))
            open_ports = self.scan_port_range(start, end)
            self.results['additional_ports'] = open_ports
            
            if open_ports:
                print(f"[+] Found {len(open_ports)} additional open ports:")
                for port, banner in open_ports:
                    print(f"    Port {port}: {banner}")
            else:
                print("[-] No additional FTP ports found")
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate a comprehensive scan report"""
        if not self.results:
            return "No scan results available"
        
        report = []
        report.append("=" * 60)
        report.append("FTP SCAN REPORT")
        report.append("=" * 60)
        report.append(f"Target: {self.host}:{self.port}")
        report.append("")
        
        if 'error' in self.results:
            report.append(f"ERROR: {self.results['error']}")
            return "\n".join(report)
        
        # Banner information
        report.append("SERVICE INFORMATION:")
        report.append("-" * 30)
        report.append(f"Banner: {self.results.get('banner', 'N/A')}")
        
        if 'analysis' in self.results:
            analysis = self.results['analysis']
            report.append(f"Service: {analysis.get('service', 'Unknown')}")
            report.append(f"Version: {analysis.get('version', 'Unknown')}")
            report.append(f"Vulnerability Status: {analysis.get('vulnerable', 'Unknown')}")
        
        # Security findings
        report.append("")
        report.append("SECURITY ASSESSMENT:")
        report.append("-" * 30)
        
        if 'anonymous_login' in self.results:
            anonymous = self.results['anonymous_login']
            status = "ALLOWED" if anonymous['allowed'] else "NOT ALLOWED"
            report.append(f"Anonymous Login: {status}")
        
        if 'vulnerabilities' in self.results:
            report.append("")
            report.append("POTENTIAL VULNERABILITIES:")
            for vuln in self.results['vulnerabilities']:
                report.append(f"  • {vuln}")
        
        # Additional ports
        if 'additional_ports' in self.results and self.results['additional_ports']:
            report.append("")
            report.append("ADDITIONAL FTP PORTS:")
            for port, banner in self.results['additional_ports']:
                report.append(f"  Port {port}: {banner}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)

def run(session, options):
    """Main function called by the framework"""
    host = options.get("host", "")
    port = int(options.get("port", 21))
    timeout = int(options.get("timeout", 10))
    scan_version = options.get("scan_version", True)
    check_vuln = options.get("check_vulnerabilities", True)
    scan_range = options.get("scan_range", "")
    
    if not host:
        print("[!] Error: Host option is required")
        return False
    
    # Initialize scanner
    scanner = FTPScanner(host, port, timeout)
    
    # Set additional options
    if scan_range:
        scanner.scan_range = scan_range
    
    try:
        # Perform comprehensive scan
        results = scanner.comprehensive_scan(scan_version, check_vuln)
        
        # Generate and print report
        report = scanner.generate_report()
        print("\n" + report)
        
        # Return success if no errors
        return 'error' not in results
        
    except Exception as e:
        print(f"[!] Scan failed: {e}")
        return False
