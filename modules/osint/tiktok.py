import requests
import json
import re
import time
from urllib.parse import quote

MODULE_INFO = {
    "name": "osint/tiktok_web_fixed",
    "description": "Fixed TikTok OSINT using multiple web API methods"
}

OPTIONS = {
    "USERNAME": {
        "required": True,
        "default": "",
        "description": "TikTok username without @"
    },
    "METHOD": {
        "required": False,
        "default": "auto",
        "description": "API method: auto, mobile, web, or html"
    }
}

def run(session, options):
    username = options.get("USERNAME", "").strip().lower()
    method = options.get("METHOD", "auto")
    
    if not username:
        print("❌ Error: USERNAME is required")
        return
    
    print(f"🔍 Investigating @{username} using TikTok Web APIs...")
    print("🔄 Trying multiple methods to fetch data...")
    
    try:
        user_data = None
        
        if method == "auto" or method == "mobile":
            print("\n📱 Trying Mobile API method...")
            user_data = get_user_via_mobile_api(username)
        
        if not user_data and (method == "auto" or method == "web"):
            print("\n🌐 Trying Web API method...")
            user_data = get_user_via_web_api(username)
        
        if not user_data and (method == "auto" or method == "html"):
            print("\n📄 Trying HTML parsing method...")
            user_data = get_user_via_html(username)
        
        if not user_data:
            print("❌ All methods failed to fetch user data")
            print("\n💡 Tips:")
            print("   - Username mungkin salah atau akun di-private")
            print("   - Coba metode lain: set METHOD mobile/web/html")
            print("   - Pastikan username tanpa @")
            return
        
        display_user_info(user_data)
        
        # Get videos if secUid available
        if user_data.get('secUid'):
            print("\n📹 Fetching user videos...")
            videos = get_user_videos(user_data['secUid'])
            if videos:
                display_videos_info(videos, username)
        else:
            print("\n⚠️ Cannot fetch videos (missing secUid)")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def get_user_via_mobile_api(username):
    """Get user data via mobile API endpoint"""
    try:
        headers = {
            'User-Agent': 'TikTok 26.2.0 rv:262018 (iPhone; iOS 14.4.2; en_US) Cronet',
            'Accept': 'application/json',
        }
        
        # Mobile API endpoint
        url = f"https://api16-normal-c-useast1a.tiktokv.com/tiktok/user/detail/?unique_id={username}"
        
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   Mobile API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('user_info'):
                print("   ✅ Mobile API success!")
                return extract_user_data_mobile(data['user_info'])
        
        return None
        
    except Exception as e:
        print(f"   ❌ Mobile API error: {str(e)}")
        return None

def get_user_via_web_api(username):
    """Get user data via web API endpoint"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': f'https://www.tiktok.com/@{username}',
            'Origin': 'https://www.tiktok.com'
        }
        
        # Try multiple web API endpoints
        endpoints = [
            f"https://www.tiktok.com/node/share/user/@{username}",
            f"https://www.tiktok.com/api/user/detail/?uniqueId={username}",
            f"https://tiktok.com/api/user/detail/?uniqueId={username}",
        ]
        
        for i, endpoint in enumerate(endpoints, 1):
            try:
                print(f"   Trying endpoint {i}: {endpoint.split('/')[-1]}")
                response = requests.get(endpoint, headers=headers, timeout=15)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    user_data = extract_user_data_web(data)
                    if user_data:
                        print("   ✅ Web API success!")
                        return user_data
                        
            except Exception as e:
                print(f"   Endpoint {i} error: {str(e)}")
                continue
        
        return None
        
    except Exception as e:
        print(f"   ❌ Web API error: {str(e)}")
        return None

def get_user_via_html(username):
    """Get user data by parsing HTML page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        url = f"https://www.tiktok.com/@{username}"
        print(f"   Fetching: {url}")
        
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   HTML Status: {response.status_code}")
        
        if response.status_code == 200:
            user_data = extract_user_from_html(response.text, username)
            if user_data:
                print("   ✅ HTML parsing success!")
                return user_data
            else:
                print("   ⚠️ Found page but could not extract user data")
        
        return None
        
    except Exception as e:
        print(f"   ❌ HTML parsing error: {str(e)}")
        return None

def extract_user_data_mobile(user_info):
    """Extract user data from mobile API response"""
    return {
        'username': user_info.get('unique_id') or user_info.get('uniqueId'),
        'nickname': user_info.get('nickname'),
        'signature': user_info.get('signature', ''),
        'verified': user_info.get('verified', False),
        'private': user_info.get('private_account', False) or user_info.get('privateAccount', False),
        'followers': user_info.get('follower_count') or user_info.get('followerCount', 0),
        'following': user_info.get('following_count') or user_info.get('followingCount', 0),
        'hearts': user_info.get('total_favorited') or user_info.get('heartCount', 0),
        'videos': user_info.get('aweme_count') or user_info.get('videoCount', 0),
        'diggs': user_info.get('digg_count', 0),
        'secUid': user_info.get('sec_uid') or user_info.get('secUid'),
        'userId': user_info.get('uid') or user_info.get('id'),
        'avatar': user_info.get('avatar_larger') or user_info.get('avatarThumb', '')
    }

def extract_user_data_web(api_data):
    """Extract user data from web API response"""
    user = {}
    
    # Multiple possible response structures
    if 'userInfo' in api_data and 'user' in api_data['userInfo']:
        user_data = api_data['userInfo']['user']
    elif 'user' in api_data:
        user_data = api_data['user']
    elif 'data' in api_data and 'user' in api_data['data']:
        user_data = api_data['data']['user']
    else:
        return None
    
    return {
        'username': user_data.get('uniqueId'),
        'nickname': user_data.get('nickname'),
        'signature': user_data.get('signature', ''),
        'verified': user_data.get('verified', False),
        'private': user_data.get('privateAccount', False),
        'followers': user_data.get('followerCount', 0),
        'following': user_data.get('followingCount', 0),
        'hearts': user_data.get('heartCount', 0),
        'videos': user_data.get('videoCount', 0),
        'diggs': user_data.get('diggCount', 0),
        'secUid': user_data.get('secUid'),
        'userId': user_data.get('id'),
        'avatar': user_data.get('avatarThumb', '')
    }

def extract_user_from_html(html_content, username):
    """Extract user data from HTML page"""
    try:
        # Method 1: Look for JSON data in script tags
        script_patterns = [
            r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>',
            r'window\[\'SIGI_STATE\'\]\s*=\s*(.*?);\s*window\[\'SIGI_RETRY\'\]',
            r'"userDetail":\s*(\{.*?\})',
        ]
        
        for pattern in script_patterns:
            match = re.search(pattern, html_content, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1)
                    data = json.loads(json_str)
                    
                    # Navigate through possible JSON structures
                    user_data = find_user_in_json(data, username)
                    if user_data:
                        return user_data
                except json.JSONDecodeError:
                    continue
        
        # Method 2: Look for meta tags
        meta_patterns = {
            'followers': r'"followerCount"\s*:\s*"(\d+)"',
            'following': r'"followingCount"\s*:\s*"(\d+)"',
            'likes': r'"heartCount"\s*:\s*"(\d+)"',
            'videos': r'"videoCount"\s*:\s*"(\d+)"',
        }
        
        user_data = {'username': username, 'nickname': username}
        for key, pattern in meta_patterns.items():
            match = re.search(pattern, html_content)
            if match:
                user_data[key] = int(match.group(1))
        
        if len(user_data) > 2:  # If we found at least one metric
            return user_data
        
        # Method 3: Check if user exists by looking for specific elements
        if "Page not found" not in html_content and "This page is not available" not in html_content:
            return {'username': username, 'nickname': username, 'exists': True}
        
        return None
        
    except Exception as e:
        print(f"   HTML extraction error: {str(e)}")
        return None

def find_user_in_json(data, username):
    """Recursively search for user data in JSON structure"""
    if isinstance(data, dict):
        # Check common paths for user data
        paths = [
            ['UserModule', 'users', username],
            ['UserPage', 'userInfo', 'user'],
            ['userDetail', 'userInfo', 'user'],
            ['props', 'pageProps', 'userInfo', 'user'],
        ]
        
        for path in paths:
            current = data
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    break
            else:
                if current and isinstance(current, dict):
                    return extract_user_data_web({'user': current})
        
        # Recursive search
        for value in data.values():
            result = find_user_in_json(value, username)
            if result:
                return result
    
    elif isinstance(data, list):
        for item in data:
            result = find_user_in_json(item, username)
            if result:
                return result
    
    return None

def get_user_videos(sec_uid, count=20):
    """Get user videos via web API"""
    try:
        url = "https://www.tiktok.com/api/post/item_list/"
        params = {
            'aid': '1988',
            'secUid': sec_uid,
            'count': count,
            'cursor': '0'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'https://www.tiktok.com/',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('itemList'):
                return data['itemList']
            elif data.get('items'):
                return data['items']
        
        return None
        
    except Exception as e:
        print(f"   ❌ Videos API error: {str(e)}")
        return None

def display_user_info(user_data):
    """Display user information"""
    print(f"\n{'='*60}")
    print("👤 TIKTOK USER INFORMATION")
    print(f"{'='*60}")
    
    print(f"📛 Username: @{user_data.get('username', 'N/A')}")
    print(f"👤 Display Name: {user_data.get('nickname', 'N/A')}")
    
    if user_data.get('signature'):
        print(f"📝 Bio: {user_data.get('signature')}")
    
    if user_data.get('followers', 0) > 0:
        print(f"👥 Followers: {user_data.get('followers', 0):,}")
        print(f"🤝 Following: {user_data.get('following', 0):,}")
        print(f"❤️  Total Likes: {user_data.get('hearts', 0):,}")
        print(f"🎬 Videos: {user_data.get('videos', 0):,}")
    else:
        print("📊 Stats: Not available (account may be private or data limited)")
    
    print(f"🔒 Private: {'Yes' if user_data.get('private') else 'No'}")
    print(f"✅ Verified: {'Yes' if user_data.get('verified') else 'No'}")
    
    if user_data.get('userId'):
        print(f"🆔 User ID: {user_data.get('userId')}")
    if user_data.get('secUid'):
        print(f"🔐 Sec UID: {user_data.get('secUid')[:20]}...")

def display_videos_info(videos, username):
    """Display user videos information"""
    if not videos:
        print("❌ No videos found or account is private")
        return
    
    print(f"\n{'='*60}")
    print(f"🎬 RECENT VIDEOS - @{username}")
    print(f"{'='*60}")
    
    print(f"📊 Found {len(videos)} videos")
    
    # Show top videos by engagement
    if len(videos) > 0:
        top_videos = sorted(videos, key=lambda x: x.get('stats', {}).get('diggCount', 0), reverse=True)[:3]
        
        print(f"\n🏆 Top {len(top_videos)} Most Popular Videos:")
        for i, video in enumerate(top_videos, 1):
            stats = video.get('stats', {})
            create_time = time.strftime('%Y-%m-%d', time.localtime(video.get('createTime', 0)))
            desc = video.get('desc', 'No description')
            if len(desc) > 60:
                desc = desc[:60] + "..."
            
            print(f"  {i}. {desc}")
            print(f"     ❤️ {stats.get('diggCount', 0):,} likes | 💬 {stats.get('commentCount', 0):,} comments")
            print(f"     🔄 {stats.get('shareCount', 0):,} shares | 📅 {create_time}")
