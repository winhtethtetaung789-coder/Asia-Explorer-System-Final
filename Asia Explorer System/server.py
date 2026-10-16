import json
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).parent
DATABASE = ROOT / "asia_explorer.db"
SCHEMA = ROOT / "database.sql"


def initialize_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))


def age_counts():
    groups = [("1-17", 1, 17), ("18-25", 18, 25), ("26-40", 26, 40), ("41-60", 41, 60), ("61+", 61, 120)]
    with sqlite3.connect(DATABASE) as connection:
        total_rows = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        counts = []
        for label, minimum, maximum in groups:
            count = connection.execute(
                "SELECT COUNT(*) FROM users WHERE age BETWEEN ? AND ?",
                (minimum, maximum),
            ).fetchone()[0]
            counts.append({"label": label, "min": minimum, "max": maximum, "count": count})
    return {"total": total_rows, "groups": counts}


class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/users/age-counts":
            self.send_json(age_counts())
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/users":
            self.send_error(404)
            return

        try:
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            name = str(payload.get("name", "")).strip()
            age = payload.get("age")
            if not name or len(name) > 80 or not isinstance(age, int) or isinstance(age, bool) or not 1 <= age <= 120:
                raise ValueError("name must be 1-80 characters and age must be an integer from 1 to 120")
            with sqlite3.connect(DATABASE) as connection:
                cursor = connection.execute("INSERT INTO users (name, age) VALUES (?, ?)", (name, age))
                user_id = cursor.lastrowid
                connection.commit()
            self.send_json({"id": user_id, "name": name, "age": age, "ageChart": age_counts()}, 201)
        except (ValueError, json.JSONDecodeError, sqlite3.Error) as error:
            self.send_json({"error": str(error)}, 400)

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    initialize_database()
    server = ThreadingHTTPServer(("127.0.0.1", 8000), RequestHandler)
    print("Asia Explorer running at http://127.0.0.1:8000")
    server.serve_forever()