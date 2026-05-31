"""
generate_logs.py
----------------
This script creates a fake server log file for testing.
Run it like this:
    python scripts/generate_logs.py
It will create a file called sample.log in the same folder.
"""

import random   # to pick random things
import sys      # to read command line arguments

# -------------------------------------------------------
# Settings — change these if you want
# -------------------------------------------------------
HOW_MANY_LINES = 2000         # how many log lines to create
OUTPUT_FILE    = "sample.log" # name of the file to save


# -------------------------------------------------------
# Lists of things we will randomly pick from
# -------------------------------------------------------

# Common IP addresses in a small office network
IP_ADDRESSES = [
    "192.168.1.1",  "192.168.1.42", "192.168.1.99",
    "10.0.0.1",     "10.0.0.7",     "10.0.0.15",
    "203.0.113.5",  "198.51.100.22"
]

# HTTP methods a browser or app might use
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]

# URL paths on a typical web API
URL_PATHS = [
    "/api/users",
    "/api/users/12",
    "/api/login",
    "/api/logout",
    "/api/products",
    "/api/products/7",
    "/api/orders",
    "/api/health",
    "/static/css/main.css",
    "/static/js/app.js",
    "/favicon.ico",
]

# HTTP status codes — more 200s than errors (realistic)
STATUS_CODES = (
    [200] * 55 +   # 55 chances of 200 OK
    [201] * 10 +   # 10 chances of 201 Created
    [301] * 3  +   # 3 chances of 301 Redirect
    [400] * 5  +   # 5 chances of 400 Bad Request
    [401] * 8  +   # 8 chances of 401 Unauthorized
    [403] * 4  +   # 4 chances of 403 Forbidden
    [404] * 10 +   # 10 chances of 404 Not Found
    [500] * 5      # 5 chances of 500 Server Error
)


# -------------------------------------------------------
# Helper functions
# -------------------------------------------------------

def make_timestamp_format1(year, month, day, hour, minute, second):
    """Format 1: 2024-03-15T14:23:01Z  (most common)"""
    return f"{year}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"

def make_timestamp_format2(year, month, day, hour, minute, second):
    """Format 2: 2024/03/15 14:23:01  (old style)"""
    return f"{year}/{month:02d}/{day:02d} {hour:02d}:{minute:02d}:{second:02d}"

def make_timestamp_format3(day, month_name, year, hour, minute, second):
    """Format 3: 15-Mar-2024 14:23:01  (another old style)"""
    return f"{day:02d}-{month_name}-{year} {hour:02d}:{minute:02d}:{second:02d}"

def make_timestamp_format4(unix_time):
    """Format 4: 1710512581  (unix epoch — just a big number)"""
    return str(unix_time)

def make_response_time_ms(ms):
    """Style 1: 142ms"""
    return f"{ms}ms"

def make_response_time_seconds(ms):
    """Style 2: 0.142s"""
    seconds = ms / 1000.0
    return f"{seconds:.3f}s"

def make_response_time_bare(ms):
    """Style 3: 142  (no unit — ambiguous)"""
    return str(ms)


# -------------------------------------------------------
# Build one normal log line
# -------------------------------------------------------

def make_normal_line(line_number):
    """
    Creates one normal log line.
    A normal line looks like:
      2024-03-15T14:23:01Z 192.168.1.42 GET /api/users 200 142ms
    """
    # Pick random values
    ip      = random.choice(IP_ADDRESSES)
    method  = random.choice(HTTP_METHODS)
    path    = random.choice(URL_PATHS)
    status  = random.choice(STATUS_CODES)
    ms      = random.randint(5, 4000)  # response time between 5ms and 4 seconds

    # Build a timestamp (we increment seconds by line number to make them go forward)
    second = line_number % 60
    minute = (line_number // 60) % 60
    hour   = (line_number // 3600) % 24
    day    = 15
    month  = 3
    year   = 2024
    # Unix epoch base for March 15 2024 00:00:00
    unix_base = 1710460800
    unix_time = unix_base + line_number

    # Pick a timestamp format randomly
    ts_choice = random.randint(1, 4)
    if ts_choice == 1:
        timestamp = make_timestamp_format1(year, month, day, hour, minute, second)
    elif ts_choice == 2:
        timestamp = make_timestamp_format2(year, month, day, hour, minute, second)
    elif ts_choice == 3:
        month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
        timestamp = make_timestamp_format3(day, month_names[month-1], year, hour, minute, second)
    else:
        timestamp = make_timestamp_format4(unix_time)

    # Pick a response time format randomly
    rt_choice = random.randint(1, 3)
    if rt_choice == 1:
        resp_time = make_response_time_ms(ms)
    elif rt_choice == 2:
        resp_time = make_response_time_seconds(ms)
    else:
        resp_time = make_response_time_bare(ms)

    # Put it all together
    line = f"{timestamp} {ip} {method} {path} {status} {resp_time}"

    # Sometimes add an extra field like a user agent (20% of the time)
    if random.random() < 0.20:
        line = line + ' "Mozilla/5.0 (Windows NT 10.0)"'

    return line


# -------------------------------------------------------
# Build one BAD / deviant log line (the messy ones)
# -------------------------------------------------------

def make_bad_line():
    """
    Creates a bad/messy line. About 7% of lines in real logs are like this.
    """
    bad_type = random.randint(1, 6)

    if bad_type == 1:
        return ""  # completely empty line

    elif bad_type == 2:
        return "   "  # just spaces

    elif bad_type == 3:
        # Missing status code — uses a dash instead of a number
        ip   = random.choice(IP_ADDRESSES)
        ms   = random.randint(5, 500)
        return f"2024-03-15T14:23:01Z {ip} GET /api/users - {ms}ms"

    elif bad_type == 4:
        # Stack trace from a crash — totally different format
        return ("ERROR: java.lang.NullPointerException\n"
                "    at Service.process(Service.java:42)")

    elif bad_type == 5:
        # Line got cut off halfway (partial write)
        return "2024-03-15T14:23:01Z 192.168"

    elif bad_type == 6:
        # JSON format line — someone changed the logging library
        import json
        ip   = random.choice(IP_ADDRESSES)
        path = random.choice(URL_PATHS)
        ms   = random.randint(5, 2000)
        data = {
            "timestamp": "2024-03-15T14:23:01Z",
            "ip":        ip,
            "method":    random.choice(HTTP_METHODS),
            "path":      path,
            "status":    random.choice(STATUS_CODES),
            "duration_ms": ms
        }
        return json.dumps(data)

    return ""  # fallback


# -------------------------------------------------------
# Main — write all lines to file
# -------------------------------------------------------

print(f"Creating {HOW_MANY_LINES} log lines...")

all_lines = []

for i in range(HOW_MANY_LINES):
    # About 7% of lines are bad/deviant
    if random.random() < 0.07:
        line = make_bad_line()
    else:
        line = make_normal_line(i)

    all_lines.append(line)

# Save to file
with open(OUTPUT_FILE, "w") as f:
    for line in all_lines:
        f.write(line + "\n")

print(f"Done! Saved to: {OUTPUT_FILE}")
print(f"Go check the file — it has {HOW_MANY_LINES} lines of fake server logs.")
