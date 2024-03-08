import requests

response = requests.get("https://api.github.com/user")
print(f"Status Code: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Content-Type: {response.headers['content-type']}")
print(f"Response Text: {response.text}")
print(f"Response Json: {response.json}")
