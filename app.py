"""
app.py - Smart Database Assistant
Flask app serving both frontend (HTML) and backend (API).
Run with: python3 app.py
"""

import os
import uuid
import shutil
import tempfile
import glob
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from database import (
    csv_to_sqlite, excel_to_sqlite, sql_to_sqlite, duplicate_db,
    get_schema, get_schema_string, get_preview, execute_sql,
    sqlite_to_csv, sqlite_to_excel
)
from ai import nl_to_sql, fix_sql
from validator import validate

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
WORKING_DIR = os.path.join(BASE_DIR, "working_db")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(WORKING_DIR, exist_ok=True)

ALLOWED_EXT = {"csv", "xlsx", "xls", "db", "sqlite", "sql"}

# In-memory stores
sessions = {}       # session_id -> {master_db, working_db, filename}
histories = {}      # session_id -> list of messages


# ─── Pages ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─── Upload ───────────────────────────────────────────────────────────────────

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected."}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXT)}"}), 400

    session_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)

    # Save original
    orig_path = os.path.join(UPLOAD_DIR, f"{session_id}_original.{ext}")
    file.save(orig_path)

    # Convert to SQLite master
    master_path = os.path.join(WORKING_DIR, f"{session_id}_master.db")
    working_path = os.path.join(WORKING_DIR, f"{session_id}_working.db")

    try:
        table_name = Path(filename).stem.replace(" ", "_").replace("-", "_") or "data"
        if ext == "csv":
            csv_to_sqlite(orig_path, master_path, table_name)
        elif ext in ("xlsx", "xls"):
            excel_to_sqlite(orig_path, master_path)
        elif ext in ("db", "sqlite"):
            shutil.copy2(orig_path, master_path)
        elif ext == "sql":
            sql_to_sqlite(orig_path, master_path)

        duplicate_db(master_path, working_path)

        sessions[session_id] = {
            "master": master_path,
            "working": working_path,
            "filename": filename,
        }
        histories[session_id] = []

        schema = get_schema(working_path)
        preview = get_preview(working_path)

        return jsonify({
            "session_id": session_id,
            "filename": filename,
            "schema": schema,
            "preview": preview,
        })

    except Exception as e:
        for p in [orig_path, master_path, working_path]:
            if os.path.exists(p):
                os.remove(p)
        return jsonify({"error": f"Failed to process file: {str(e)}"}), 500


# ─── Chat ─────────────────────────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    session_id = data.get("session_id", "")
    message = data.get("message", "").strip()

    if not session_id or session_id not in sessions:
        return jsonify({"error": "Session not found. Please re-upload your file."}), 400
    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    working_path = sessions[session_id]["working"]
    schema_str = get_schema_string(working_path)
    history = histories.get(session_id, [])

    # Ask AI
    ai_result = nl_to_sql(message, schema_str, history)
    if ai_result["error"]:
        return jsonify({"error": ai_result["error"], "sql": None, "result": None})

    sql = ai_result["sql"]

    # Validate
    ok, err = validate(sql)
    if not ok:
        fix = fix_sql(sql, err, schema_str)
        if fix["sql"]:
            ok2, _ = validate(fix["sql"])
            if ok2:
                sql = fix["sql"]
            else:
                return jsonify({"error": err, "sql": sql, "result": None})
        else:
            return jsonify({"error": err, "sql": sql, "result": None})

    # Execute
    try:
        result = execute_sql(working_path, sql)
    except Exception as e:
        # Try auto-fix
        fix = fix_sql(sql, str(e), schema_str)
        if fix["sql"]:
            ok2, _ = validate(fix["sql"])
            if ok2:
                try:
                    result = execute_sql(working_path, fix["sql"])
                    sql = fix["sql"]
                except Exception as e2:
                    return jsonify({"error": str(e2), "sql": sql, "result": None})
            else:
                return jsonify({"error": str(e), "sql": sql, "result": None})
        else:
            return jsonify({"error": str(e), "sql": sql, "result": None})

    # Update history
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": f"SQL: {sql}"})
    histories[session_id] = history[-20:]

    # Refresh preview after mutations
    updated_preview = None
    if result["type"] == "mutation":
        updated_preview = get_preview(working_path)

    return jsonify({
        "sql": sql,
        "result": result,
        "updated_preview": updated_preview,
    })


# ─── Preview ──────────────────────────────────────────────────────────────────

@app.route("/preview")
def preview():
    session_id = request.args.get("session_id", "")
    if not session_id or session_id not in sessions:
        return jsonify({"error": "Session not found."}), 400
    data = get_preview(sessions[session_id]["working"])
    schema = get_schema(sessions[session_id]["working"])
    return jsonify({"preview": data, "schema": schema})


# ─── Download ─────────────────────────────────────────────────────────────────

@app.route("/download")
def download():
    session_id = request.args.get("session_id", "")
    fmt = request.args.get("format", "sqlite")

    if not session_id or session_id not in sessions:
        return jsonify({"error": "Session not found."}), 400

    working_path = sessions[session_id]["working"]
    base_name = Path(sessions[session_id]["filename"]).stem

    if fmt == "sqlite":
        return send_file(working_path, as_attachment=True, download_name=f"{base_name}_modified.db")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{fmt}")
    tmp.close()

    try:
        if fmt == "csv":
            sqlite_to_csv(working_path, tmp.name)
            return send_file(tmp.name, as_attachment=True, download_name=f"{base_name}_modified.csv",
                             mimetype="text/csv")
        elif fmt == "xlsx":
            sqlite_to_excel(working_path, tmp.name)
            return send_file(tmp.name, as_attachment=True, download_name=f"{base_name}_modified.xlsx",
                             mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            return jsonify({"error": "Invalid format."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Reset ────────────────────────────────────────────────────────────────────

@app.route("/reset", methods=["POST"])
def reset():
    data = request.get_json()
    session_id = data.get("session_id", "")

    if not session_id or session_id not in sessions:
        return jsonify({"error": "Session not found."}), 400

    sess = sessions[session_id]
    duplicate_db(sess["master"], sess["working"])
    histories[session_id] = []

    preview = get_preview(sess["working"])
    schema = get_schema(sess["working"])
    return jsonify({"message": "Reset to original data.", "preview": preview, "schema": schema})


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🗄️  Smart Database Assistant running at http://localhost:{port}\n")
    app.run(debug=False, port=port, use_reloader=False)