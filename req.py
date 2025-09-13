import requests
word = {
  "email": "user3@example.com",
  "full_name": "string",
  "password": "string",
  "role": "student"
}
response = requests.post("http://83.166.247.181:8000/auth/register", json=word)
print(response.text)