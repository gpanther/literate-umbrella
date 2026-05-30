import sys, json
from pathlib import Path

dir_path = Path(sys.argv[1])

if not dir_path.exists() or not dir_path.is_dir():
    raise SystemExit(f"Directory not found: {dir_path}")

dir_path = Path(sys.argv[1])

to_process = set()
for html_path in dir_path.rglob("*.html"):
    text = html_path.read_text()
    if 'data-player="vPlayer-' not in text:
        continue

    json_path = html_path.with_suffix(".json")
    data = json.loads(json_path.read_text())
    url = data.get("url")
    if url in to_process:
        continue
    print(url)
    to_process.update(url)
    if len(to_process) % 100 == 0:
        print(f"Found {len(to_process)} URLs", file=sys.stderr)