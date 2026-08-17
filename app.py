from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

DATABASE = "immunisation-2.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def landing():
    conn = get_db_connection()

    tables = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """).fetchall()

    conn.close()

    return render_template(
        "landing.html",
        tables=tables
    )


@app.route("/vaccination")
def vaccination():
    return render_template("vaccination.html")


@app.route("/improvement")
def improvement():
    return render_template("improvement.html")


if __name__ == "__main__":
    app.run(debug=True)