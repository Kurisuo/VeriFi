import html
import json
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT_DIR / "output" / "chunks.jsonl"
LAYOUT_OUTPUT_PATH = ROOT_DIR / "output" / "layout_chunks.jsonl"
STATS_PATH = ROOT_DIR / "output" / "ingestion_stats.json"
MAIN_PATH = ROOT_DIR / "data_ingestion" / "main.py"
VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_ingestion.validator import validate_records


INGESTION_LOCK = threading.Lock()


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Chunk Viewer</title>
  <style>
    body {
      margin: 0;
      font-family: Arial, sans-serif;
      background: #f6f6f6;
      color: #222;
    }

    header {
      position: sticky;
      top: 0;
      z-index: 1;
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid #ddd;
      background: white;
    }

    button {
      padding: 8px 12px;
      border: 1px solid #999;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
      font-size: 14px;
    }

    button:disabled {
      opacity: 0.6;
      cursor: default;
    }

    a {
      color: #174ea6;
      font-size: 14px;
      text-decoration: none;
    }

    a.active {
      font-weight: bold;
      text-decoration: underline;
    }

    #status {
      font-size: 14px;
      white-space: pre-wrap;
    }

    main {
      padding: 16px;
    }

    #summary {
      margin-bottom: 12px;
    }

    .summary-card {
      border: 1px solid #ccc;
      border-radius: 4px;
      background: white;
      padding: 12px;
      font-size: 14px;
    }

    #chunks {
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: calc(100vh - 84px);
      overflow-y: auto;
      padding-right: 6px;
    }

    .chunk {
      border: 1px solid #ccc;
      border-radius: 4px;
      background: white;
      padding: 12px;
    }

    .chunk-title {
      margin-bottom: 8px;
      font-size: 14px;
      font-weight: bold;
    }

    .metadata {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 8px;
    }

    .meta-item {
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 3px 6px;
      background: #fafafa;
      font-size: 12px;
    }

    .warning {
      border-color: #e0a800;
      background: #fff8e1;
    }

    .error {
      border-color: #b00020;
      background: #fde7ea;
    }

    details {
      margin-bottom: 8px;
      font-size: 12px;
    }

    pre {
      max-height: 220px;
      overflow: auto;
      border: 1px solid #ddd;
      padding: 8px;
      background: #fafafa;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .text {
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 14px;
    }

    mark {
      background: #fff176;
      padding: 0 1px;
    }

    .empty {
      padding: 16px;
      border: 1px dashed #aaa;
      background: white;
    }
  </style>
</head>
<body>
  <header>
    <button id="run">Run ingestion</button>
    <button id="refresh">Refresh chunks</button>
    <a href="/" id="raw-link">Raw chunks</a>
    <a href="/semantic" id="semantic-link">Semantic chunks</a>
    <a href="/validated" id="validated-link">Validated semantic chunks</a>
    <span id="status">Loading...</span>
  </header>
  <main>
    <div id="summary"></div>
    <div id="chunks"></div>
  </main>

  <script>
    const runButton = document.getElementById("run");
    const refreshButton = document.getElementById("refresh");
    const statusEl = document.getElementById("status");
    const summaryEl = document.getElementById("summary");
    const chunksEl = document.getElementById("chunks");
    const viewMode = window.location.pathname === "/validated"
      ? "validated"
      : window.location.pathname === "/semantic"
        ? "semantic"
        : "layout";
    const isValidatedView = viewMode === "validated";

    document.getElementById(`${viewMode === "layout" ? "raw" : viewMode}-link`).classList.add("active");

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function summarizeValue(value) {
      if (Array.isArray(value)) {
        if (value.every((item) => typeof item === "number")) {
          return `number[${value.length}]`;
        }
        return `array[${value.length}]`;
      }

      if (value && typeof value === "object") {
        return "object";
      }

      if (typeof value === "string" && value.length > 120) {
        return `string[${value.length}]`;
      }

      return String(value);
    }

    function renderText(record) {
      const words = record.text.split(/(\\s+)/);
      let wordIndex = 0;
      let html = "";

      for (const part of words) {
        if (part.trim() === "") {
          html += escapeHtml(part);
          continue;
        }

        const isStartOverlap = wordIndex < record.overlap_with_previous_words;
        const isEndOverlap = wordIndex >= record.total_words - record.overlap_with_next_words;
        const escaped = escapeHtml(part);

        if (isStartOverlap || isEndOverlap) {
          html += `<mark>${escaped}</mark>`;
        } else {
          html += escaped;
        }

        wordIndex += 1;
      }

      return html;
    }

    function renderMetadata(record) {
      return Object.entries(record.metadata)
        .map(([key, value]) => {
          return `<span class="meta-item"><strong>${escapeHtml(key)}:</strong> ${escapeHtml(summarizeValue(value))}</span>`;
        })
        .join("");
    }

    function renderSummary(data) {
      const validation = data.summary;
      const ingestion = data.ingestion;
      const warningCounts = Object.entries(validation?.warning_counts || {})
        .map(([key, value]) => {
          return `<span class="meta-item warning"><strong>${escapeHtml(key)}:</strong> ${escapeHtml(value)}</span>`;
        })
        .join("");

      const validationCard = validation ? `
        <div class="summary-card">
          <div class="metadata">
            <span class="meta-item"><strong>Input:</strong> ${escapeHtml(validation.input_records)}</span>
            <span class="meta-item"><strong>Shown:</strong> ${escapeHtml(validation.validated_records)}</span>
            <span class="meta-item"><strong>Dropped:</strong> ${escapeHtml(validation.dropped_records)}</span>
            <span class="meta-item ${validation.hard_errors ? "error" : ""}"><strong>Errors:</strong> ${escapeHtml(validation.hard_errors)}</span>
            <span class="meta-item ${validation.warnings ? "warning" : ""}"><strong>Warnings:</strong> ${escapeHtml(validation.warnings)}</span>
          </div>
          <div class="metadata">${warningCounts}</div>
        </div>
      ` : "";

      const timingEntries = Object.entries(ingestion?.timings || {})
        .map(([key, value]) => `<span class="meta-item"><strong>${escapeHtml(key.replaceAll("_", " "))}:</strong> ${escapeHtml(Number(value).toFixed(4))}s</span>`)
        .join("");
      const extractionCache = ingestion?.cache?.extraction;
      const cacheEntries = extractionCache ? `
        <span class="meta-item"><strong>Extraction cache hits:</strong> ${escapeHtml(extractionCache.hits)}</span>
        <span class="meta-item"><strong>Extraction cache misses:</strong> ${escapeHtml(extractionCache.misses)}</span>
      ` : "";
      const timingCard = ingestion ? `
        <div class="summary-card">
          <div class="metadata">
            <span class="meta-item"><strong>Documents:</strong> ${escapeHtml(ingestion.documents)}</span>
            <span class="meta-item"><strong>Pages:</strong> ${escapeHtml(ingestion.pages)}</span>
            <span class="meta-item"><strong>Layout chunks:</strong> ${escapeHtml(ingestion.layout_chunks)}</span>
            <span class="meta-item"><strong>Semantic chunks:</strong> ${escapeHtml(ingestion.semantic_chunks)}</span>
            ${cacheEntries}
          </div>
          <div class="metadata">${timingEntries}</div>
        </div>
      ` : "";

      summaryEl.innerHTML = `${timingCard}${validationCard}`;
    }

    function renderChunks(data) {
      const labels = {
        layout: "layout chunks",
        semantic: "semantic chunks",
        validated: "validated semantic chunks",
      };
      statusEl.textContent = `${data.records.length} ${labels[viewMode]} loaded`;
      renderSummary(data);

      if (!data.records.length) {
        chunksEl.innerHTML = '<div class="empty">No chunks found. Run ingestion first.</div>';
        return;
      }

      chunksEl.innerHTML = data.records.map((record) => {
        return `
          <section class="chunk">
            <div class="chunk-title">Chunk ${escapeHtml(record.metadata.chunk_index ?? "")}</div>
            <div class="metadata">${renderMetadata(record)}</div>
            <details>
              <summary>All metadata</summary>
              <pre>${escapeHtml(JSON.stringify(record.metadata, null, 2))}</pre>
            </details>
            <div class="text">${renderText(record)}</div>
          </section>
        `;
      }).join("");
    }

    async function loadChunks() {
      const endpoints = {
        layout: "/api/layout-chunks",
        semantic: "/api/semantic-chunks",
        validated: "/api/validated-chunks",
      };
      const response = await fetch(endpoints[viewMode]);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to load chunks");
      }

      renderChunks(data);
    }

    async function runIngestion() {
      runButton.disabled = true;
      refreshButton.disabled = true;
      statusEl.textContent = "Running data_ingestion/main.py...";

      try {
        const response = await fetch("/api/run", { method: "POST" });
        const data = await response.json();

        if (!response.ok) {
          statusEl.textContent = data.output || data.error || "Run failed";
          return;
        }

        statusEl.textContent = `Run complete in ${Number(data.elapsed_seconds).toFixed(4)}s\n${data.output || ""}`;
        await loadChunks();
      } finally {
        runButton.disabled = false;
        refreshButton.disabled = false;
      }
    }

    runButton.addEventListener("click", runIngestion);
    refreshButton.addEventListener("click", () => {
      statusEl.textContent = "Refreshing...";
      loadChunks().catch((error) => {
        statusEl.textContent = error.message;
      });
    });

    loadChunks().catch((error) => {
      statusEl.textContent = error.message;
      chunksEl.innerHTML = '<div class="empty">No chunks loaded.</div>';
    });
  </script>
</body>
</html>
"""


def read_records(path=OUTPUT_PATH):
    if not path.exists():
        return []

    records = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    return records


def read_ingestion_stats():
    if not STATS_PATH.exists():
        return None
    with STATS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def split_words(text):
    return text.split()


def common_overlap(previous_text, current_text):
    previous_words = split_words(previous_text)
    current_words = split_words(current_text)
    max_words = min(len(previous_words), len(current_words))

    for count in range(max_words, 0, -1):
        if previous_words[-count:] == current_words[:count]:
            return count

    return 0


def prepare_records(records):
    prepared = []
    previous_overlaps = [0] * len(records)
    next_overlaps = [0] * len(records)

    for index in range(1, len(records)):
        overlap = common_overlap(records[index - 1].get("text", ""), records[index].get("text", ""))
        next_overlaps[index - 1] = overlap
        previous_overlaps[index] = overlap

    for index, record in enumerate(records):
        metadata = {
            key: value
            for key, value in record.items()
            if key != "text"
        }

        words = split_words(record.get("text", ""))
        prepared.append({
            "metadata": metadata,
            "text": record.get("text", ""),
            "total_words": len(words),
            "overlap_with_previous_words": previous_overlaps[index],
            "overlap_with_next_words": next_overlaps[index],
        })

    return prepared


def run_ingestion():
    python_path = VENV_PYTHON if VENV_PYTHON.exists() else "python3"
    started = time.perf_counter()
    completed = subprocess.run(
        [str(python_path), str(MAIN_PATH)],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )

    output = completed.stdout
    if completed.stderr:
        output = f"{output}\n{completed.stderr}".strip()

    elapsed_seconds = time.perf_counter() - started
    return completed.returncode, output, elapsed_seconds, read_ingestion_stats()


class ChunkViewerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in {"/", "/semantic", "/validated"}:
            self.respond_html(HTML_PAGE)
            return

        if self.path in {"/api/chunks", "/api/layout-chunks"}:
            records = prepare_records(read_records(LAYOUT_OUTPUT_PATH))
            self.respond_json({
                "records": records,
                "ingestion": read_ingestion_stats(),
            })
            return

        if self.path == "/api/semantic-chunks":
            records = prepare_records(read_records(OUTPUT_PATH))
            self.respond_json({
                "records": records,
                "ingestion": read_ingestion_stats(),
            })
            return

        if self.path == "/api/validated-chunks":
            result = validate_records(read_records(OUTPUT_PATH))
            records = prepare_records(result["records"])
            self.respond_json({
                "records": records,
                "summary": result["summary"],
                "dropped_records": result["dropped_records"],
                "ingestion": read_ingestion_stats(),
            })
            return

        if self.path == "/api/stats":
            self.respond_json({"ingestion": read_ingestion_stats()})
            return

        self.send_error(404)

    def do_POST(self):
        if self.path == "/api/run":
            if not INGESTION_LOCK.acquire(blocking=False):
                self.respond_json({"error": "Ingestion is already running"}, status=409)
                return
            try:
                returncode, output, elapsed_seconds, stats = run_ingestion()
            finally:
                INGESTION_LOCK.release()
            status = 200 if returncode == 0 else 500
            self.respond_json({
                "returncode": returncode,
                "output": output,
                "elapsed_seconds": round(elapsed_seconds, 4),
                "ingestion": stats,
            }, status=status)
            return

        self.send_error(404)

    def log_message(self, format, *args):
        return

    def respond_html(self, body, status=200):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def respond_json(self, body, status=200):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8765), ChunkViewerHandler)
    print("Chunk viewer running at http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
