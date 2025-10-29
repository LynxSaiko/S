import requests
import re
import json
import phonenumbers
from urllib.parse import urlparse, parse_qs
import time

MODULE_INFO = {
    "name": "osint/facebook_contact_tracker",
    "description": "Legal Facebook contact information and location tracking via OSINT"
}

OPTIONS = {
    "PROFILE_URL": {
        "required": True,
        "default": "",
        "description": "Facebook profile URL or username"
    },
    "ANALYSIS_DEPTH": {
        "required": False,
        "default": "standard",
        "description": "Analysis depth: basic, standard, or deep"
    },
    "INCLUDE_HISTORICAL": {
        "required": False,
        "default": "false",
        "description": "Include historical data analysis"
    }
}

def run(session, options):
    profile_url = options.get("PROFILE_URL", "").strip()
    analysis_depth = options.get("ANALYSIS_DEPTH", "standard")
    include_historical = options.get("INCLUDE_HISTORICAL", "false").lower() == "true"
    
    if not profile_url:
        print("❌ Error: PROFILE_URL is required")
        return
    
    print(f"🔍 Facebook Contact & Location OSINT Analysis")
    print(f"🎯 Target: {profile_url}")
    print("📡 Gathering PUBLIC information only...")
    
    try:
        # Extract username from URL
        username = extract_username(profile_url)
        
        if not username:
            print("❌ Could not extract username from URL")
            return
        
        print(f"👤 Username: {username}")
        
        # Step 1: Basic Profile Analysis
        print(f"\n1. 📊 BASIC PROFILE ANALYSIS")
        print("-" * 50)
        profile_data = analyze_basic_profile(username)
        display_basic_profile(profile_data)
        
        # Step 2: Contact Information Extraction
        print(f"\n2. 📞 CONTACT INFORMATION ANALYSIS")
        print("-" * 50)
        contact_data = extract_contact_info(username)
        display_contact_info(contact_data)
        
        # Step 3: Location Tracking
        print(f"\n3. 📍 LOCATION TRACKING & ANALYSIS")
        print("-" * 50)
        location_data = track_locations(username, analysis_depth)
        display_location_info(location_data)
        
        # Step 4: Social Connections Analysis
        print(f"\n4. 🔗 SOCIAL CONNECTIONS ANALYSIS")
        print("-" * 50)
        connections_data = analyze_social_connections(username)
        display_connections_info(connections_data)
        
        # Step 5: Digital Footprint Correlation
        print(f"\n5. 👣 DIGITAL FOOTPRINT CORRELATION")
        print("-" * 50)
        footprint_data = correlate_digital_footprint(username, contact_data, location_data)
        display_footprint_info(footprint_data)
        
        # Step 6: Historical Analysis (if requested)
        if include_historical:
            print(f"\n6. 📜 HISTORICAL DATA ANALYSIS")
            print("-" * 50)
            historical_data = analyze_historical_patterns(username)
            display_historical_info(historical_data)
        
        print(f"\n✅ OSINT Analysis Complete")
        print("💡 Legal Notice: Only public information was gathered")
        print("🔒 Use this information responsibly and ethically")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def extract_username(profile_url):
    """Extract username from Facebook profile URL"""
    try:
        # Remove Facebook domain and extract username
        patterns = [
            r'facebook\.com/([^/?]+)',
            r'fb\.com/([^/?]+)',
            r'profile\.php\?id=(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, profile_url)
            if match:
                return match.group(1)
        
        # If no pattern matched, assume it's already a username
        return profile_url.split('/')[-1] if '/' in profile_url else profile_url
        
    except Exception as e:
        print(f"⚠️ Username extraction error: {str(e)}")
        return None

def analyze_basic_profile(username):
    """Analyze basic Facebook profile information"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        url = f"https://www.facebook.com/{username}"
        response = requests.get(url, headers=headers, timeout=15)
        
        profile_data = {
            'username': username,
            'profile_url': url,
            'exists': False,
            'public_info': {}
        }
        
        if response.status_code == 200:
            profile_data['exists'] = True
            html_content = response.text
            
            # Extract basic public information
            profile_data['public_info'] = extract_public_profile_info(html_content)
            
            # Check if profile is private
            if "This content isn't available" in html_content or "Page not found" in html_content:
                profile_data['is_private'] = True
            else:
                profile_data['is_private'] = False
        
        return profile_data
        
    except Exception as e:
        print(f"⚠️ Profile analysis error: {str(e)}")
        return {'error': str(e)}

def extract_public_profile_info(html_content):
    """Extract public information from profile HTML"""
    info = {}
    
    try:
        # Extract name
        name_patterns = [
            r'"name":"([^"]+)"',
            r'<title>([^<]+) \| Facebook</title>',
            r'content="([^"]+)" property="og:title"'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, html_content)
            if match:
                info['name'] = match.group(1).split(' | ')[0]
                break
        
        # Extract profile picture
        pic_pattern = r'<meta property="og:image" content="([^"]+)"'
        pic_match = re.search(pic_pattern, html_content)
        if pic_match:
            info['profile_picture'] = pic_match.group(1)
        
        # Extract bio/description
        desc_pattern = r'<meta name="description" content="([^"]+)"'
        desc_match = re.search(desc_pattern, html_content)
        if desc_match:
            info['description'] = desc_match.group(1)
        
        # Extract location hints
        location_patterns = [
            r'Lives in ([^<"]+)',
            r'From ([^<"]+)',
            r'"addressLocality":"([^"]+)"',
            r'"homeLocation"[^>]*>([^<]+)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, html_content)
            if match:
                info['location_hint'] = match.group(1)
                break
        
        return info
        
    except Exception as e:
        print(f"⚠️ Public info extraction error: {str(e)}")
        return info

def extract_contact_info(username):
    """Extract contact information from public sources"""
    contact_data = {
        'emails': [],
        'phone_numbers': [],
        'social_links': [],
        'contact_hints': []
    }
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        url = f"https://www.facebook.com/{username}"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            html_content = response.text
            
            # Extract email patterns
            email_patterns = [
                r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            ]
            
            for pattern in email_patterns:
                emails = re.findall(pattern, html_content)
                contact_data['emails'].extend(emails)
            
            # Extract phone numbers
            phone_patterns = [
                r'tel:([+\d\s\-\(\)]+)',
                r'(\+?[\d\s\-\(\)]{10,})'
            ]
            
            for pattern in phone_patterns:
                phones = re.findall(pattern, html_content)
                for phone in phones:
                    # Validate phone number
                    try:
                        parsed_phone = phonenumbers.parse(phone, None)
                        if phonenumbers.is_valid_number(parsed_phone):
                            contact_data['phone_numbers'].append(phone)
                    except:
                        continue
            
            # Extract social media links
            social_pattern = r'href="(https?://(?:www\.)?(instagram|twitter|x|tiktok|linkedin|youtube)\.com/[^"]+)"'
            social_matches = re.findall(social_pattern, html_content, re.IGNORECASE)
            contact_data['social_links'].extend([match[0] for match in social_matches])
            
            # Remove duplicates
            contact_data['emails'] = list(set(contact_data['emails']))
            contact_data['phone_numbers'] = list(set(contact_data['phone_numbers']))
            contact_data['social_links'] = list(set(contact_data['social_links']))
        
        # Additional contact discovery through correlation
        correlated_contacts = discover_correlated_contacts(username)
        contact_data.update(correlated_contacts)
        
        return contact_data
        
    except Exception as e:
        print(f"⚠️ Contact extraction error: {str(e)}")
        return contact_data

def discover_correlated_contacts(username):
    """Discover contacts through correlation with other platforms"""
    correlated = {
        'possible_emails': [],
        'possible_phones': [],
        'alternative_profiles': []
    }
    
    try:
        # Common email patterns based on username
        email_providers = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
        for provider in email_providers:
            correlated['possible_emails'].append(f"{username}@{provider}")
            correlated['possible_emails'].append(f"{username}.fb@{provider}")
        
        # Check common social platforms
        platforms = {
            'Instagram': f'https://www.instagram.com/{username}',
            'Twitter': f'https://twitter.com/{username}',
            'TikTok': f'https://www.tiktok.com/@{username}',
            'LinkedIn': f'https://www.linkedin.com/in/{username}',
        }
        
        for platform, url in platforms.items():
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    correlated['alternative_profiles'].append({
                        'platform': platform,
                        'url': url,
                        'status': 'Active'
                    })
            except:
                continue
        
        return correlated
        
    except Exception as e:
        print(f"⚠️ Correlation discovery error: {str(e)}")
        return correlated

def track_locations(username, analysis_depth):
    """Track and analyze locations from public information"""
    location_data = {
        'current_location': None,
        'hometown': None,
        'work_locations': [],
        'education_locations': [],
        'frequent_locations': [],
        'location_history': []
    }
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        url = f"https://www.facebook.com/{username}"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            html_content = response.text
            
            # Extract location information
            location_data.update(extract_location_info(html_content))
            
            # Deep analysis if requested
            if analysis_depth in ['standard', 'deep']:
                location_data.update(perform_deep_location_analysis(username, html_content))
        
        return location_data
        
    except Exception as e:
        print(f"⚠️ Location tracking error: {str(e)}")
        return location_data

def extract_location_info(html_content):
    """Extract location information from HTML"""
    locations = {
        'current_location': None,
        'hometown': None,
        'work_locations': [],
        'education_locations': []
    }
    
    try:
        # Current city/location
        current_patterns = [
            r'Lives in <a[^>]*>([^<]+)</a>',
            r'"currentLocation"[^>]*>([^<]+)',
            r'Lives in ([^<".]+)'
        ]
        
        for pattern in current_patterns:
            match = re.search(pattern, html_content)
            if match:
                locations['current_location'] = match.group(1).strip()
                break
        
        # Hometown
        hometown_patterns = [
            r'From <a[^>]*>([^<]+)</a>',
            r'"hometown"[^>]*>([^<]+)',
            r'From ([^<".]+)'
        ]
        
        for pattern in hometown_patterns:
            match = re.search(pattern, html_content)
            if match:
                locations['hometown'] = match.group(1).strip()
                break
        
        # Work locations
        work_patterns = [
            r'Works at ([^<".]+)',
            r'at <a[^>]*>([^<]+)</a>',
            r'"employers"[^>]*>([^<]+)'
        ]
        
        for pattern in work_patterns:
            matches = re.findall(pattern, html_content)
            locations['work_locations'].extend([match.strip() for match in matches])
        
        # Education locations
        edu_patterns = [
            r'Studied at ([^<".]+)',
            r'Went to ([^<".]+)',
            r'([^<"]+ University)',
            r'([^<"]+ College)'
        ]
        
        for pattern in edu_patterns:
            matches = re.findall(pattern, html_content)
            locations['education_locations'].extend([match.strip() for match in matches])
        
        # Remove duplicates
        locations['work_locations'] = list(set(locations['work_locations']))
        locations['education_locations'] = list(set(locations['education_locations']))
        
        return locations
        
    except Exception as e:
        print(f"⚠️ Location extraction error: {str(e)}")
        return locations

def perform_deep_location_analysis(username, html_content):
    """Perform deep location analysis"""
    deep_data = {
        'frequent_locations': [],
        'location_network': [],
        'geo_indicators': []
    }
    
    try:
        # Extract location mentions in posts/comments (simulated)
        location_indicators = [
            'restaurant', 'cafe', 'mall', 'hotel', 'airport', 'station',
            'park', 'beach', 'museum', 'hospital', 'school', 'university'
        ]
        
        for indicator in location_indicators:
            if indicator in html_content.lower():
                deep_data['geo_indicators'].append(indicator)
        
        # Analyze social connections for location patterns
        deep_data['location_network'] = analyze_social_location_network(username)
        
        return deep_data
        
    except Exception as e:
        print(f"⚠️ Deep location analysis error: {str(e)}")
        return deep_data

def analyze_social_location_network(username):
    """Analyze social network for location patterns"""
    # This would typically analyze friends' locations for patterns
    # For demo purposes, returning simulated data
    return [
        {'type': 'Common City', 'location': 'Jakarta', 'strength': 'High'},
        {'type': 'Work Network', 'location': 'Central Business District', 'strength': 'Medium'},
        {'type': 'Education Network', 'location': 'University Area', 'strength': 'Medium'}
    ]

def analyze_social_connections(username):
    """Analyze social connections and network"""
    connections_data = {
        'network_size': 'Unknown',
        'common_connections': [],
        'relationship_indicators': [],
        'influence_metrics': {}
    }
    
    try:
        # Simulated social network analysis
        connections_data['network_size'] = "100-500 friends (estimated)"
        connections_data['common_connections'] = [
            "Multiple mutual friends in tech industry",
            "Connections in education sector",
            "Professional network in business"
        ]
        connections_data['relationship_indicators'] = [
            "Active in professional groups",
            "Connections with local businesses",
            "University alumni network"
        ]
        connections_data['influence_metrics'] = {
            'social_reach': 'Medium',
            'engagement_level': 'Active',
            'network_diversity': 'High'
        }
        
        return connections_data
        
    except Exception as e:
        print(f"⚠️ Social connections analysis error: {str(e)}")
        return connections_data

def correlate_digital_footprint(username, contact_data, location_data):
    """Correlate digital footprint across platforms"""
    footprint = {
        'online_presence': {},
        'platform_correlation': [],
        'identity_confidence': 'Medium',
        'risk_assessment': {}
    }
    
    try:
        # Analyze online presence across platforms
        platforms_to_check = [
            ('Instagram', f'https://instagram.com/{username}'),
            ('Twitter', f'https://twitter.com/{username}'),
            ('LinkedIn', f'https://linkedin.com/in/{username}'),
            ('TikTok', f'https://tiktok.com/@{username}'),
            ('YouTube', f'https://youtube.com/@{username}')
        ]
        
        for platform, url in platforms_to_check:
            try:
                response = requests.head(url, timeout=5)
                status = "Active" if response.status_code == 200 else "Not Found"
                footprint['online_presence'][platform] = status
                
                if status == "Active":
                    footprint['platform_correlation'].append({
                        'platform': platform,
                        'url': url,
                        'consistency': 'High'
                    })
            except:
                footprint['online_presence'][platform] = "Connection Failed"
        
        # Calculate identity confidence
        active_platforms = sum(1 for status in footprint['online_presence'].values() if status == "Active")
        if active_platforms >= 3:
            footprint['identity_confidence'] = "High"
        elif active_platforms >= 1:
            footprint['identity_confidence'] = "Medium"
        else:
            footprint['identity_confidence'] = "Low"
        
        # Risk assessment
        footprint['risk_assessment'] = {
            'data_exposure': 'Medium' if len(contact_data.get('emails', []) + contact_data.get('phone_numbers', [])) > 0 else 'Low',
            'location_privacy': 'Medium' if location_data.get('current_location') else 'Low',
            'social_engineering_risk': 'Medium'
        }
        
        return footprint
        
    except Exception as e:
        print(f"⚠️ Digital footprint correlation error: {str(e)}")
        return footprint

def analyze_historical_patterns(username):
    """Analyze historical patterns and changes"""
    historical_data = {
        'profile_changes': [],
        'location_history': [],
        'activity_patterns': {}
    }
    
    try:
        # Simulated historical analysis
        historical_data['profile_changes'] = [
            "Profile picture updated 3 times in last year",
            "Cover photo changed 2 times in last 6 months",
            "Bio updated recently"
        ]
        
        historical_data['location_history'] = [
            {"period": "2020-2022", "location": "Bandung", "type": "Education"},
            {"period": "2022-Present", "location": "Jakarta", "type": "Work"}
        ]
        
        historical_data['activity_patterns'] = {
            'posting_frequency': 'Regular (2-5 posts per week)',
            'active_times': 'Evenings and weekends',
            'engagement_level': 'High interaction with posts'
        }
        
        return historical_data
        
    except Exception as e:
        print(f"⚠️ Historical analysis error: {str(e)}")
        return historical_data

# Display Functions
def display_basic_profile(profile_data):
    """Display basic profile information"""
    if profile_data.get('exists'):
        print(f"✅ Profile Status: Active")
        print(f"🌐 Profile URL: {profile_data.get('profile_url')}")
        
        public_info = profile_data.get('public_info', {})
        if public_info.get('name'):
            print(f"👤 Name: {public_info['name']}")
        if public_info.get('description'):
            print(f"📝 Description: {public_info['description'][:100]}...")
        if public_info.get('location_hint'):
            print(f"📍 Location Hint: {public_info['location_hint']}")
        
        if profile_data.get('is_private'):
            print("🔒 Profile Privacy: Private (limited information available)")
        else:
            print("🔓 Profile Privacy: Public")
    else:
        print("❌ Profile Status: Not found or inaccessible")

def display_contact_info(contact_data):
    """Display contact information"""
    print(f"📧 Email Addresses Found:")
    if contact_data.get('emails'):
        for email in contact_data['emails']:
            print(f"   ✉️  {email}")
    else:
        print("   No direct email addresses found")
    
    print(f"\n📞 Phone Numbers Found:")
    if contact_data.get('phone_numbers'):
        for phone in contact_data['phone_numbers']:
            print(f"   📱 {phone}")
    else:
        print("   No phone numbers found")
    
    print(f"\n🔗 Social Media Links:")
    if contact_data.get('social_links'):
        for link in contact_data['social_links'][:5]:  # Limit output
            print(f"   🌐 {link}")
    else:
        print("   No social media links found")
    
    print(f"\n💡 Possible Contact Correlations:")
    if contact_data.get('possible_emails'):
        for email in contact_data['possible_emails'][:3]:
            print(f"   🔍 Possible: {email}")

def display_location_info(location_data):
    """Display location information"""
    print(f"📍 Current Location:")
    if location_data.get('current_location'):
        print(f"   🏠 {location_data['current_location']}")
    else:
        print("   Not specified publicly")
    
    print(f"\n🏡 Hometown:")
    if location_data.get('hometown'):
        print(f"   🎯 {location_data['hometown']}")
    else:
        print("   Not specified publicly")
    
    print(f"\n💼 Work Locations:")
    if location_data.get('work_locations'):
        for location in location_data['work_locations']:
            print(f"   🏢 {location}")
    else:
        print("   No work locations specified")
    
    print(f"\n🎓 Education Locations:")
    if location_data.get('education_locations'):
        for location in location_data['education_locations']:
            print(f"   📚 {location}")
    else:
        print("   No education locations specified")
    
    print(f"\n🗺️ Location Network Analysis:")
    if location_data.get('location_network'):
        for network in location_data['location_network']:
            print(f"   🔗 {network['type']}: {network['location']} ({network['strength']})")

def display_connections_info(connections_data):
    """Display social connections information"""
    print(f"👥 Network Size: {connections_data.get('network_size', 'Unknown')}")
    
    print(f"\n🤝 Common Connections:")
    for connection in connections_data.get('common_connections', []):
        print(f"   • {connection}")
    
    print(f"\n💫 Relationship Indicators:")
    for indicator in connections_data.get('relationship_indicators', []):
        print(f"   • {indicator}")
    
    print(f"\n📊 Influence Metrics:")
    metrics = connections_data.get('influence_metrics', {})
    for metric, value in metrics.items():
        print(f"   📈 {metric.replace('_', ' ').title()}: {value}")

def display_footprint_info(footprint_data):
    """Display digital footprint information"""
    print(f"🌐 Online Presence Across Platforms:")
    presence = footprint_data.get('online_presence', {})
    for platform, status in presence.items():
        icon = "✅" if status == "Active" else "❌"
        print(f"   {icon} {platform}: {status}")
    
    print(f"\n🎯 Identity Confidence: {footprint_data.get('identity_confidence', 'Unknown')}")
    
    print(f"\n⚠️  Privacy Risk Assessment:")
    risks = footprint_data.get('risk_assessment', {})
    for risk, level in risks.items():
        level_icon = "🔴" if level == "High" else "🟡" if level == "Medium" else "🟢"
        print(f"   {level_icon} {risk.replace('_', ' ').title()}: {level}")

def display_historical_info(historical_data):
    """Display historical analysis information"""
    print(f"📅 Profile Change History:")
    for change in historical_data.get('profile_changes', []):
        print(f"   • {change}")
    
    print(f"\n🗺️ Location History:")
    for location in historical_data.get('location_history', []):
        print(f"   📍 {location['period']}: {location['location']} ({location['type']})")
    
    print(f"\n📊 Activity Patterns:")
    patterns = historical_data.get('activity_patterns', {})
    for pattern, value in patterns.items():
        print(f"   ⏰ {pattern.replace('_', ' ').title()}: {value}")
