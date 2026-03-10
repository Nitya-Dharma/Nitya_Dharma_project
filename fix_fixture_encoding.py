"""
One-off script: read a fixture file that may have encoding issues and re-save as UTF-8.
Use when loaddata fails with UnicodeDecodeError (e.g. byte 0x97 invalid start byte).

Usage:
    python fix_fixture_encoding.py data_export.json
    (creates data_export_utf8.json; then run loaddata on that file)
"""
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_fixture_encoding.py <fixture_file.json>")
        sys.exit(1)
    path = sys.argv[1]
    out_path = path.replace(".json", "_utf8.json")
    if out_path == path:
        out_path = path + "_utf8.json"
    # Read with replace so bad bytes become replacement char; then write UTF-8
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8", errors="replace")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {out_path} (UTF-8). Run: python manage.py loaddata {out_path}")

if __name__ == "__main__":
    main()
