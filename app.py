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

    # Fact 1: number of countries
    country_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM Country
    """).fetchone()["total"]

    # Fact 2: number of antigen types
    antigen_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM Antigen
    """).fetchone()["total"]

    # Fact 3: number of vaccination records
    vaccination_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM Vaccination
    """).fetchone()["total"]

    # Fact 4: data timeframe
    years = conn.execute("""
        SELECT
            MIN(year) AS first_year,
            MAX(year) AS last_year
        FROM Vaccination
    """).fetchone()

    conn.close()

    return render_template(
        "landing.html",
        country_count=country_count,
        antigen_count=antigen_count,
        vaccination_count=vaccination_count,
        first_year=years["first_year"],
        last_year=years["last_year"]
    )


@app.route("/vaccination")
def vaccination():
    return render_template("vaccination.html")


@app.route("/improvement")
def improvement():
    return render_template("improvement.html")


if __name__ == "__main__":
    app.run(debug=True, port = 5001)