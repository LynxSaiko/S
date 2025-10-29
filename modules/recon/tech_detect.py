#!/usr/bin/env python3

import requests
import re
import json
import time
from urllib.parse import urlparse
import hashlib

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.align import Align
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False

MODULE_INFO = {
    "name": "recon/wapplyzer",
    "description": "🌐 Wappalyzer-like Technology Detection - Comprehensive Stack Analysis"
}

OPTIONS = {
    "TARGET": {
        "required": True,
        "default": "https://example.com",
        "description": "Target URL to scan"
    },
    "TIMEOUT": {
        "required": False,
        "default": "10",
        "description": "Request timeout in seconds"
    },
    "DETECT_ANALYTICS": {
        "required": False,
        "default": "true",
        "description": "Detect analytics and tracking tools"
    },
    "DETECT_CDN": {
        "required": False,
        "default": "true",
        "description": "Detect CDN and hosting providers"
    }
}

class WapplyzerDetector:
    def __init__(self, options):
        self.options = options
        self.technologies = {}
        self.session = requests.Session()
        self.setup_session()
        self.load_technology_patterns()
        
    def setup_session(self):
        """Setup HTTP session"""
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def load_technology_patterns(self):
        """Load comprehensive technology patterns like Wappalyzer"""
        self.tech_patterns = {
            # Operating Systems
            'Linux': {
                'category': 'Operating Systems',
                'patterns': [r'linux', r'x11', r'ubuntu', r'debian'],
                'headers': {'Server': [r'linux', r'unix']}
            },
            'Windows': {
                'category': 'Operating Systems', 
                'patterns': [r'windows', r'microsoft', r'asp.net'],
                'headers': {'Server': [r'windows', r'microsoft']}
            },
            
            # Web Servers
            'Apache': {
                'category': 'Web Servers',
                'patterns': [r'apache', r'httpd'],
                'headers': {'Server': [r'apache', r'httpd']}
            },
            'Nginx': {
                'category': 'Web Servers',
                'patterns': [r'nginx'],
                'headers': {'Server': [r'nginx']}
            },
            'IIS': {
                'category': 'Web Servers',
                'patterns': [r'iis', r'microsoft-iis'],
                'headers': {'Server': [r'microsoft-iis', r'iis']}
            },
            'Cloudflare': {
                'category': 'Web Servers',
                'patterns': [r'cloudflare'],
                'headers': {'Server': [r'cloudflare'], 'CF-Ray': [r'.*']}
            },
            
            # Programming Languages
            'PHP': {
                'category': 'Programming Languages',
                'patterns': [r'php', r'\.php\?', r'x-powered-by.*php'],
                'headers': {'X-Powered-By': [r'php']},
                'cookies': ['phpsessid']
            },
            'Python': {
                'category': 'Programming Languages',
                'patterns': [r'python', r'django', r'flask'],
                'headers': {'X-Powered-By': [r'python']}
            },
            'Node.js': {
                'category': 'Programming Languages', 
                'patterns': [r'node\.js', r'express'],
                'headers': {'X-Powered-By': [r'node\.js', r'express']}
            },
            'Ruby': {
                'category': 'Programming Languages',
                'patterns': [r'ruby', r'rails', r'rack'],
                'headers': {'X-Powered-By': [r'ruby', r'rails']},
                'cookies': ['_rails_app']
            },
            'Java': {
                'category': 'Programming Languages',
                'patterns': [r'java', r'jsp', r'servlet'],
                'headers': {'X-Powered-By': [r'java', r'jsp']}
            },
            'ASP.NET': {
                'category': 'Programming Languages',
                'patterns': [r'asp\.net', r'\.aspx', r'viewstate'],
                'headers': {'X-Powered-By': [r'asp\.net']}
            },
            
            # JavaScript Frameworks
            'React': {
                'category': 'JavaScript Frameworks',
                'patterns': [r'react', r'react\.js', r'react-dom'],
                'scripts': [r'react', r'react\.min\.js']
            },
            'Vue.js': {
                'category': 'JavaScript Frameworks',
                'patterns': [r'vue', r'vue\.js', r'vue-router'],
                'scripts': [r'vue', r'vue\.min\.js']
            },
            'Angular': {
                'category': 'JavaScript Frameworks',
                'patterns': [r'angular', r'ng-', r'angular\.js'],
                'scripts': [r'angular', r'angular\.min\.js']
            },
            'jQuery': {
                'category': 'JavaScript Frameworks',
                'patterns': [r'jquery', r'\$\.', r'jquery\.min\.js'],
                'scripts': [r'jquery']
            },
            'Next.js': {
                'category': 'JavaScript Frameworks',
                'patterns': [r'next', r'__next', r'_next/static'],
                'headers': {'X-Powered-By': [r'next\.js']}
            },
            'Nuxt.js': {
                'category': 'JavaScript Frameworks',
                'patterns': [r'nuxt', r'_nuxt'],
                'headers': {'X-Powered-By': [r'nuxt']}
            },
            
            # CMS
            'WordPress': {
                'category': 'CMS',
                'patterns': [r'wp-content', r'wp-includes', r'wordpress', r'/wp-json/'],
                'headers': {'X-Powered-By': [r'wordpress']},
                'meta': {'generator': [r'wordpress']}
            },
            'Joomla': {
                'category': 'CMS',
                'patterns': [r'joomla', r'/media/jui/', r'/media/system/'],
                'meta': {'generator': [r'joomla']}
            },
            'Drupal': {
                'category': 'CMS',
                'patterns': [r'drupal', r'sites/default/', r'/core/assets/'],
                'meta': {'generator': [r'drupal']},
                'headers': {'X-Generator': [r'drupal']}
            },
            'Magento': {
                'category': 'CMS',
                'patterns': [r'magento', r'/static/version', r'/mage/'],
                'meta': {'generator': [r'magento']}
            },
            'Shopify': {
                'category': 'CMS',
                'patterns': [r'shopify', r'cdn\.shopify\.com'],
                'scripts': [r'shopify']
            },
            'WooCommerce': {
                'category': 'CMS',
                'patterns': [r'woocommerce', r'/wp-content/plugins/woocommerce/']
            },
            
            # Ecommerce
            'WooCommerce': {'category': 'Ecommerce', 'patterns': [r'woocommerce']},
            'Shopify': {'category': 'Ecommerce', 'patterns': [r'shopify']},
            'Magento': {'category': 'Ecommerce', 'patterns': [r'magento']},
            'PrestaShop': {'category': 'Ecommerce', 'patterns': [r'prestashop']},
            'OpenCart': {'category': 'Ecommerce', 'patterns': [r'opencart']},
            
            # Database
            'MySQL': {'category': 'Database', 'patterns': [r'mysql']},
            'PostgreSQL': {'category': 'Database', 'patterns': [r'postgresql']},
            'MongoDB': {'category': 'Database', 'patterns': [r'mongodb']},
            'Redis': {'category': 'Database', 'patterns': [r'redis']},
            
            # Analytics
            'Google Analytics': {
                'category': 'Analytics',
                'patterns': [r'google-analytics', r'ga\.js', r'gtag'],
                'scripts': [r'google-analytics', r'googletagmanager']
            },
            'Google Tag Manager': {
                'category': 'Analytics',
                'patterns': [r'googletagmanager', r'gtm\.js'],
                'scripts': [r'googletagmanager']
            },
            'Facebook Pixel': {
                'category': 'Analytics',
                'patterns': [r'facebook\.pixel', r'fbq\('],
                'scripts': [r'connect\.facebook\.net']
            },
            'Hotjar': {
                'category': 'Analytics',
                'patterns': [r'hotjar', r'static\.hotjar\.com'],
                'scripts': [r'hotjar']
            },
            'Matomo': {
                'category': 'Analytics',
                'patterns': [r'matomo', r'piwik'],
                'scripts': [r'matomo', r'piwik']
            },
            
            # CDN
            'Cloudflare': {'category': 'CDN', 'patterns': [r'cloudflare']},
            'Akamai': {'category': 'CDN', 'patterns': [r'akamai']},
            'Amazon CloudFront': {'category': 'CDN', 'patterns': [r'cloudfront']},
            'Fastly': {'category': 'CDN', 'patterns': [r'fastly']},
            'MaxCDN': {'category': 'CDN', 'patterns': [r'maxcdn']},
            
            # Fonts
            'Google Fonts': {
                'category': 'Fonts',
                'patterns': [r'fonts\.googleapis\.com', r'fonts\.gstatic\.com']
            },
            'Font Awesome': {
                'category': 'Fonts',
                'patterns': [r'fontawesome', r'kit\.fontawesome\.com']
            },
            
            # JavaScript Libraries
            'Bootstrap': {
                'category': 'UI Frameworks',
                'patterns': [r'bootstrap', r'bootstrap\.min\.css'],
                'scripts': [r'bootstrap']
            },
            'Tailwind CSS': {
                'category': 'UI Frameworks', 
                'patterns': [r'tailwind', r'tailwindcss']
            },
            'Foundation': {
                'category': 'UI Frameworks',
                'patterns': [r'foundation', r'foundation\.min\.css']
            },
            'Materialize': {
                'category': 'UI Frameworks',
                'patterns': [r'materialize', r'materialize\.min\.css']
            },
            
            # Cache
            'Varnish': {'category': 'Caching', 'patterns': [r'varnish']},
            'Redis': {'category': 'Caching', 'patterns': [r'redis']},
            'Memcached': {'category': 'Caching', 'patterns': [r'memcached']},
            
            # Security
            'reCAPTCHA': {
                'category': 'Security',
                'patterns': [r'recaptcha', r'google\.com/recaptcha'],
                'scripts': [r'recaptcha']
            },
            'hCaptcha': {
                'category': 'Security',
                'patterns': [r'hcaptcha', r'hcaptcha\.com'],
                'scripts': [r'hcaptcha']
            },
            
            # Payment
            'Stripe': {
                'category': 'Payment',
                'patterns': [r'stripe', r'stripe\.com'],
                'scripts': [r'stripe']
            },
            'PayPal': {
                'category': 'Payment',
                'patterns': [r'paypal', r'paypalobjects\.com'],
                'scripts': [r'paypal']
            },
        }
    
    def detect_from_headers(self, headers):
        """Detect technologies from HTTP headers"""
        detected = []
        
        for tech, info in self.tech_patterns.items():
            if 'headers' in info:
                for header_name, patterns in info['headers'].items():
                    if header_name in headers:
                        header_value = headers[header_name].lower()
                        for pattern in patterns:
                            if re.search(pattern, header_value, re.IGNORECASE):
                                detected.append(tech)
                                break
        
        return detected
    
    def detect_from_html(self, html):
        """Detect technologies from HTML content"""
        detected = []
        
        for tech, info in self.tech_patterns.items():
            if 'patterns' in info:
                for pattern in info['patterns']:
                    if re.search(pattern, html, re.IGNORECASE):
                        detected.append(tech)
                        break
            
            # Detect from script tags
            if 'scripts' in info:
                script_pattern = r'<script[^>]*src=["\']([^"\']*)["\'][^>]*>'
                scripts = re.findall(script_pattern, html, re.IGNORECASE)
                for script in scripts:
                    for pattern in info['scripts']:
                        if re.search(pattern, script, re.IGNORECASE):
                            detected.append(tech)
                            break
        
        return detected
    
    def detect_from_meta(self, html):
        """Detect technologies from meta tags"""
        detected = []
        
        for tech, info in self.tech_patterns.items():
            if 'meta' in info:
                for meta_name, patterns in info['meta'].items():
                    meta_pattern = f'<meta[^>]*name=["\']{meta_name}["\'][^>]*content=["\']([^"\']*)["\'][^>]*>'
                    meta_matches = re.findall(meta_pattern, html, re.IGNORECASE)
                    for meta_content in meta_matches:
                        for pattern in patterns:
                            if re.search(pattern, meta_content, re.IGNORECASE):
                                detected.append(tech)
                                break
        
        return detected
    
    def detect_from_cookies(self, cookies):
        """Detect technologies from cookies"""
        detected = []
        
        for tech, info in self.tech_patterns.items():
            if 'cookies' in info:
                for cookie_pattern in info['cookies']:
                    for cookie in cookies:
                        if re.search(cookie_pattern, cookie, re.IGNORECASE):
                            detected.append(tech)
                            break
        
        return detected
    
    def organize_technologies(self, detected_techs):
        """Organize technologies by category"""
        organized = {}
        
        for tech in set(detected_techs):
            if tech in self.tech_patterns:
                category = self.tech_patterns[tech]['category']
                if category not in organized:
                    organized[category] = []
                organized[category].append(tech)
        
        return organized
    
    def get_technology_icon(self, tech_name):
        """Get icons for technologies (similar to Wappalyzer)"""
        icons = {
            'WordPress': '🔧', 'Joomla': '🌐', 'Drupal': '💧', 'Magento': '🛒',
            'Shopify': '🛍️', 'React': '⚛️', 'Vue.js': '🟢', 'Angular': '🅰️',
            'jQuery': '⚡', 'PHP': '🐘', 'Python': '🐍', 'Node.js': '🟢',
            'Apache': '🔷', 'Nginx': '⚡', 'IIS': '🪟', 'Cloudflare': '🌩️',
            'Google Analytics': '📊', 'Google Tag Manager': '🏷️', 'Facebook Pixel': '📘',
            'MySQL': '🐬', 'PostgreSQL': '🐘', 'MongoDB': '🍃', 'Redis': '🔴',
            'Bootstrap': '🎨', 'Tailwind CSS': '💨', 'Google Fonts': '🔤',
            'Stripe': '💳', 'PayPal': '🔵', 'reCAPTCHA': '✅',
            'Linux': '🐧', 'Windows': '🪟', 'WooCommerce': '🛒'
        }
        return icons.get(tech_name, '🔍')
    
    def display_wappalyzer_style(self, organized_techs, response):
        """Display results in Wappalyzer-like style"""
        
        # Header with basic info
        console.print(Panel.fit(
            f"[bold cyan]🌐 Technology Stack Analysis[/bold cyan]\n"
            f"[white]URL:[/white] {response.url}\n"
            f"[white]Status:[/white] {response.status_code} • "
            f"[white]Size:[/white] {len(response.content):,} bytes • "
            f"[white]Time:[/white] {response.elapsed.total_seconds():.2f}s",
            style="blue"
        ))
        
        # Technology cards organized by category
        for category, techs in organized_techs.items():
            if techs:
                # Create technology cards for this category
                tech_cards = []
                for tech in sorted(techs):
                    icon = self.get_technology_icon(tech)
                    tech_cards.append(f"{icon} [bold white]{tech}[/bold white]")
                
                # Display category with technologies
                category_panel = Panel(
                    "\n".join([f"  • {card}" for card in tech_cards]),
                    title=f"[bold magenta]{category}[/bold magenta]",
                    border_style="cyan",
                    padding=(0, 2)
                )
                console.print(category_panel)
        
        # Summary
        total_techs = sum(len(techs) for techs in organized_techs.values())
        console.print(Panel.fit(
            f"[green]✅ Found {total_techs} technologies across {len(organized_techs)} categories[/green]",
            style="green"
        ))
    
    def display_compact_grid(self, organized_techs):
        """Display technologies in a compact grid like Wappalyzer"""
        
        # Create technology cards
        all_techs = []
        for category, techs in organized_techs.items():
            for tech in techs:
                icon = self.get_technology_icon(tech)
                all_techs.append(f"{icon} [bold white]{tech}[/bold white]")
        
        # Display in columns
        if all_techs:
            console.print(Panel(
                Columns(all_techs, column_first=True, expand=True),
                title="[bold blue]🛠️ Detected Technologies[/bold blue]",
                style="blue"
            ))
    
    def run_detection(self):
        """Main detection function"""
        target = self.options.get('TARGET')
        timeout = int(self.options.get('TIMEOUT', 10))
        
        console.print(Panel.fit(
            f"[bold cyan]🎯 Target:[/bold cyan] {target}\n"
            f"[bold green]⏱️ Timeout:[/bold green] {timeout}s",
            title="Wapplyzer-like Technology Detection",
            style="blue"
        ))
        
        console.print("[yellow]🔍 Scanning for technologies...[/yellow]")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("•"),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            ) as progress:
                
                task = progress.add_task("Analyzing technology stack...", total=100)
                
                # Fetch page
                progress.update(task, description="📡 Fetching target page...")
                response = self.session.get(target, timeout=timeout, allow_redirects=True)
                progress.update(task, advance=25)
                
                # Analyze headers
                progress.update(task, description="🔍 Analyzing HTTP headers...")
                header_techs = self.detect_from_headers(response.headers)
                progress.update(task, advance=20)
                
                # Analyze HTML content
                progress.update(task, description="📄 Scanning HTML content...")
                html_techs = self.detect_from_html(response.text)
                progress.update(task, advance=25)
                
                # Analyze meta tags
                progress.update(task, description="🏷️ Checking meta tags...")
                meta_techs = self.detect_from_meta(response.text)
                progress.update(task, advance=15)
                
                # Analyze cookies
                progress.update(task, description="🍪 Inspecting cookies...")
                cookie_techs = self.detect_from_cookies(response.cookies)
                progress.update(task, advance=15)
                
                # Combine all detections
                all_techs = header_techs + html_techs + meta_techs + cookie_techs
                organized_techs = self.organize_technologies(all_techs)
                
                progress.update(task, advance=100)
            
            console.print(f"\n[green]✅ Technology detection completed![/green]")
            
            # Display results
            self.display_wappalyzer_style(organized_techs, response)
            
            # Also show compact grid view
            console.print("\n")
            self.display_compact_grid(organized_techs)
            
        except Exception as e:
            console.print(f"[red]❌ Error during detection: {e}[/red]")
    
    def generate_tech_report(self, organized_techs):
        """Generate a detailed technology report"""
        report = []
        report.append("## Technology Stack Report")
        report.append("")
        
        for category, techs in organized_techs.items():
            report.append(f"### {category}")
            for tech in sorted(techs):
                report.append(f"- {self.get_technology_icon(tech)} {tech}")
            report.append("")
        
        return "\n".join(report)

def run(session, options):
    """Main function called by framework"""
    detector = WapplyzerDetector(options)
    detector.run_detection()

# Example usage
if __name__ == "__main__":
    test_options = {
        "TARGET": "https://wordpress.org",
        "TIMEOUT": "10",
        "DETECT_ANALYTICS": "true",
        "DETECT_CDN": "true"
    }
    detector = WapplyzerDetector(test_options)
    detector.run_detection()
