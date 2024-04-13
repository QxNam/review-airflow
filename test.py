import requests
from pprint import pprint

# url = "http://9net.ddns.net:9008/embedding?q="
# r = requests.get('http://localhost:5099')
# print(len(r.json()['embedding']))
url='http://localhost:5099'
response = requests.post(f"{url}/search", json={"query": "Hội thảo định hướng tách ngành ĐH khóa 19"})
pprint(response.json())
print('\n')

response = requests.post(f"{url}/complete", json={"query": "Hội nghị cấp khoa được tổ chức ngày nào?"})
pprint(response.json())