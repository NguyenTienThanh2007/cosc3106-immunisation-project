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

    selected_antigen = request.args.get("antigen")
    selected_year = request.args.get("year")
    selected_region = request.args.get("region")
    selected_country = request.args.get("country")

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

    results = []
    regional_summary = []
    missing_coverage_count = 0

    if selected_antigen and selected_year:

        # Missing coverage count
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

        # Table 1
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

        # Table 2
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
    conn = get_db_connection()

    # Get user selections
    selected_antigen = request.args.get("antigen")
    start_year = request.args.get("start_year")
    end_year = request.args.get("end_year")
    limit = request.args.get("limit", "10")

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

    # =========================
    # RESULTS
    # =========================

    improvement_results = []
    error_message = None

    if selected_antigen and start_year and end_year:

        try:
            start_year_int = int(start_year)
            end_year_int = int(end_year)
            limit_int = int(limit)

        except ValueError:
            error_message = "Invalid year or result limit."

        else:
            if start_year_int >= end_year_int:
                error_message = "Start year must be earlier than end year."

            elif limit_int not in [5, 10, 20]:
                error_message = "Invalid number of countries selected."

            else:
                query = """
                    SELECT
                        ROW_NUMBER() OVER (
                            ORDER BY
                                (
                                    (
                                        CAST(end_v.doses AS REAL)
                                        / end_p.population * 100
                                    )
                                    -
                                    (
                                        CAST(start_v.doses AS REAL)
                                        / start_p.population * 100
                                    )
                                ) DESC
                        ) AS rank,

                        Country.name AS country_name,

                        ROUND(
                            CAST(start_v.doses AS REAL)
                            / start_p.population * 100,
                            2
                        ) AS start_rate,

                        ROUND(
                            CAST(end_v.doses AS REAL)
                            / end_p.population * 100,
                            2
                        ) AS end_rate,

                        ROUND(
                            (
                                CAST(end_v.doses AS REAL)
                                / end_p.population * 100
                            )
                            -
                            (
                                CAST(start_v.doses AS REAL)
                                / start_p.population * 100
                            ),
                            2
                        ) AS improvement

                    FROM Vaccination AS start_v

                    JOIN Vaccination AS end_v
                        ON start_v.country = end_v.country
                        AND start_v.antigen = end_v.antigen

                    JOIN Country
                        ON start_v.country = Country.CountryID

                    JOIN CountryPopulation AS start_p
                        ON start_v.country = start_p.country
                        AND start_v.year = start_p.year

                    JOIN CountryPopulation AS end_p
                        ON end_v.country = end_p.country
                        AND end_v.year = end_p.year

                    WHERE start_v.antigen = ?
                      AND end_v.antigen = ?
                      AND start_v.year = ?
                      AND end_v.year = ?

                      -- Population must be valid
                      AND start_p.population > 0
                      AND end_p.population > 0

                      -- Both years must contain dose data
                      AND TRIM(CAST(start_v.doses AS TEXT)) != ''
                      AND TRIM(CAST(end_v.doses AS TEXT)) != ''

                      -- Only countries with a positive improvement
                      AND (
                            (
                                CAST(end_v.doses AS REAL)
                                / end_p.population * 100
                            )
                            -
                            (
                                CAST(start_v.doses AS REAL)
                                / start_p.population * 100
                            )
                          ) > 0

                    ORDER BY improvement DESC
                    LIMIT ?
                """

                improvement_results = conn.execute(
                    query,
                    [
                        selected_antigen,
                        selected_antigen,
                        start_year_int,
                        end_year_int,
                        limit_int
                    ]
                ).fetchall()

    conn.close()

    return render_template(
        "improvement.html",
        antigens=antigens,
        years=years,
        improvement_results=improvement_results,
        selected_antigen=selected_antigen,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
        error_message=error_message
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)