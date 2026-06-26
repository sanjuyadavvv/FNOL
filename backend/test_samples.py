import json
from pathlib import Path
import urllib.request

samples = Path(__file__).resolve().parent.parent / "sample-documents"
for f in sorted(samples.glob("*.txt")):
    with open(f, "rb") as fh:
        data = fh.read()
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{f.name}"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        "http://localhost:8000/api/process-fnol",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    print(f.name, "->", result["recommendedRoute"])
    print("  missing:", result["missingFields"])
    print("  reasoning:", result["reasoning"][:100])
    print()
