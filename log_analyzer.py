"""
log_analyzer.py
---------------
A simple tool that reads a server log file and prints a summary report.

How to run:
    python log_analyzer.py sample.log

What it does:
    - Reads every line in the log file
    - Tries to understand each line
    - Counts things (status codes, slow requests, busy IPs, etc.)
    - Prints a nice report at the end
    - Skips broken lines and tells you how many were skipped

No external libraries needed — only built-in Python.
"""

import sys    # to read the filename from the command line
import json   # to handle JSON-formatted lines


# ================================================================
# STEP 1 — READ THE FILE
# ================================================================

def read_file(filename):
    """
    Opens a file and returns all its lines as a list of strings.
    If the file doesn't exist, it prints an error and stops.
    """
    try:
        with open(filename, "r") as f:
            lines = f.readlines()   # reads every line into a list
        print(f"File opened: {filename}")
        print(f"Total lines in file: {len(lines)}")
        return lines

    except FileNotFoundError:
        print(f"ERROR: Could not find file '{filename}'")
        print("Please check the filename and try again.")
        sys.exit(1)   # stop the program with an error code


# ================================================================
# STEP 2 — PARSE ONE LINE
# ================================================================

def parse_response_time(token):
    """
    Converts a response time string to a float in milliseconds.
    Examples:
        "142ms"   → 142.0
        "0.142s"  → 142.0
        "142"     → 142.0   (we assume ms when no unit given)
        "abc"     → None    (can't understand it)
    """
    token = token.strip()

    # Case 1: ends with "ms"  →  just remove "ms" and convert
    if token.lower().endswith("ms"):
        number_part = token[:-2]   # remove last 2 characters ("ms")
        try:
            return float(number_part)
        except ValueError:
            return None

    # Case 2: ends with "s"  →  remove "s" and multiply by 1000
    if token.lower().endswith("s"):
        number_part = token[:-1]   # remove last 1 character ("s")
        try:
            return float(number_part) * 1000.0
        except ValueError:
            return None

    # Case 3: just a plain number — assume it is milliseconds
    try:
        return float(token)
    except ValueError:
        return None   # could not understand it at all


def parse_status_code(token):
    """
    Converts a status code string to an integer.
    Examples:
        "200" → 200
        "404" → 404
        "-"   → None  (missing status code)
        "abc" → None  (broken)
    """
    if token == "-":
        return None   # dash means status was not logged

    try:
        code = int(token)
        # Valid HTTP status codes are between 100 and 599
        if 100 <= code <= 599:
            return code
        else:
            return None
    except ValueError:
        return None


def parse_timestamp(token):
    """
    Checks if a token looks like a timestamp.
    We do a very simple check — just look at the shape of the string.
    Returns the token as-is if it looks like a timestamp, or None if not.

    We support these shapes:
      2024-03-15T14:23:01Z   ← ISO format
      2024/03/15             ← slash format (first token of two)
      15-Mar-2024            ← day-month-year
      1710512581             ← unix epoch (10-digit number)
    """
    token = token.strip()

    # ISO format: starts with 4 digits, then a dash
    # Example: 2024-03-15T14:23:01Z
    if len(token) >= 10 and token[4] == "-" and token[7] == "-":
        return token

    # Slash format: starts with 4 digits, then a slash
    # Example: 2024/03/15
    if len(token) >= 10 and token[4] == "/" and token[7] == "/":
        return token

    # Day-Mon-Year format: starts with 2 digits, then a dash, then letters
    # Example: 15-Mar-2024
    if len(token) >= 11 and token[2] == "-" and token[6] == "-":
        return token

    # Unix epoch: all digits, 9 to 11 characters long
    # Example: 1710512581
    if token.isdigit() and 9 <= len(token) <= 11:
        return token

    return None   # does not look like a timestamp


def parse_json_line(line):
    """
    If a line is JSON (starts with {), try to extract fields from it.
    Returns a dictionary with the log entry, or None if it fails.
    """
    line = line.strip()
    if not line.startswith("{"):
        return None   # not a JSON line

    try:
        obj = json.loads(line)   # parse the JSON

        # Try to get each field — different JSON loggers use different names
        ip     = obj.get("ip") or obj.get("remote_addr") or "unknown"
        method = obj.get("method") or "UNKNOWN"
        path   = obj.get("path") or obj.get("uri") or "unknown"

        # Status code
        raw_status = obj.get("status") or obj.get("status_code")
        status = parse_status_code(str(raw_status)) if raw_status else None

        # Response time — try several common key names
        resp_ms = None
        for key in ["duration_ms", "response_time", "latency", "ms"]:
            if key in obj:
                resp_ms = parse_response_time(str(obj[key]))
                break

        # Return as a simple dictionary
        return {
            "ip":      ip,
            "method":  method.upper(),
            "path":    path,
            "status":  status,
            "resp_ms": resp_ms,
        }

    except Exception:
        return None   # JSON was broken


def parse_normal_line(line):
    """
    Tries to parse a standard log line like:
      2024-03-15T14:23:01Z 192.168.1.42 GET /api/users 200 142ms

    Returns a dictionary with the fields, or None if it can't parse.

    The strategy:
      1. Split the line into words
      2. Find the HTTP METHOD word (GET, POST, etc.)
      3. Everything to the left of METHOD is timestamp + IP
      4. Everything to the right is path, status, response time
    """
    line = line.strip()
    if not line:
        return None

    # Split into individual words
    words = line.split()

    if len(words) < 5:
        return None   # too short to be a valid log line

    # HTTP methods we know about
    known_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

    # Find which word is the HTTP method
    method_position = None
    for i in range(len(words)):
        if words[i].upper() in known_methods:
            method_position = i
            break

    if method_position is None:
        return None   # no HTTP method found — can't parse this line

    # We need at least: [timestamp] [ip] [method] [path] [status]
    # So method must be at position 2 or later
    if method_position < 2:
        return None

    # The word just before the method is the IP address
    ip = words[method_position - 1]

    # Everything before the IP is the timestamp (could be 1 or 2 words)
    # We join them and just store as a string — we won't parse the date deeply
    timestamp_words = words[ : method_position - 1]
    timestamp = " ".join(timestamp_words)

    # The method itself
    method = words[method_position].upper()

    # After the method: path, status, response_time, [maybe more fields]
    rest = words[method_position + 1 :]

    if len(rest) < 2:
        return None   # not enough fields after the method

    path       = rest[0]
    status_raw = rest[1]
    status     = parse_status_code(status_raw)

    # Response time (if present)
    resp_ms = None
    if len(rest) >= 3:
        resp_ms = parse_response_time(rest[2])

    # Return the parsed entry as a simple dictionary
    return {
        "ip":      ip,
        "method":  method,
        "path":    path,
        "status":  status,
        "resp_ms": resp_ms,
    }


def parse_line(line):
    """
    Master function — tries to parse one line.
    Returns (entry, skip_reason):
      - entry is a dict if parsing worked, or None if it failed
      - skip_reason explains why we skipped it (or None if we didn't)
    """
    line_stripped = line.strip()

    # Empty line
    if line_stripped == "":
        return None, "empty line"

    # JSON line — starts with {
    if line_stripped.startswith("{"):
        entry = parse_json_line(line_stripped)
        if entry:
            return entry, None
        else:
            return None, "broken JSON"

    # Normal log line
    entry = parse_normal_line(line_stripped)
    if entry:
        return entry, None
    else:
        return None, "could not parse"


# ================================================================
# STEP 3 — PROCESS ALL LINES
# ================================================================

def process_all_lines(lines):
    """
    Goes through every line in the file.
    Returns:
      - good_entries: list of successfully parsed log dictionaries
      - skip_reasons: dictionary counting why lines were skipped
    """
    good_entries = []
    skip_reasons = {}   # e.g. {"empty line": 45, "could not parse": 12}

    for line in lines:
        entry, reason = parse_line(line)

        if entry is not None:
            good_entries.append(entry)
        else:
            # Count this skip reason
            if reason not in skip_reasons:
                skip_reasons[reason] = 0
            skip_reasons[reason] += 1

    return good_entries, skip_reasons


# ================================================================
# STEP 4 — COUNT THINGS (the analysis)
# ================================================================

def count_status_codes(entries):
    """
    Counts how many times each status code appears.
    Returns a dictionary like: {200: 1500, 404: 230, 500: 45}
    """
    counts = {}
    for entry in entries:
        code = entry["status"]
        if code is not None:
            if code not in counts:
                counts[code] = 0
            counts[code] += 1
    return counts


def count_methods(entries):
    """
    Counts how many times each HTTP method appears.
    Returns a dictionary like: {"GET": 800, "POST": 400}
    """
    counts = {}
    for entry in entries:
        method = entry["method"]
        if method not in counts:
            counts[method] = 0
        counts[method] += 1
    return counts


def count_paths(entries):
    """
    Counts how many requests each URL path got.
    Returns a dictionary like: {"/api/users": 500, "/api/login": 300}
    """
    counts = {}
    for entry in entries:
        path = entry["path"]
        if path not in counts:
            counts[path] = 0
        counts[path] += 1
    return counts


def count_ips(entries):
    """
    Counts how many requests each IP address made.
    """
    counts = {}
    for entry in entries:
        ip = entry["ip"]
        if ip not in counts:
            counts[ip] = 0
        counts[ip] += 1
    return counts


def find_error_paths(entries):
    """
    Counts errors (status 400+) per URL path.
    Helps find which endpoints are causing the most problems.
    """
    counts = {}
    for entry in entries:
        code = entry["status"]
        if code is not None and code >= 400:
            path = entry["path"]
            if path not in counts:
                counts[path] = 0
            counts[path] += 1
    return counts


def get_top_n(dictionary, n):
    """
    Returns the top N items from a dictionary, sorted by value (highest first).
    Example: get_top_n({"a": 5, "b": 10, "c": 3}, 2) → [("b", 10), ("a", 5)]
    """
    # Sort the dictionary by value in descending order
    sorted_items = sorted(dictionary.items(), key=lambda x: x[1], reverse=True)
    return sorted_items[:n]   # return only the first N items


def get_slowest_endpoints(entries, top_n=10):
    """
    Finds the slowest endpoints by average response time.
    Only includes endpoints that have at least 3 requests (to avoid flukes).
    Returns a list of (path, average_ms) tuples.
    """
    # First, collect all response times per path
    path_times = {}
    for entry in entries:
        if entry["resp_ms"] is not None:
            path = entry["path"]
            if path not in path_times:
                path_times[path] = []
            path_times[path].append(entry["resp_ms"])

    # Now calculate the average for each path (only if 3+ requests)
    averages = {}
    for path, times in path_times.items():
        if len(times) >= 3:
            total = sum(times)
            average = total / len(times)
            averages[path] = average

    return get_top_n(averages, top_n)


def get_response_time_stats(entries):
    """
    Calculates simple response time statistics.
    Returns a dictionary with min, max, average, and a rough percentile.
    """
    # Collect all valid response times
    all_times = []
    for entry in entries:
        if entry["resp_ms"] is not None:
            all_times.append(entry["resp_ms"])

    if not all_times:
        return None   # no response time data at all

    all_times.sort()   # sort from smallest to largest

    total   = len(all_times)
    minimum = all_times[0]
    maximum = all_times[-1]
    average = sum(all_times) / total

    # p95 = the value that 95% of requests are faster than
    # We find the index that is 95% of the way through the sorted list
    p95_index = int(total * 0.95)
    p95 = all_times[p95_index]

    return {
        "count":   total,
        "min_ms":  minimum,
        "max_ms":  maximum,
        "avg_ms":  average,
        "p95_ms":  p95,
    }


def count_errors(entries):
    """
    Counts how many requests had error status codes (400 and above).
    """
    error_count = 0
    for entry in entries:
        code = entry["status"]
        if code is not None and code >= 400:
            error_count += 1
    return error_count


# ================================================================
# STEP 5 — PRINT THE REPORT
# ================================================================

def ms_to_readable(ms):
    """
    Converts milliseconds to a readable string.
    Examples: 142.0 → "142ms",  2500.0 → "2.50s"
    """
    if ms is None:
        return "N/A"
    if ms >= 1000:
        return f"{ms/1000:.2f}s"
    return f"{ms:.0f}ms"


def print_report(lines, good_entries, skip_reasons):
    """
    Prints the full analysis report.
    """
    total_lines   = len(lines)
    total_parsed  = len(good_entries)
    total_skipped = total_lines - total_parsed
    top_n         = 10   # how many items to show in each "top" section

    # ---- Calculate everything ----
    status_counts  = count_status_codes(good_entries)
    method_counts  = count_methods(good_entries)
    path_counts    = count_paths(good_entries)
    ip_counts      = count_ips(good_entries)
    error_paths    = find_error_paths(good_entries)
    slowest        = get_slowest_endpoints(good_entries, top_n)
    rt_stats       = get_response_time_stats(good_entries)
    error_count    = count_errors(good_entries)

    if total_parsed > 0:
        error_rate = (error_count / total_parsed) * 100
    else:
        error_rate = 0

    # ---- Print the report ----
    line = "=" * 55

    print()
    print(line)
    print("        SERVER LOG ANALYSIS REPORT")
    print(line)
    print()

    # --- File Summary ---
    print("[ FILE SUMMARY ]")
    print(f"  Total lines in file : {total_lines}")
    print(f"  Lines parsed OK     : {total_parsed}")
    print(f"  Lines skipped       : {total_skipped}")

    if skip_reasons:
        print("  Skipped breakdown:")
        for reason, count in skip_reasons.items():
            print(f"    - {reason}: {count}")
    print()

    # --- Traffic Overview ---
    print("[ TRAFFIC OVERVIEW ]")
    print(f"  Total requests : {total_parsed}")
    print(f"  Total errors   : {error_count}  ({error_rate:.1f}% of requests)")
    print()

    # --- Status Codes ---
    print("[ STATUS CODES ]")
    for code, count in sorted(status_counts.items()):
        # Make a simple bar using # characters
        bar_length = int((count / total_parsed) * 30) if total_parsed > 0 else 0
        bar = "#" * bar_length
        pct = (count / total_parsed * 100) if total_parsed > 0 else 0
        print(f"  {code}  {count:>6}  ({pct:4.1f}%)  {bar}")
    print()

    # --- HTTP Methods ---
    print("[ HTTP METHODS ]")
    for method, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_parsed * 100) if total_parsed > 0 else 0
        print(f"  {method:<8}  {count:>6}  ({pct:.1f}%)")
    print()

    # --- Response Times ---
    print("[ RESPONSE TIMES ]")
    if rt_stats:
        print(f"  Fastest  : {ms_to_readable(rt_stats['min_ms'])}")
        print(f"  Average  : {ms_to_readable(rt_stats['avg_ms'])}")
        print(f"  p95      : {ms_to_readable(rt_stats['p95_ms'])}")
        print(f"  Slowest  : {ms_to_readable(rt_stats['max_ms'])}")
    else:
        print("  No response time data found.")
    print()

    # --- Slowest Endpoints ---
    print(f"[ TOP {top_n} SLOWEST ENDPOINTS ]")
    print("  (average response time, only paths with 3+ requests)")
    if slowest:
        for i, (path, avg_ms) in enumerate(slowest, start=1):
            print(f"  {i:2}.  {path:<40}  {ms_to_readable(avg_ms)}")
    else:
        print("  Not enough data.")
    print()

    # --- Most Requested Paths ---
    print(f"[ TOP {top_n} MOST REQUESTED PATHS ]")
    for i, (path, count) in enumerate(get_top_n(path_counts, top_n), start=1):
        pct = (count / total_parsed * 100) if total_parsed > 0 else 0
        print(f"  {i:2}.  {path:<40}  {count:>6}  ({pct:.1f}%)")
    print()

    # --- Paths With Most Errors ---
    print(f"[ TOP {top_n} PATHS WITH MOST ERRORS ]")
    if error_paths:
        for i, (path, count) in enumerate(get_top_n(error_paths, top_n), start=1):
            print(f"  {i:2}.  {path:<40}  {count:>6} errors")
    else:
        print("  No errors found! Great.")
    print()

    # --- Busiest IP Addresses ---
    print(f"[ TOP {top_n} BUSIEST IP ADDRESSES ]")
    for i, (ip, count) in enumerate(get_top_n(ip_counts, top_n), start=1):
        pct = (count / total_parsed * 100) if total_parsed > 0 else 0
        print(f"  {i:2}.  {ip:<20}  {count:>6}  ({pct:.1f}%)")
    print()

    # --- Simple Alerts (auto warnings) ---
    print("[ ALERTS ]")
    found_alert = False

    if error_rate > 10:
        print(f"  WARNING: High error rate! {error_rate:.1f}% of requests failed.")
        found_alert = True

    if rt_stats and rt_stats["p95_ms"] > 3000:
        print(f"  WARNING: Slow server! 95% of requests take over {ms_to_readable(rt_stats['p95_ms'])}")
        found_alert = True

    if rt_stats and rt_stats["max_ms"] > 10000:
        print(f"  WARNING: Slowest request took {ms_to_readable(rt_stats['max_ms'])} — check for timeouts!")
        found_alert = True

    if total_skipped > total_lines * 0.20:
        pct = (total_skipped / total_lines * 100)
        print(f"  WARNING: {pct:.0f}% of lines were skipped — log file may be very messy.")
        found_alert = True

    if not found_alert:
        print("  All looks normal!")
    print()

    print(line)
    print("  Done! End of report.")
    print(line)
    print()


# ================================================================
# MAIN — this runs when you type: python log_analyzer.py file.log
# ================================================================

def main():
    # Check that the user gave us a filename
    if len(sys.argv) < 2:
        print("Usage: python log_analyzer.py <logfile>")
        print("Example: python log_analyzer.py sample.log")
        sys.exit(1)

    filename = sys.argv[1]   # the first argument after the script name

    # Step 1: Read the file
    print(f"\nReading: {filename}")
    lines = read_file(filename)

    # Step 2 & 3: Parse every line
    print("Parsing log lines...")
    good_entries, skip_reasons = process_all_lines(lines)

    if len(good_entries) == 0:
        print("ERROR: Could not parse ANY lines from this file.")
        print("Check that the file is a valid server log.")
        sys.exit(1)

    print(f"Parsed {len(good_entries)} entries successfully.")
    print("Building report...\n")

    # Step 4 & 5: Count things and print the report
    print_report(lines, good_entries, skip_reasons)


# This means: only run main() if this script is run directly
# (not if it is imported by another script)
if __name__ == "__main__":
    main()
