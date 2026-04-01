"""Print Image_Path for each record in records.pkl (for deployment: copy these files to server)."""
import os
import pickle
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(ROOT, "records.pkl")

if not os.path.exists(path):
    print("No records.pkl found.", file=sys.stderr)
    sys.exit(1)

with open(path, "rb") as f:
    records = pickle.load(f)

print("Files that must exist under uploaded_images/ for matching-record images to load:\n")
for i, r in enumerate(records):
    p = r.get("Image_Path", "")
    fn = p.replace("uploaded_images/", "").replace("uploaded_images\\", "")
    print(f"  [{i}] {p}")
    print(f"      copy to server: uploaded_images/{fn}\n")
