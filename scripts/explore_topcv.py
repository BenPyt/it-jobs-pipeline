'''
Write a script to test several request configurations against TopCV one by one and print the status code for each:

`
1.requests.get(url)` plain — expect a 403 (to serve as a baseline)
2.Add `User-Agent` — the pipeline's current configuration
3.Add a full set of browser headers: `Accept`, `Accept-Language`, `Accept-Encoding`, `Referer` (set to `https://www.google.com/`), `Sec-Fetch-Mode: navigate`, `Sec-Fetch-Site: cross-site`, `Upgrade-Insecure-Requests: 1`, `Connection: keep-alive`
4.Use `requests.Session()`: visit the homepage (`https://www.topcv.vn`) first to obtain cookies, pause for 2 seconds, then visit the list page
'''
import requests
import time

#1 Plain request
url = 'https://www.topcv.vn/'
response = requests.get(url)
print(f"Plain request status code: {response.status_code}")

#2 Request with User-Agent
headers_user_agent = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
response = requests.get(url, headers=headers_user_agent)
print(f"Request with User-Agent status code: {response.status_code}")

#3 Request with full set of browser headers
headers_full = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.google.com/',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Upgrade-Insecure-Requests': '1',
    'Connection': 'keep-alive'
}
response = requests.get(url, headers=headers_full)
print(f"Request with full set of browser headers status code: {response.status_code}")

#4 Using requests.Session()
session = requests.Session()
session.get('https://www.topcv.vn/')
time.sleep(2)
response = session.get('https://www.topcv.vn/viec-lam')
print(f"Request with Session status code: {response.status_code}")
