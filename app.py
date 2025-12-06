from flask import Flask, request, jsonify
import csv
import os
import re

app = Flask(__name__)

def load_csv(path: str):
    rows = []
    headers = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for row in reader:
            row["__blob"] = " ".join((row.get(h, "") or "") for h in headers).lower()
            rows.append(row)
    return rows

# ----- Files -----
# Procedures CSV (existing)
CSV_PROCEDURES = os.environ.get("CSV_PATH", "data.csv")
# Reports CSV (new)
CSV_REPORTS = os.environ.get("CSV_REPORTS_PATH", "reports.csv")

# ----- Load data at startup -----
DATA_PROCEDURES = load_csv(CSV_PROCEDURES)
DATA_REPORTS = load_csv(CSV_REPORTS)

def score_row(blob: str, keywords: list[str]) -> int:
    return sum(1 for kw in keywords if kw and kw in blob)

def parse_keywords(q: str) -> list[str]:
    # Split on semicolon, comma, or any whitespace
    parts = [p.strip() for p in re.split(r"[;,]\s*|\s+", q) if p.strip()]
    return [p.lower() for p in parts]

def run_search(dataset, q: str, limit: int):
    keywords = parse_keywords(q)
    scored = []
    for i, row in enumerate(dataset):
        s = score_row(row["__blob"], keywords)
        if s > 0:
            cleaned = {k: v for k, v in row.items() if k != "__blob"}
            scored.append({"score": s, "row_index": i, "row": cleaned})
    scored.sort(key=lambda x: (-x["score"], x["row_index"]))
    return scored[:limit]

@app.get("/healthz")
def healthz():
    return {"ok": True}

# ----- Procedures (existing) -----
@app.get("/search")
def search_procedures():
    q = (request.args.get("q") or "").strip()
    limit = int(request.args.get("limit", 3))
    if not q:
        return jsonify({"error": "Missing q parameter"}), 400
    results = run_search(DATA_PROCEDURES, q, limit)
    return jsonify({"query": q, "count": len(results), "results": results})

# ----- Reports (new) -----
@app.get("/search_reports")
def search_reports():
    q = (request.args.get("q") or "").strip()
    limit = int(request.args.get("limit", 3))
    if not q:
        return jsonify({"error": "Missing q parameter"}), 400
    results = run_search(DATA_REPORTS, q, limit)
    return jsonify({"query": q, "count": len(results), "results": results})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
