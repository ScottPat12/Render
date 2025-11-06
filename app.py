from flask import Flask, request, jsonify
import csv
import os

app = Flask(__name__)

# ---- Load CSV at startup ----
DATA = []
HEADERS = []
CSV_PATH = os.environ.get("CSV_PATH", "data.csv")

with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)  # header row REQUIRED
    HEADERS = reader.fieldnames or []
    for row in reader:
        # Precompute lowercase blob for matching
        row["__blob"] = " ".join((row.get(h, "") or "") for h in HEADERS).lower()
        DATA.append(row)

def score_row(blob: str, keywords: list[str]) -> int:
    return sum(1 for kw in keywords if kw and kw in blob)

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/search")
def search():
    q = (request.args.get("q") or "").strip().lower()
    limit = int(request.args.get("limit", 3))

    if not q:
        return jsonify({"error": "Missing q parameter"}), 400

    # Split on commas/whitespace, drop empties
    raw_parts = [p.strip() for p in q.replace(",", " ").split()]
    keywords = [p for p in raw_parts if p]

    scored = []
    for i, row in enumerate(DATA):
        s = score_row(row["__blob"], keywords)
        if s > 0:
            cleaned = {k: v for k, v in row.items() if k != "__blob"}
            scored.append({"score": s, "row_index": i, "row": cleaned})

    scored.sort(key=lambda x: (-x["score"], x["row_index"]))
    return jsonify({
        "query": keywords,
        "count": min(len(scored), limit),
        "results": scored[:limit],
    })

# Local dev only; Render uses Gunicorn to run the app
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
