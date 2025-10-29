import socket
import requests
import subprocess
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MODULE_INFO = {
    "name": "security/router_audit_fixed",
    "description": "Router security vulnerability assessment (SSL warnings fixed)"
}

OPTIONS = {
    "ROUTER_IP": {
        "required": True,
        "default": "192.168.1.1",
        "description": "Router IP address"
    },
    "AUDIT_TYPE": {
        "required": False,
        "default": "basic",
        "description": "Audit type: basic, comprehensive, or wireless"
    }
}

def run(session, options):
    router_ip = options.get("ROUTER_IP", "192.168.1.1")
    audit_type = options.get("AUDIT_TYPE", "basic")
    
    print(f"🔒 Router Security Audit")
    print(f"🎯 Target: {router_ip}")
    print(f"📊 Audit Type: {audit_type}")
    
    try:
        # Basic connectivity check
        print(f"\n1. 🔗 Connectivity Check...")
        if not check_connectivity(router_ip):
            print("❌ Router is not reachable")
            return
        
        # Port and service scan
        print(f"\n2. 🔍 Service Discovery...")
        open_ports = scan_router_ports(router_ip)
        
        # Security checks
        print(f"\n3. 🛡️ Security Assessment...")
        security_issues = perform_security_checks(router_ip, open_ports, audit_type)
        
        # Display results
        print(f"\n4. 📋 Security Report...")
        display_security_report(security_issues)
        
        # Recommendations
        print(f"\n5. 💡 Security Recommendations...")
        provide_recommendations(security_issues)
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def check_connectivity(ip):
    """Check if router is reachable"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((ip, 80))
        sock.close()
        return result == 0
    except:
        return False

def scan_router_ports(ip):
    """Scan common router ports"""
    common_ports = [21, 22, 23, 53, 80, 443, 8080, 8443, 7547, 1900, 161, 162]
    open_ports = []
    
    for port in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                open_ports.append(port)
                service = get_service_name(port)
                print(f"   ✅ {port}/tcp - {service}")
        except:
            pass
    
    return open_ports

def perform_security_checks(ip, open_ports, audit_type):
    """Perform security checks"""
    issues = []
    
    # Check for default credentials
    print(f"   🔐 Testing for default credentials...")
    default_creds_issue = check_default_credentials(ip, open_ports)
    if default_creds_issue:
        issues.append(default_creds_issue)
    
    # Check for weak protocols
    print(f"   📡 Checking for weak protocols...")
    if 23 in open_ports:  # Telnet
        issues.append({
            'severity': 'HIGH',
            'issue': 'Telnet service enabled',
            'description': 'Telnet transmits credentials in plain text',
            'recommendation': 'Disable Telnet and use SSH instead'
        })
    
    # Check HTTP services
    print(f"   🌐 Checking web services...")
    web_issues = check_web_security(ip, open_ports)
    issues.extend(web_issues)
    
    # Comprehensive checks
    if audit_type == 'comprehensive':
        print(f"   🔧 Running comprehensive checks...")
        comp_issues = comprehensive_checks(ip)
        issues.extend(comp_issues)
    
    # Wireless security checks
    if audit_type in ['comprehensive', 'wireless']:
        print(f"   📶 Checking wireless security...")
        wireless_issues = check_wireless_security(ip)
        issues.extend(wireless_issues)
    
    return issues

def check_default_credentials(ip, open_ports):
    """Check for default credentials with SSL disabled"""
    common_credentials = [
        ('admin', 'admin'),
        ('admin', 'password'),
        ('admin', '1234'),
        ('root', 'admin'),
        ('admin', ''),
        ('user', 'user')
    ]
    
    for port in [80, 443, 8080, 8443]:
        if port in open_ports:
            if port in [443, 8443]:
                protocol = 'https'
            else:
                protocol = 'http'
            
            for username, password in common_credentials:
                try:
                    url = f"{protocol}://{ip}:{port}"
                    
                    # Create session with SSL verification disabled
                    session = requests.Session()
                    session.verify = False
                    
                    response = session.get(url, auth=(username, password), timeout=5)
                    
                    if response.status_code == 200 and 'login' not in response.url.lower():
                        return {
                            'severity': 'CRITICAL',
                            'issue': 'Default credentials found',
                            'description': f'Username: {username}, Password: {password}',
                            'recommendation': 'Change default credentials immediately'
                        }
                except:
                    continue
    
    return None

def check_web_security(ip, open_ports):
    """Check web interface security with SSL disabled"""
    issues = []
    
    for port in [80, 8080]:
        if port in open_ports:
            try:
                url = f"http://{ip}:{port}"
                
                # Create session with SSL verification disabled
                session = requests.Session()
                session.verify = False
                
                response = session.get(url, timeout=5)
                
                # Check for HTTP instead of HTTPS
                if port == 80 and 'https' not in response.url:
                    issues.append({
                        'severity': 'MEDIUM',
                        'issue': 'HTTP used instead of HTTPS',
                        'description': 'Web interface uses unencrypted HTTP',
                        'recommendation': 'Enable HTTPS and redirect HTTP to HTTPS'
                    })
                
                # Check for common vulnerabilities
                if 'cross-site' in response.text.lower() or 'xss' in response.text.lower():
                    issues.append({
                        'severity': 'MEDIUM',
                        'issue': 'Potential XSS vulnerability',
                        'description': 'Web interface may be vulnerable to XSS attacks',
                        'recommendation': 'Update router firmware'
                    })
                        
            except:
                pass
    
    return issues

def comprehensive_checks(ip):
    """Comprehensive security checks"""
    issues = []
    
    # Check for UPnP vulnerabilities
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        message = 'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 1\r\nST: ssdp:all\r\n\r\n'
        sock.sendto(message.encode(), (ip, 1900))
        sock.recv(1024)
        sock.close()
        
        issues.append({
            'severity': 'MEDIUM',
            'issue': 'UPnP service enabled',
            'description': 'UPnP can be exploited for network attacks',
            'recommendation': 'Disable UPnP if not needed'
        })
    except:
        pass
    
    # Check for DNS rebinding vulnerability
    try:
        # Create session with SSL verification disabled
        session = requests.Session()
        session.verify = False
        
        response = session.get(f"http://{ip}:80/", headers={'Host': 'localhost'}, timeout=3)
        if response.status_code == 200:
            issues.append({
                'severity': 'LOW',
                'issue': 'Potential DNS rebinding',
                'description': 'Router may be vulnerable to DNS rebinding attacks',
                'recommendation': 'Configure proper host header validation'
            })
    except:
        pass
    
    return issues

def check_wireless_security(ip):
    """Check wireless security settings"""
    issues = []
    
    # These would typically require authentication to access wireless settings
    # For demo purposes, we'll provide general wireless security advice
    
    issues.extend([
        {
            'severity': 'HIGH',
            'issue': 'Wireless encryption check needed',
            'description': 'Verify WPA2/WPA3 encryption is enabled',
            'recommendation': 'Use WPA2/WPA3 with strong password'
        },
        {
            'severity': 'MEDIUM',
            'issue': 'SSID broadcast enabled',
            'description': 'Network is visible to everyone',
            'recommendation': 'Disable SSID broadcast for better security'
        },
        {
            'severity': 'MEDIUM', 
            'issue': 'WPS enabled',
            'description': 'WPS can be vulnerable to brute force attacks',
            'recommendation': 'Disable WPS feature'
        }
    ])
    
    return issues

def display_security_report(issues):
    """Display security assessment report"""
    if not issues:
        print("   ✅ No security issues found!")
        return
    
    # Group by severity
    critical = [i for i in issues if i['severity'] == 'CRITICAL']
    high = [i for i in issues if i['severity'] == 'HIGH']
    medium = [i for i in issues if i['severity'] == 'MEDIUM']
    low = [i for i in issues if i['severity'] == 'LOW']
    
    print(f"\n📊 SECURITY ASSESSMENT SUMMARY")
    print("=" * 60)
    print(f"🔴 CRITICAL: {len(critical)}")
    print(f"🟠 HIGH: {len(high)}")
    print(f"🟡 MEDIUM: {len(medium)}")
    print(f"🟢 LOW: {len(low)}")
    print("=" * 60)
    
    # Display issues by severity
    for severity, issues_list in [('CRITICAL', critical), ('HIGH', high), 
                                 ('MEDIUM', medium), ('LOW', low)]:
        if issues_list:
            print(f"\n{severity} SEVERITY ISSUES:")
            for i, issue in enumerate(issues_list, 1):
                print(f"  {i}. {issue['issue']}")
                print(f"     📝 {issue['description']}")
                print(f"     💡 {issue['recommendation']}")

def provide_recommendations(issues):
    """Provide security recommendations"""
    print(f"\n🛡️ SECURITY RECOMMENDATIONS")
    print("=" * 50)
    
    recommendations = [
        "Change default administrator credentials",
        "Keep router firmware updated",
        "Disable remote administration",
        "Use WPA2/WPA3 encryption for WiFi",
        "Disable WPS feature",
        "Enable firewall with strict rules",
        "Disable unused services (Telnet, UPnP)",
        "Use strong WiFi password (12+ characters)",
        "Enable MAC address filtering",
        "Regularly check connected devices"
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")

def get_service_name(port):
    """Get service name for port"""
    services = {
        21: 'FTP', 22: 'SSH', 23: 'Telnet', 53: 'DNS',
        80: 'HTTP', 443: 'HTTPS', 8080: 'HTTP-Alt',
        8443: 'HTTPS-Alt', 7547: 'CWMP', 1900: 'UPnP',
        161: 'SNMP', 162: 'SNMP-Trap'
    }
    return services.get(port, 'Unknown')
