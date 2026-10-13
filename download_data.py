"""Download official public sources, verifying the recorded release fingerprints."""
from pathlib import Path
from urllib.request import urlopen, Request
import hashlib
import json

ROOT = Path(__file__).resolve().parent


def main():
    manifest = json.loads((ROOT / "data/sources.json").read_text())
    for entry in manifest["files"]:
        destination = ROOT / entry["path"]
        if destination.exists():
            payload = destination.read_bytes()
        else:
            request = Request(entry["url"], headers={"User-Agent": "AI-attitudes-learning-project/1.0"})
            with urlopen(request, timeout=60) as response:
                payload = response.read()
        if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
            raise ValueError(f"Unexpected source contents: {destination.name}. Review the release; do not silently replace it.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        print(f"Verified {destination.name}")


if __name__ == "__main__":
    main()
