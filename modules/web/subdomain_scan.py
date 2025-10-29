#!/usr/bin/env python3
"""
Powerful Subdomain Scanner Module
Author: Lazy Framework
Description: Advanced subdomain enumeration with YAML wordlists and multiple techniques
"""

MODULE_INFO = {
    "name": "Advanced Subdomain Scanner",
    "description": "Powerful subdomain enumeration with YAML wordlists, brute force, and DNS techniques",
    "author": "Lazy Framework Team",
    "license": "MIT",
    "dependencies": ["dnspython", "requests", "aiohttp", "asyncio", "pyyaml"],
    "platform": "All",
    "arch": "All", 
    "rank": "Excellent",
}

OPTIONS = {
    "url": {
        "description": "Target domain URL (example.com)",
        "required": True,
        "default": ""
    },
    "wordlist": {
        "description": "Path to custom wordlist file (txt or yaml)",
        "required": False,
        "default": ""
    },
    "wordlist_type": {
        "description": "Type of wordlist: common, large, custom",
        "required": False,
        "default": "common"
    },
    "threads": {
        "description": "Number of threads for brute force",
        "required": False,
        "default": "50"
    },
    "timeout": {
        "description": "DNS query timeout in seconds",
        "required": False,
        "default": "5"
    },
    "recursive": {
        "description": "Enable recursive subdomain discovery (yes/no)",
        "required": False,
        "default": "yes"
    },
    "output": {
        "description": "Output file to save results",
        "required": False,
        "default": ""
    },
    "engine": {
        "description": "Scan engine: brute, dns, all",
        "required": False,
        "default": "all"
    },
    "verbose": {
        "description": "Show verbose output (yes/no)",
        "required": False,
        "default": "yes"
    }
}

import dns.resolver
import dns.exception
import asyncio
import aiohttp
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import os
import sys
import time
from pathlib import Path
import yaml

class SubdomainScanner:
    def __init__(self, domain, threads=50, timeout=5):
        self.domain = domain
        self.threads = threads
        self.timeout = timeout
        self.found_subdomains = set()
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = timeout
        self.resolver.lifetime = timeout
        
        # Common DNS servers
        self.dns_servers = [
            '8.8.8.8', '8.8.4.4',  # Google
            '1.1.1.1', '1.0.0.1',  # Cloudflare
            '9.9.9.9', '149.112.112.112',  # Quad9
            '208.67.222.222', '208.67.220.220',  # OpenDNS
        ]
        
    def load_wordlist(self, wordlist_path=None, wordlist_type="common"):
        """Load wordlist from file or use built-in YAML"""
        wordlist = set()
        
        # Jika custom wordlist diberikan
        if wordlist_path and os.path.exists(wordlist_path):
            try:
                if wordlist_path.endswith(('.yaml', '.yml')):
                    wordlist = self._load_yaml_wordlist(wordlist_path)
                else:
                    # Load dari file teks biasa
                    with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                        wordlist.update(line.strip() for line in f if line.strip())
                print(f"[+] Loaded {len(wordlist)} words from custom wordlist: {wordlist_path}")
            except Exception as e:
                print(f"[-] Error loading custom wordlist: {e}")
                return self._load_builtin_yaml_wordlist(wordlist_type)
        else:
            # Gunakan built-in YAML wordlist
            wordlist = self._load_builtin_yaml_wordlist(wordlist_type)
            print(f"[+] Using built-in {wordlist_type} wordlist with {len(wordlist)} words")
        
        return list(wordlist)
    
    def _load_yaml_wordlist(self, yaml_path):
        """Load wordlist from YAML file"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        wordlist = set()
        
        # Support multiple YAML structures
        if isinstance(data, dict):
            if 'subdomains' in data:
                # Structure: {subdomains: [list]}
                wordlist.update(data['subdomains'])
            elif 'wordlist' in data:
                # Structure: {wordlist: [list]}
                wordlist.update(data['wordlist'])
            elif 'common' in data:
                # Structure: {common: [list], large: [list]}
                for key in data:
                    if isinstance(data[key], list):
                        wordlist.update(data[key])
            else:
                # Assume all top-level lists are wordlists
                for key, value in data.items():
                    if isinstance(value, list):
                        wordlist.update(value)
        elif isinstance(data, list):
            # Direct list of subdomains
            wordlist.update(data)
        
        return wordlist
    
    def _load_builtin_yaml_wordlist(self, wordlist_type="common"):
        """Load built-in wordlist from external YAML file"""
        # Cari file YAML wordlist
        possible_paths = [
            Path(__file__).parent.parent / "wordlists" / "subdomains.yaml",
            Path(__file__).parent / "wordlists" / "subdomains.yaml",
            Path("wordlists") / "subdomains.yaml",
            Path("/usr/share/lazy-framework/wordlists/subdomains.yaml"),
        ]
        
        yaml_path = None
        for path in possible_paths:
            if path.exists():
                yaml_path = path
                break
        
        if not yaml_path:
            print("[-] Built-in YAML wordlist not found. Using minimal fallback wordlist.")
            return self._get_fallback_wordlist()
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            wordlist = set()
            
            # Load berdasarkan tipe yang diminta
            if wordlist_type == "common" and "common" in data:
                wordlist.update(data["common"])
            elif wordlist_type == "large" and "large_wordlist" in data:
                wordlist.update(data["large_wordlist"])
            else:
                # Load semua wordlist yang tersedia
                for category, words in data.items():
                    if isinstance(words, list):
                        wordlist.update(words)
            
            return wordlist
            
        except Exception as e:
            print(f"[-] Error loading built-in YAML wordlist: {e}")
            return self._get_fallback_wordlist()
    
    def _get_fallback_wordlist(self):
        """Fallback wordlist jika YAML tidak ditemukan"""
        return {
            'www', 'api', 'mail', 'ftp', 'admin', 'blog', 'shop', 'forum', 'cdn',
            'static', 'img', 'images', 'media', 'video', 'app', 'apps', 'mobile',
            'secure', 'login', 'account', 'user', 'dashboard', 'panel', 'control',
            'server', 'service', 'portal', 'gateway', 'vpn', 'ssh', 'ssl', 'db',
            'database', 'mysql', 'mongo', 'redis', 'cache', 'proxy', 'backup',
            'archive', 'old', 'new', 'temp', 'tmp', 'beta', 'alpha', 'demo',
            'stage', 'dev', 'test', 'staging', 'prod', 'production', 'development'
        }

    def dns_scan(self, subdomain):
        """Check if subdomain exists via DNS"""
        full_domain = f"{subdomain}.{self.domain}"
        
        for dns_server in self.dns_servers:
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [dns_server]
                resolver.timeout = self.timeout
                resolver.lifetime = self.timeout
                
                answers = resolver.resolve(full_domain, 'A')
                if answers:
                    for answer in answers:
                        ip = answer.to_text()
                        print(f"[+] Found: {full_domain} -> {ip} (via {dns_server})")
                        self.found_subdomains.add((full_domain, ip))
                        return True
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
                continue
            except Exception:
                continue
        
        return False

    async def async_dns_scan(self, session, subdomain):
        """Async DNS scan"""
        return self.dns_scan(subdomain)

    def brute_force_scan(self, wordlist):
        """Brute force subdomains using DNS"""
        print(f"[*] Starting brute force scan with {len(wordlist)} words...")
        
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {executor.submit(self.dns_scan, word): word for word in wordlist}
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    continue

    def certificate_transparency_scan(self):
        """Check Certificate Transparency logs"""
        print("[*] Checking Certificate Transparency logs...")
        ct_urls = [
            f"https://crt.sh/?q=%.{self.domain}&output=json",
            f"https://api.certspotter.com/v1/issuances?domain={self.domain}&include_subdomains=true&expand=dns_names"
        ]
        
        for url in ct_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for entry in data:
                        if 'name_value' in entry:
                            domains = entry['name_value'].split('\n')
                            for domain in domains:
                                if self.domain in domain:
                                    print(f"[+] CT Log: {domain.strip()}")
                                    self.found_subdomains.add((domain.strip(), "CT Log"))
            except Exception as e:
                continue

    def search_engine_scan(self):
        """Search engine discovery (basic)"""
        print("[*] Checking search engines...")
        search_queries = [
            f"site:*.{self.domain}",
            f"inurl:{self.domain}"
        ]
        
        # This is a basic implementation - in real use, you'd use search engine APIs
        print("[!] Search engine scanning requires API keys for comprehensive results")

    def save_results(self, output_file):
        """Save results to file"""
        if output_file and self.found_subdomains:
            try:
                with open(output_file, 'w') as f:
                    for domain, ip in sorted(self.found_subdomains):
                        f.write(f"{domain} -> {ip}\n")
                print(f"[+] Results saved to: {output_file}")
            except Exception as e:
                print(f"[-] Error saving results: {e}")

    def scan(self, wordlist_path=None, wordlist_type="common", recursive=True, output_file=None, engine="all"):
        """Main scan method"""
        start_time = time.time()
        
        print(f"[*] Starting subdomain scan for: {self.domain}")
        print(f"[*] Threads: {self.threads}, Timeout: {self.timeout}s")
        
        # Load wordlist
        wordlist = self.load_wordlist(wordlist_path, wordlist_type)
        
        # Perform scans based on engine selection
        if engine in ["brute", "all"]:
            self.brute_force_scan(wordlist)
        
        if engine in ["dns", "all"]:
            self.certificate_transparency_scan()
        
        if recursive and engine in ["all"]:
            print("[*] Performing recursive discovery...")
            # Find subdomains of found subdomains
            new_domains = [domain for domain, _ in self.found_subdomains]
            for found_domain in new_domains:
                if found_domain != self.domain:
                    sub_domain = found_domain.split('.')[0]
                    scanner = SubdomainScanner(self.domain, self.threads, self.timeout)
                    scanner.brute_force_scan([sub_domain])
                    self.found_subdomains.update(scanner.found_subdomains)
        
        # Save results
        if output_file:
            self.save_results(output_file)
        
        elapsed_time = time.time() - start_time
        print(f"\n[+] Scan completed in {elapsed_time:.2f} seconds")
        print(f"[+] Found {len(self.found_subdomains)} unique subdomains")
        
        return self.found_subdomains

def run(session, options):
    """Main function called by Lazy Framework"""
    url = options.get("url", "").strip()
    if not url:
        print("[-] Error: URL parameter is required")
        return
    
    # Extract domain from URL
    if '://' in url:
        parsed = urlparse(url)
        domain = parsed.netloc
    else:
        domain = url
    
    # Remove www. if present
    if domain.startswith('www.'):
        domain = domain[4:]
    
    wordlist = options.get("wordlist", "").strip()
    wordlist_type = options.get("wordlist_type", "common")
    threads = int(options.get("threads", "50"))
    timeout = int(options.get("timeout", "5"))
    recursive = options.get("recursive", "yes").lower() == "yes"
    output = options.get("output", "").strip()
    engine = options.get("engine", "all")
    verbose = options.get("verbose", "yes").lower() == "yes"
    
    print(f"[*] Target Domain: {domain}")
    print(f"[*] Using engine: {engine}")
    print(f"[*] Wordlist type: {wordlist_type}")
    
    # Validate wordlist file if provided
    if wordlist and not os.path.exists(wordlist):
        print(f"[-] Wordlist file not found: {wordlist}")
        return
    
    # Initialize scanner
    scanner = SubdomainScanner(domain, threads, timeout)
    
    # Perform scan
    try:
        results = scanner.scan(
            wordlist_path=wordlist if wordlist else None,
            wordlist_type=wordlist_type,
            recursive=recursive,
            output_file=output if output else None,
            engine=engine
        )
        
        # Display results
        if results:
            print(f"\n[+] SUBDOMAIN RESULTS:")
            print("-" * 50)
            for domain, ip in sorted(results):
                print(f"{domain} -> {ip}")
        else:
            print("[-] No subdomains found")
            
    except KeyboardInterrupt:
        print("\n[!] Scan interrupted by user")
    except Exception as e:
        print(f"[-] Scan error: {e}")

if __name__ == "__main__":
    # Test function
    test_options = {
        "url": "example.com",
        "threads": "10",
        "timeout": "3",
        "verbose": "yes"
    }
    run({}, test_options)
