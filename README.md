# Log Analyzer

A simple Python tool that reads a server log file and prints a summary report.
Written using basic Python only — no pip install needed.

---

## How to run (Google Colab or any computer)

### Step 1 — Make a test log file

```
python scripts/generate_logs.py
```

This creates a file called `sample.log` with 2000 fake log lines.

### Step 2 — Analyze the log file

```
python log_analyzer.py sample.log
```

That's it! You will see a full report in the terminal.

---

## To analyze your own log file

```
python log_analyzer.py /path/to/your/logfile.log
```

---

## What the report shows

- How many lines were parsed vs skipped (and why)
- Total requests and error count
- Status code breakdown (200, 404, 500, etc.)
- HTTP method breakdown (GET, POST, etc.)
- Response time stats (fastest, average, p95, slowest)
- Top 10 slowest endpoints
- Top 10 most requested paths
- Top 10 paths with the most errors
- Top 10 busiest IP addresses
- Automatic warnings if something looks wrong

---

## Project files

```
log-analyzer/
├── log_analyzer.py          ← main tool (run this)
├── scripts/
│   └── generate_logs.py     ← creates test data (run first)
├── README.md
└── ANSWERS.md
```

---

## Requirements

- Python 3.7 or newer
- No extra packages needed (uses only built-in Python)

---

## Google Colab instructions

1. Open a new Colab notebook at colab.research.google.com
2. Upload `log_analyzer.py` and the `scripts/` folder using the files panel on the left
3. In a code cell, run:

```python
!python scripts/generate_logs.py
!python log_analyzer.py sample.log
```
