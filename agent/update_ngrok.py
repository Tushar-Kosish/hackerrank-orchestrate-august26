import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent
ngrok_dir = root / 'ngrok'
ngrok_dir.mkdir(parents=True, exist_ok=True)
ngrok_path = ngrok_dir / 'ngrok.exe'

urls = [
    'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-windows-amd64.zip',
]

for url in urls:
    print(f'Downloading ngrok from {url}')
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            zip_path = tmpdir / 'ngrok.zip'
            urllib.request.urlretrieve(url, zip_path)
            print(f'  downloaded {zip_path.stat().st_size} bytes')
            with zipfile.ZipFile(zip_path, 'r') as z:
                names = z.namelist()
                print('  archive contents:', names[:10])
                if 'ngrok.exe' not in names:
                    raise RuntimeError('ngrok.exe not found in archive')
                z.extract('ngrok.exe', tmpdir)
            extracted = tmpdir / 'ngrok.exe'
            if not extracted.exists():
                raise RuntimeError('Extracted ngrok.exe missing')
            shutil.copy2(extracted, ngrok_path)
            print(f'Installed ngrok to {ngrok_path}')
            proc = __import__('subprocess').run([str(ngrok_path), 'version'], capture_output=True, text=True)
            print('ngrok version rc', proc.returncode)
            print(proc.stdout)
            print(proc.stderr)
        break
    except Exception as exc:
        print('Failed to update from', url, exc)
else:
    sys.exit('Could not download or install ngrok')
