"""
Downloads emoji-picker-element JS files for offline bundling.
Run once: python download_assets.py
"""
import urllib.request, tarfile, io, os

TARBALL = "https://registry.npmjs.org/emoji-picker-element/-/emoji-picker-element-1.29.1.tgz"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

EXTRACT = {
    "package/index.js":    "emoji-picker.js",
    "package/picker.js":   "emoji-picker-picker.js",
    "package/database.js": "emoji-picker-database.js",
}

print("Downloading emoji-picker-element 1.29.1 ...")
with urllib.request.urlopen(TARBALL) as resp:
    data = resp.read()
print(f"  Downloaded {len(data):,} bytes")

with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
    for src, dst in EXTRACT.items():
        member = tar.getmember(src)
        f = tar.extractfile(member)
        content = f.read()
        dest = os.path.join(OUT_DIR, dst)
        with open(dest, "wb") as out:
            out.write(content)
        print(f"  Saved {dst} ({len(content):,} bytes)")

# Patch index.js to use local relative paths
idx = os.path.join(OUT_DIR, "emoji-picker.js")
with open(idx, "r", encoding="utf-8") as f:
    src = f.read()
src = src.replace("'./picker.js'", "'/static/emoji-picker-picker.js'")
src = src.replace("'./database.js'", "'/static/emoji-picker-database.js'")
with open(idx, "w", encoding="utf-8") as f:
    f.write(src)
print("  Patched emoji-picker.js with local paths")

print("Done.")
