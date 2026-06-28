"""
database.py - SQLite operations, file conversions, schema extraction.
"""
import sqlite3
import shutil
import pandas as pd


def csv_to_sqlite(csv_path, db_path, table_name="data"):
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()


def excel_to_sqlite(excel_path, db_path):
    ext = excel_path.rsplit(".", 1)[-1].lower()
    conn = sqlite3.connect(db_path)
    if ext == "xls":
        # Use xlrd for old .xls format
        import xlrd
        wb = xlrd.open_workbook(excel_path)
        for sheet_name in wb.sheet_names():
            ws = wb.sheet_by_name(sheet_name)
            if ws.nrows == 0:
                continue
            headers = [str(ws.cell_value(0, c)) or f"col_{c}" for c in range(ws.ncols)]
            data = []
            for r in range(1, ws.nrows):
                data.append(dict(zip(headers, [ws.cell_value(r, c) for c in range(ws.ncols)])))
            if data:
                safe = sheet_name.replace(" ", "_").replace("-", "_")
                df = pd.DataFrame(data)
                df.to_sql(safe, conn, if_exists="replace", index=False)
    else:
        # Use openpyxl for .xlsx
        import openpyxl
        wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = list(ws.values)
            if not rows:
                continue
            headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
            data = [dict(zip(headers, row)) for row in rows[1:]]
            if data:
                safe = sheet_name.replace(" ", "_").replace("-", "_")
                df = pd.DataFrame(data)
                df.to_sql(safe, conn, if_exists="replace", index=False)
        wb.close()
    conn.close()


def sql_to_sqlite(sql_path, db_path):
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
    conn = sqlite3.connect(db_path)
    conn.executescript(sql)
    conn.commit()
    conn.close()


def duplicate_db(src, dst):
    shutil.copy2(src, dst)


def get_schema(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    schema = {}
    for t in tables:
        cur.execute(f"PRAGMA table_info('{t}')")
        schema[t] = [{"name": c[1], "type": c[2]} for c in cur.fetchall()]
    conn.close()
    return schema


def get_schema_string(db_path):
    schema = get_schema(db_path)
    lines = []
    for table, cols in schema.items():
        col_str = ", ".join(f"{c['name']} {c['type']}" for c in cols)
        lines.append(f"Table: {table} ({col_str})")
    return "\n".join(lines)


def get_preview(db_path, limit=20):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    result = {}
    for t in tables:
        df = pd.read_sql_query(f"SELECT * FROM '{t}' LIMIT {limit}", conn)
        cur.execute(f"SELECT COUNT(*) FROM '{t}'")
        total = cur.fetchone()[0]
        result[t] = {
            "columns": list(df.columns),
            "rows": df.fillna("").values.tolist(),
            "total": total
        }
    conn.close()
    return result


def execute_sql(db_path, sql):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute(sql)
        upper = sql.strip().upper()
        if upper.startswith("SELECT") or upper.startswith("WITH"):
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
            conn.close()
            return {"type": "query", "columns": cols, "rows": [list(r) for r in rows], "rowcount": len(rows)}
        else:
            conn.commit()
            affected = cur.rowcount
            conn.close()
            return {"type": "mutation", "rowcount": affected, "message": f"Done. {affected} row(s) affected."}
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


def sqlite_to_csv(db_path, out_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    if tables:
        df = pd.read_sql_query(f"SELECT * FROM '{tables[0]}'", conn)
        df.to_csv(out_path, index=False)
    conn.close()


def sqlite_to_excel(db_path, out_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for t in tables:
            df = pd.read_sql_query(f"SELECT * FROM '{t}'", conn)
            df.to_excel(writer, sheet_name=t[:31], index=False)
    conn.close()