#write a function to receive an url, send request with headers, output including:
#1. status code
#2. resp.text length
#3. find if there is a string "triệu" in resp.text or not

import requests

#define headers for the requests
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def test_request(url, headers=None):
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        status_code = response.status_code
        text_length = len(response.text)
        contains_string = "triệu" in response.text

        return status_code, text_length, contains_string

    except requests.exceptions.RequestException as e:
        return "ERROR", 0, str(e)


url = 'https://www.vietnamworks.com/viec-lam?g=5'
print("VietnamWorks:", test_request(url, headers=headers))

url = 'https://www.careerviet.vn/viec-lam/cong-nghe-thong-tin-c1-vi.html'
print("CareerViet:", test_request(url, headers=headers))

url = 'https://www.careerlink.vn/viec-lam/k/C%C3%B4ng-Ngh%E1%BB%87-Th%C3%B4ng-Tin'
print("CareerLink:", test_request(url, headers=headers))

url = 'https://jobsgo.vn/viec-lam-cong-nghe-thong-tin.html'
print("JobsGo:", test_request(url, headers=headers))