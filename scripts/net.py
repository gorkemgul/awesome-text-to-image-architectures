"""HTTP download shared by the helper scripts (not used by catalog.py)."""

import shutil
import ssl
import subprocess
from urllib.error import URLError
from urllib.request import Request, urlopen

UA = "Mozilla/5.0 (awesome-text-to-image-architectures helper)"


def get(url):
    """Return (final_url, body). Falls back to curl when Python lacks CA certificates (python.org macOS builds)."""
    try:
        with urlopen(Request(url, headers={"User-Agent": UA}), timeout=60) as response:
            return response.geturl(), response.read()
    except URLError as exc:
        if not isinstance(exc.reason, ssl.SSLError) or not shutil.which("curl"):
            raise
    result = subprocess.run(["curl", "-sSfL", "-A", UA, "--max-time", "60", "-w", "\n%{url_effective}", url], check=True, capture_output=True)
    body, _, final_url = result.stdout.rpartition(b"\n")
    return final_url.decode(), body
