from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

DATABASE = "immunisation-2.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# LEVEL 1A - LANDING PAGE
# =========================

@app.route("/")
def landing():
    conn = get_db_connection()

    country_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM Country
    """).fetchone()["total"]

    antigen_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM Antigen
    """).fetchone()["total"]

    vaccination_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM Vaccination
    """).fetchone()["total"]

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


# =========================
# LEVEL 2A - VACCINATION
# =========================

@app.route("/vaccination")
def vaccination():
    conn = get_db_connection()

    # User selections
    selected_antigen = request.args.get("antigen")
    selected_year = request.args.get("year")
    selected_region = request.args.get("region")
    selected_country = request.args.get("country")


    # =========================
    # DROPDOWN DATA
    # =========================

    antigens = conn.execute("""
        SELECT
            AntigenID,
            name
        FROM Antigen
        ORDER BY AntigenID
    """).fetchall()

    years = conn.execute("""
        SELECT DISTINCT year
        FROM Vaccination
        ORDER BY year DESC
    """).fetchall()

    regions = conn.execute("""
        SELECT
            RegionID,
            region
        FROM Region
        ORDER BY region
    """).fetchall()

    countries = conn.execute("""
        SELECT
            CountryID,
            name
        FROM Country
        ORDER BY name
    """).fetchall()


    # =========================
    # RESULTS
    # =========================

    results = []
    regional_summary = []
    missing_coverage_count = 0


    if selected_antigen and selected_year:

        # =====================================
        # DATA ANOMALY - MISSING COVERAGE
        # =====================================

        missing_query = """
            SELECT COUNT(*) AS total

            FROM Vaccination

            JOIN Country
                ON Vaccination.country = Country.CountryID

            JOIN Region
                ON Country.region = Region.RegionID

            WHERE Vaccination.antigen = ?
              AND Vaccination.year = ?
              AND TRIM(CAST(Vaccination.coverage AS TEXT)) = ''
        """

        missing_params = [
            selected_antigen,
            selected_year
        ]

        if selected_region:
            missing_query += """
                AND Region.RegionID = ?
            """
            missing_params.append(selected_region)

        if selected_country:
            missing_query += """
                AND Country.CountryID = ?
            """
            missing_params.append(selected_country)

        missing_coverage_count = conn.execute(
            missing_query,
            missing_params
        ).fetchone()["total"]


        # =====================================
        # TABLE 1 - COUNTRY RESULTS
        # =====================================

        query = """
            SELECT
                Vaccination.antigen,
                Vaccination.year,
                Country.name AS country_name,
                Region.region AS region_name,
                Vaccination.coverage

            FROM Vaccination

            JOIN Country
                ON Vaccination.country = Country.CountryID

            JOIN Region
                ON Country.region = Region.RegionID

            WHERE Vaccination.antigen = ?
              AND Vaccination.year = ?
              AND TRIM(CAST(Vaccination.coverage AS TEXT)) != ''
              AND CAST(Vaccination.coverage AS REAL) >= 90
        """

        params = [
            selected_antigen,
            selected_year
        ]

        if selected_region:
            query += """
                AND Region.RegionID = ?
            """
            params.append(selected_region)

        if selected_country:
            query += """
                AND Country.CountryID = ?
            """
            params.append(selected_country)

        query += """
            ORDER BY CAST(Vaccination.coverage AS REAL) DESC
        """

        results = conn.execute(
            query,
            params
        ).fetchall()


        # =====================================
        # TABLE 2 - REGIONAL SUMMARY
        # =====================================

        summary_query = """
            SELECT
                Vaccination.antigen,
                Vaccination.year,
                Region.region AS region_name,

                ROUND(
                    AVG(CAST(Vaccination.coverage AS REAL)),
                    2
                ) AS average_coverage,

                COUNT(
                    DISTINCT CASE
                        WHEN CAST(Vaccination.coverage AS REAL) >= 90
                        THEN Country.CountryID
                    END
                ) AS countries_above_90

            FROM Vaccination

            JOIN Country
                ON Vaccination.country = Country.CountryID

            JOIN Region
                ON Country.region = Region.RegionID

            WHERE Vaccination.antigen = ?
              AND Vaccination.year = ?
              AND TRIM(CAST(Vaccination.coverage AS TEXT)) != ''
        """

        summary_params = [
            selected_antigen,
            selected_year
        ]

        if selected_region:
            summary_query += """
                AND Region.RegionID = ?
            """
            summary_params.append(selected_region)

        if selected_country:
            summary_query += """
                AND Country.CountryID = ?
            """
            summary_params.append(selected_country)

        summary_query += """
            GROUP BY
                Vaccination.antigen,
                Vaccination.year,
                Region.RegionID,
                Region.region

            ORDER BY average_coverage DESC
        """

        regional_summary = conn.execute(
            summary_query,
            summary_params
        ).fetchall()


    conn.close()


    return render_template(
        "vaccination.html",
        antigens=antigens,
        years=years,
        regions=regions,
        countries=countries,
        results=results,
        regional_summary=regional_summary,
        missing_coverage_count=missing_coverage_count,
        selected_antigen=selected_antigen,
        selected_year=selected_year,
        selected_region=selected_region,
        selected_country=selected_country
    )


# =========================
# LEVEL 3A - IMPROVEMENT
# =========================

@app.route("/improvement")
def improvement():
    return render_template("improvement.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)