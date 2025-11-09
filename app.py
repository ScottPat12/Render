from flask import Flask, request, jsonify
import csv, os, re, logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------- Utility functions ----------------
def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for row in reader:
            # join all fields, normalize spaces, lowercase
            text = " ".join((row.get(h, "") or "") for h in headers)
            row["__blob"] = re.sub(r"\s+", " ", text).lower().strip()
            rows.append(row)
    return rows

def safe_load_csv(path, default=None):
    if default is None:
        default = []
    if not os.path.exists(path):
        print(f"⚠️ WARNING: CSV not found at {path}. Using empty dataset.")
        return default
    return load_csv(path)

def score_row(blob: str, keywords: list[str]) -> int:
    return sum(1 for kw in keywords if kw and kw in blob)

def run_search(dataset, q: str, limit: int):
    raw_parts = [p.strip() for p in q.replace(",", " ").split()]
    keywords = [p.lower() for p in raw_parts if p]
    scored = []
    for i, row in enumerate(dataset):
        s = score_row(row["__blob"], keywords)
        if s > 0:
            cleaned = {k: v for k, v in row.items() if k != "__blob"}
            scored.append({"score": s, "row_index": i, "row": cleaned})
    scored.sort(key=lambda x: (-x["score"], x["row_index"]))
    return scored[:limit]

# ---------------- File paths ----------------
CSV_PROCEDURES = os.environ.get("CSV_PATH", "data.csv")
CSV_REPORTS = os.environ.get("CSV_REPORTS_PATH", "reports.csv")

# ---------------- Load data ----------------
DATA_PROCEDURES = safe_load_csv(CSV_PROCEDURES)
DATA_REPORTS = safe_load_csv(CSV_REPORTS)

# ---------------- Endpoints ----------------
@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/search")
def search_procedures():
    q = (request.args.get("q") or "").strip()
    limit = int(request.args.get("limit", 3))
    if not q:
        return jsonify({"error": "Missing q parameter"}), 400
    results = run_search(DATA_PROCEDURES, q, limit)
    app.logger.info(f"PROCEDURE SEARCH: q='{q}', results={len(results)}")
    return jsonify({"query": q, "count": len(results), "results": results})

@app.get("/search_reports")
def search_reports():
    q = (request.args.get("q") or "").strip()
    limit = int(request.args.get("limit", 3))
    if not q:
        return jsonify({"error": "Missing q parameter"}), 400
    results = run_search(DATA_REPORTS, q, limit)
    app.logger.info(f"REPORTS SEARCH: q='{q}', results={len(results)}")
    return jsonify({"query": q, "count": len(results), "results": results})

# optional debug route (remove later)
@app.get("/debug/reports_count")
def debug_reports():
    return jsonify({"loaded_reports": len(DATA_REPORTS)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
