import requests
import re
import json
import time
from datetime import datetime

MODULE_INFO = {
    "name": "osint/tiktok_live_fixed",
    "description": "Fixed TikTok live analysis with multiple detection methods"
}

OPTIONS = {
    "USERNAME": {
        "required": True,
        "default": "",
        "description": "TikTok username without @"
    },
    "DEEP_SCAN": {
        "required": False,
        "default": "true",
        "description": "Use multiple methods for live detection"
    }
}

def run(session, options):
    username = options.get("USERNAME", "").strip().lower()
    deep_scan = options.get("DEEP_SCAN", "true").lower() == "true"
    
    if not username:
        print("❌ Error: USERNAME is required")
        return
    
    print(f"🔍 Analyzing @{username} for live streams...")
    print("🔄 Using enhanced detection methods...")
    
    try:
        # Method 1: HTML Parsing (Primary)
        print("\n1. 📄 HTML Page Analysis")
        html_data = analyze_via_html(username)
        
        if not html_data:
            print("❌ Failed to fetch user data")
            return
            
        display_user_info(html_data)
        
        # Method 2: Live Status Check
        print("\n2. 🔴 Live Stream Detection")
        live_data = check_live_status_enhanced(username, deep_scan)
        
        if live_data and live_data.get('is_live'):
            display_live_info(live_data, username)
            calculate_earnings(live_data)
        else:
            print("📴 User is not currently live streaming")
            
            # Check live capability
            if html_data.get('can_go_live'):
                print("✅ User has live streaming capability")
            
            # Show estimated potential
            show_live_potential(html_data)
        
        # Method 3: Gift & Earnings Analysis
        print("\n3. 💰 Earnings Potential Analysis")
        analyze_earnings_potential(html_data)
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def analyze_via_html(username):
    """Analyze user data via HTML parsing"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        
        url = f"https://www.tiktok.com/@{username}"
        print(f"   🌐 Fetching: {url}")
        
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   📄 Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ HTTP Error: {response.status_code}")
            return None
        
        return parse_html_content(response.text, username)
        
    except Exception as e:
        print(f"   ❌ HTML analysis error: {str(e)}")
        return None

def parse_html_content(html_content, username):
    """Parse HTML content for user data"""
    user_data = {
        'username': username,
        'exists': True,
        'can_go_live': False,
        'is_live': False
    }
    
    # Check if user exists
    if "Page not found" in html_content or "This page is not available" in html_content:
        user_data['exists'] = False
        return user_data
    
    # Extract from SIGI_STATE
    sigi_data = extract_sigi_data(html_content)
    if sigi_data:
        user_data.update(sigi_data)
    
    # Extract from meta tags and other patterns
    user_data.update(extract_basic_info(html_content))
    
    # Check live indicators
    user_data.update(check_live_indicators(html_content))
    
    return user_data

def extract_sigi_data(html_content):
    """Extract data from SIGI_STATE"""
    data = {}
    
    try:
        sigi_pattern = r'<script id="SIGI_STATE" type="application/json">(.*?)</script>'
        match = re.search(sigi_pattern, html_content, re.DOTALL)
        
        if match:
            sigi_json = json.loads(match.group(1))
            
            # Extract user data
            if 'UserModule' in sigi_json and 'users' in sigi_json['UserModule']:
                users = sigi_json['UserModule']['users']
                for user_key, user_info in users.items():
                    data.update({
                        'nickname': user_info.get('nickname'),
                        'signature': user_info.get('signature', ''),
                        'verified': user_info.get('verified', False),
                        'private': user_info.get('privateAccount', False),
                        'followers': user_info.get('followerCount', 0),
                        'following': user_info.get('followingCount', 0),
                        'hearts': user_info.get('heartCount', 0),
                        'videos': user_info.get('videoCount', 0),
                        'userId': user_info.get('id'),
                        'secUid': user_info.get('secUid'),
                    })
                    break
            
            # Check live status
            if 'LiveRoom' in sigi_json:
                live_data = sigi_json['LiveRoom']
                data['is_live'] = check_live_in_sigi(live_data)
                
        return data
        
    except Exception as e:
        print(f"   ⚠️ SIGI extraction error: {str(e)}")
        return data

def check_live_in_sigi(live_data):
    """Check live status in SIGI data"""
    try:
        # Multiple ways live status can be indicated
        if 'liveRoomUser' in live_data:
            user_status = live_data['liveRoomUser'].get('status', 0)
            return user_status == 2  # 2 means live
        
        if 'liveRoom' in live_data:
            room_status = live_data['liveRoom'].get('status', 0)
            return room_status == 2
            
        return False
        
    except:
        return False

def extract_basic_info(html_content):
    """Extract basic info from HTML"""
    data = {}
    
    try:
        # Extract from meta description
        desc_pattern = r'<meta property="og:description" content="([^"]*)"'
        desc_match = re.search(desc_pattern, html_content)
        if desc_match:
            data['meta_description'] = desc_match.group(1)
        
        # Extract follower count from various patterns
        follower_patterns = [
            r'"followerCount":"(\d+)"',
            r'followers["\']?\s*:\s*["\']?(\d+)',
            r'(\d+[\d,]*)\s*Followers',
        ]
        
        for pattern in follower_patterns:
            match = re.search(pattern, html_content)
            if match:
                try:
                    followers = int(match.group(1).replace(',', ''))
                    if followers > data.get('followers', 0):
                        data['followers'] = followers
                except:
                    continue
        
        return data
        
    except Exception as e:
        print(f"   ⚠️ Basic info extraction error: {str(e)}")
        return data

def check_live_indicators(html_content):
    """Check for live streaming indicators"""
    data = {'can_go_live': False, 'is_live': False}
    
    # Check for live stream indicators
    live_indicators = [
        'isLive',
        'is_live',
        'liveStream',
        'live-room',
        '🔴 LIVE',
        'isActive:true',
    ]
    
    for indicator in live_indicators:
        if indicator in html_content:
            data['is_live'] = True
            break
    
    # Check for live capability
    capability_indicators = [
        'liveCommerce',
        'liveEcommerce',
        'liveness',
        'can_go_live',
    ]
    
    for indicator in capability_indicators:
        if indicator in html_content:
            data['can_go_live'] = True
            break
    
    return data

def check_live_status_enhanced(username, deep_scan=False):
    """Enhanced live status checking with multiple methods"""
    live_data = {'is_live': False}
    
    print("   🔄 Checking live status...")
    
    # Method 1: Webcast API (simplified)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Origin': 'https://www.tiktok.com',
            'Referer': 'https://www.tiktok.com/',
        }
        
        # Try different API endpoints
        endpoints = [
            f"https://www.tiktok.com/api/live/detail/?aid=1988&roomId={username}",
            f"https://webcast.tiktok.com/webcast/room/enter/?webcast_sdk_version=1.3.0&aid=1988&room_id={username}",
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, headers=headers, timeout=10)
                if response.status_code == 200:
                    # Try to parse as JSON
                    try:
                        data = response.json()
                        if data.get('data'):
                            live_data.update(parse_live_response(data))
                            if live_data['is_live']:
                                print("   ✅ Live status: ACTIVE (API)")
                                return live_data
                    except:
                        # If not JSON, check for live indicators in text
                        if 'live' in response.text.lower():
                            live_data['is_live'] = True
                            live_data['source'] = 'text_analysis'
                            print("   ✅ Live status: ACTIVE (Text Analysis)")
                            return live_data
            except:
                continue
                
    except Exception as e:
        print(f"   ⚠️ API check error: {str(e)}")
    
    # Method 2: Deep scan with additional endpoints
    if deep_scan:
        deep_result = deep_live_scan(username)
        if deep_result:
            return deep_result
    
    print("   ❌ Live status: INACTIVE")
    return live_data

def parse_live_response(api_data):
    """Parse live API response"""
    data = {'is_live': False}
    
    try:
        # Different response structures
        if 'data' in api_data:
            room_data = api_data['data']
            
            # Check various live indicators
            if isinstance(room_data, dict):
                if room_data.get('status') == 2:
                    data['is_live'] = True
                if room_data.get('user_count', 0) > 0:
                    data['is_live'] = True
                    data['viewer_count'] = room_data.get('user_count')
                if room_data.get('title'):
                    data['title'] = room_data.get('title')
                    data['is_live'] = True
                    
        return data
        
    except:
        return data

def deep_live_scan(username):
    """Deep scan for live status using additional methods"""
    print("   🔍 Performing deep scan...")
    
    try:
        # Check via mobile user-agent
        mobile_headers = {
            'User-Agent': 'TikTok 26.2.0 rv:262018 (iPhone; iOS 14.4.2; en_US) Cronet',
            'Accept': 'application/json',
        }
        
        mobile_url = f"https://api16-normal-c-useast1a.tiktokv.com/tiktok/user/detail/?unique_id={username}"
        response = requests.get(mobile_url, headers=mobile_headers, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('user_info', {}).get('live_status') == 1:
                    return {
                        'is_live': True,
                        'source': 'mobile_api',
                        'viewer_count': data.get('user_info', {}).get('live_room_viewer_count', 0)
                    }
            except:
                pass
                
    except Exception as e:
        print(f"   ⚠️ Deep scan error: {str(e)}")
    
    return None

def display_user_info(user_data):
    """Display user information"""
    print(f"\n{'='*60}")
    print("👤 TIKTOK USER INFORMATION")
    print(f"{'='*60}")
    
    print(f"📛 Username: @{user_data.get('username', 'N/A')}")
    
    if user_data.get('nickname'):
        print(f"👤 Display Name: {user_data.get('nickname')}")
    
    if user_data.get('signature'):
        print(f"📝 Bio: {user_data.get('signature')}")
    
    if user_data.get('followers', 0) > 0:
        print(f"👥 Followers: {user_data.get('followers', 0):,}")
        print(f"🤝 Following: {user_data.get('following', 0):,}")
        print(f"❤️  Total Likes: {user_data.get('hearts', 0):,}")
        print(f"🎬 Videos: {user_data.get('videos', 0):,}")
    
    print(f"🔒 Private: {'Yes' if user_data.get('private') else 'No'}")
    print(f"✅ Verified: {'Yes' if user_data.get('verified') else 'No'}")
    print(f"🔴 Live Capable: {'Yes' if user_data.get('can_go_live') else 'No'}")
    print(f"🎥 Currently Live: {'Yes' if user_data.get('is_live') else 'No'}")

def display_live_info(live_data, username):
    """Display live stream information"""
    print(f"\n🎉 LIVE STREAM DETECTED!")
    print(f"🔴 @{username} is LIVE NOW")
    print("-" * 40)
    
    if live_data.get('title'):
        print(f"📺 Title: {live_data.get('title')}")
    
    if live_data.get('viewer_count', 0) > 0:
        print(f"👥 Current Viewers: {live_data.get('viewer_count', 0):,}")
    
    print(f"🕒 Live since: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📡 Source: {live_data.get('source', 'Unknown')}")

def calculate_earnings(live_data):
    """Calculate potential earnings from live stream"""
    print(f"\n💰 POTENTIAL EARNINGS ESTIMATION")
    print("-" * 40)
    
    viewer_count = live_data.get('viewer_count', 100)  # Default to 100 if unknown
    
    # Earnings estimation based on viewer count
    base_diamonds = viewer_count * 0.5  # Conservative estimate
    high_diamonds = viewer_count * 2.0   # High engagement estimate
    
    # Convert to USD
    base_usd = base_diamonds * 0.005
    high_usd = high_diamonds * 0.005
    
    print(f"👥 Based on {viewer_count:,} viewers:")
    print(f"💎 Estimated Diamonds: {base_diamonds:,.0f} - {high_diamonds:,.0f}")
    print(f"💵 Estimated USD: ${base_usd:,.2f} - ${high_usd:,.2f}")
    print(f"🇮🇩 Estimated IDR: Rp {base_usd * 15500:,.0f} - Rp {high_usd * 15500:,.0f}")
    
    # Show gift equivalents
    print(f"\n🎁 POPULAR GIFT EQUIVALENTS:")
    gifts = [
        ('Rose', 1),
        ('TikTok', 5),
        ('Crown', 50),
        ('Lion', 300),
        ('Universe', 1000),
    ]
    
    for gift_name, gift_cost in gifts:
        min_count = int(base_diamonds / gift_cost)
        max_count = int(high_diamonds / gift_cost)
        if max_count > 0:
            print(f"   {gift_name}: {min_count}-{max_count} gifts")

def show_live_potential(user_data):
    """Show live streaming potential"""
    print(f"\n📈 LIVE STREAMING POTENTIAL")
    print("-" * 40)
    
    followers = user_data.get('followers', 0)
    
    if followers == 0:
        print("ℹ️  Follower data not available")
        return
    
    # Estimate potential viewers based on followers
    avg_viewer_rate = 0.02  # 2% of followers typically watch live
    potential_viewers = int(followers * avg_viewer_rate)
    
    # Estimate potential earnings
    potential_diamonds = potential_viewers * 1.0  # 1 diamond per viewer avg
    potential_usd = potential_diamonds * 0.005
    
    print(f"📊 Based on {followers:,} followers:")
    print(f"👥 Potential Viewers: {potential_viewers:,} (2% of followers)")
    print(f"💎 Potential Diamonds: {potential_diamonds:,.0f} per stream")
    print(f"💵 Potential Earnings: ${potential_usd:,.2f} USD per stream")
    print(f"🇮🇩 Potential Earnings: Rp {potential_usd * 15500:,.0f} IDR per stream")
    
    # Weekly potential
    weekly_usd = potential_usd * 3  # Assuming 3 streams per week
    print(f"\n📅 Weekly Potential (3 streams): ${weekly_usd:,.2f} USD")

def analyze_earnings_potential(user_data):
    """Analyze overall earnings potential"""
    print(f"\n💎 DIAMOND & EARNINGS BREAKDOWN")
    print("-" * 40)
    
    followers = user_data.get('followers', 0)
    
    if followers == 0:
        print("ℹ️  Cannot calculate without follower data")
        return
    
    # Engagement rates for different creator levels
    engagement_tiers = [
        ('Micro Creator', 1000, 5000, 0.01, 0.03),
        ('Growing Creator', 5000, 50000, 0.02, 0.05),
        ('Popular Creator', 50000, 500000, 0.03, 0.08),
        ('Top Creator', 500000, 5000000, 0.05, 0.15),
        ('Superstar', 5000000, 100000000, 0.08, 0.25),
    ]
    
    # Find appropriate tier
    tier_name = "Unknown"
    min_diamonds = 0
    max_diamonds = 0
    
    for tier, min_follow, max_follow, min_rate, max_rate in engagement_tiers:
        if min_follow <= followers < max_follow:
            tier_name = tier
            min_diamonds = followers * min_rate
            max_diamonds = followers * max_rate
            break
    
    min_usd = min_diamonds * 0.005
    max_usd = max_diamonds * 0.005
    
    print(f"🏆 Creator Tier: {tier_name}")
    print(f"📊 Estimated Monthly Diamonds: {min_diamonds:,.0f} - {max_diamonds:,.0f}")
    print(f"💵 Estimated Monthly USD: ${min_usd:,.2f} - ${max_usd:,.2f}")
    print(f"🇮🇩 Estimated Monthly IDR: Rp {min_usd * 15500:,.0f} - Rp {max_usd * 15500:,.0f}")
    
    # Diamond package equivalents
    print(f"\n🎯 DIAMOND PACKAGE EQUIVALENTS:")
    packages = [100, 500, 1000, 5000, 10000]
    for package in packages:
        min_packages = min_diamonds / package
        max_packages = max_diamonds / package
        if max_packages >= 0.1:  # Only show if significant
            print(f"   {package:,} diamonds: {min_packages:.1f}-{max_packages:.1f} packages/month")
