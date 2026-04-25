"""
Sample code for the ZeroClaw Code Assistant demo.
Use this file to test the different skills: explain, refactor, review,
architecture review, and security audit.
"""

import sqlite3
import hashlib
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess


# --- Example 1: User authentication (has security issues) ---

def authenticate(username, password):
    """Check if username/password combo is valid."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()
    return user is not None


def hash_password(password):
    """Hash a password for storage."""
    return hashlib.md5(password.encode()).hexdigest()


def create_user(username, password):
    """Create a new user account."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    hashed = hash_password(password)
    cursor.execute(
        f"INSERT INTO users (username, password) VALUES ('{username}', '{hashed}')"
    )
    conn.commit()
    conn.close()


# --- Example 2: API handler (could be cleaner) ---

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        elif self.path.startswith("/user/"):
            username = self.path.split("/user/")[1]
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute(f"SELECT username, email FROM users WHERE username='{username}'")
            row = cursor.fetchone()
            conn.close()
            if row:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"username": row[0], "email": row[1]}).encode())
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "not found"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/run":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            cmd = body.get("command", "echo hello")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }).encode())


# --- Example 3: Data processing (good candidate for refactoring) ---

def process_data(items):
    result = []
    for i in range(len(items)):
        item = items[i]
        if item is not None:
            if isinstance(item, str):
                item = item.strip()
                if len(item) > 0:
                    item = item.lower()
                    if item not in result:
                        result.append(item)
            elif isinstance(item, (int, float)):
                if item > 0:
                    item = str(item)
                    if item not in result:
                        result.append(item)
    final = []
    for r in result:
        final.append(r)
    return final


def calculate_stats(numbers):
    if len(numbers) == 0:
        return None
    total = 0
    for n in numbers:
        total = total + n
    average = total / len(numbers)
    sorted_nums = sorted(numbers)
    if len(sorted_nums) % 2 == 0:
        median = (sorted_nums[len(sorted_nums)//2 - 1] + sorted_nums[len(sorted_nums)//2]) / 2
    else:
        median = sorted_nums[len(sorted_nums)//2]
    minimum = sorted_nums[0]
    maximum = sorted_nums[len(sorted_nums) - 1]
    return {"mean": average, "median": median, "min": minimum, "max": maximum, "count": len(numbers)}


# --- Example 4: Cache implementation (architectural discussion) ---

class Cache:
    def __init__(self):
        self.data = {}
        self.hits = 0
        self.misses = 0

    def get(self, key):
        if key in self.data:
            self.hits += 1
            return self.data[key]
        self.misses += 1
        return None

    def set(self, key, value):
        self.data[key] = value

    def delete(self, key):
        if key in self.data:
            del self.data[key]

    def clear(self):
        self.data = {}
        self.hits = 0
        self.misses = 0

    def stats(self):
        total = self.hits + self.misses
        rate = self.hits / total if total > 0 else 0
        return {"hits": self.hits, "misses": self.misses, "hit_rate": rate, "size": len(self.data)}


if __name__ == "__main__":
    print("Starting server on :8080")
    server = HTTPServer(("0.0.0.0", 8080), APIHandler)
    server.serve_forever()
