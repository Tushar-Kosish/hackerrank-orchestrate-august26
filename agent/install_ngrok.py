import pathlib
import urllib.request
import zipfile
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
zip_path = root / "ngrok.zip"
out_dir = root / "ngrok"
download_urls = [
    "https://github.com/ngrok/ngrok/releases/latest/download/ngrok-windows-amd64.zip",
    "https://github.com/ngrok/ngrok/releases/latest/download/ngrok-stable-windows-amd64.zip",
    "https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-windows-amd64.zip",
]

for url in download_urls:
    try:
        print(f"Downloading ngrok from {url}")
        with urllib.request.urlopen(url, timeout=60) as response:
            with zip_path.open("wb") as f:
                f.write(response.read())
        break
    except Exception as e:
        print(f"Failed to download from {url}: {e}")
else:
    raise SystemExit("Could not download ngrok from any known URL")

print(f"Extracting ngrok to {out_dir}")
out_dir.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(zip_path, "r") as z:
    z.extractall(out_dir)
found = list(out_dir.rglob("ngrok.exe"))
if not found:
    raise SystemExit("ngrok.exe not found after extraction")
print(f"ngrok installed at: {found[0]}")
print("Run this command:")
print(f"{found[0]}")
print("Then authenticate with your ngrok authtoken and start the tunnel using:")
print(f"{found[0]} authtoken <YOUR_AUTHTOKEN>")
print(f"{found[0]} http 5000")
