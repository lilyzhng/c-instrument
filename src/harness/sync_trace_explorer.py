"""Sync the frontend to the backend: inject pathfinder/trace_store.json into
pathfinder/index.html's embedded DATA literal, so a backend change always shows
up in the website. Run after any edit to trace_store.json (or the manifest
-> trace_store pipeline).

The HTML embeds the store as `const DATA = {...};` between the markers
  /*DATA_START*/ ... /*DATA_END*/
This replaces whatever is between them with the current JSON. Idempotent.

    python3 src/harness/sync_trace_explorer.py
"""

import json
import pathlib
import re

HTML = pathlib.Path("pathfinder/index.html")
STORE = pathlib.Path("pathfinder/trace_store.json")


def main():
    data = json.loads(STORE.read_text())
    html = HTML.read_text()
    payload = "const DATA = " + json.dumps(data, indent=1) + ";"
    block = "/*DATA_START*/\n" + payload + "\n/*DATA_END*/"

    if "/*DATA_START*/" in html and "/*DATA_END*/" in html:
        html = re.sub(r"/\*DATA_START\*/.*?/\*DATA_END\*/", lambda m: block, html, flags=re.S)
        HTML.write_text(html)
        print(f"synced: injected trace_store.json ({len(data['experiments'])} experiments, "
              f"{len(data['packs'])} packs) into pathfinder/index.html")
    else:
        print("WARNING: markers /*DATA_START*/ .. /*DATA_END*/ not found in the HTML.")
        print("Add them around the embedded data literal, or the frontend must reference")
        print("this store some other way. Backend is current; frontend needs the markers.")


if __name__ == "__main__":
    main()
