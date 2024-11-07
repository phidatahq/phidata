import http.client
import json

conn = http.client.HTTPSConnection("google.serper.dev")
payload = json.dumps({"q": "apple inc"})
headers = {"X-API-KEY": "d8b60401260c0238aadb5a92c23334428bc71b59", "Content-Type": "application/json"}
conn.request("POST", "/autocomplete", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
