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


# =========================
# LEVEL 1B - MISSION STATEMENT
# =========================

@app.route("/mission")
def mission():
    conn = get_db_connection()

    personas = conn.execute("""
        SELECT
            PersonaID,
            persona_name,
            role,
            description,
            goals
        FROM Persona
        ORDER BY PersonaID
    """).fetchall()

    team_members = conn.execute("""
        SELECT
            TeamMemberID,
            full_name,
            student_number
        FROM TeamMember
        ORDER BY TeamMemberID
    """).fetchall()

    conn.close()

    return render_template(
        "mission.html",
        personas=personas,
        team_members=team_members
    )


# =========================
# LEVEL 2B - INFECTION EXPLORER
# =========================

# Whitelist of columns that Table 1 may be sorted by, so the user-selected sort criterion can never be used to inject SQL.
INFECTION_SORT_COLUMNS = {
    "country": "country_name",
    "rate": "cases_per_100k"
}


@app.route("/infections")
def infections():
    conn = get_db_connection()

    selected_economy = request.args.get("economy")
    selected_infection = request.args.get("infection")
    selected_year = request.args.get("year")

    sort_by = request.args.get("sort_by", "rate")
    sort_dir = request.args.get("sort_dir", "desc")

    if sort_by not in INFECTION_SORT_COLUMNS:
        sort_by = "rate"

    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"

    # The link a user clicks next on each header - toggles the direction if that column is already active, otherwise starts fresh.
    country_sort_next = "desc" if (sort_by == "country" and sort_dir == "asc") else "asc"
    rate_sort_next = "asc" if (sort_by == "rate" and sort_dir == "desc") else "desc"

    economies = conn.execute("""
        SELECT
            economyID,
            phase
        FROM Economy
        ORDER BY economyID
    """).fetchall()

    infection_types = conn.execute("""
        SELECT
            id,
            description
        FROM Infection_Type
        ORDER BY description
    """).fetchall()

    years = conn.execute("""
        SELECT DISTINCT year
        FROM InfectionData
        ORDER BY year DESC
    """).fetchall()

    country_results = []
    phase_summary = []
    missing_data_count = 0

    if selected_economy and selected_infection and selected_year:

        # Missing / unusable data count for the selected filters
        missing_query = """
            SELECT COUNT(*) AS total

            FROM InfectionData

            JOIN Country
                ON InfectionData.country = Country.CountryID

            LEFT JOIN CountryPopulation
                ON InfectionData.country = CountryPopulation.country
                AND InfectionData.year = CountryPopulation.year

            WHERE InfectionData.inf_type = ?
              AND InfectionData.year = ?
              AND Country.economy = ?
              AND (
                    InfectionData.cases IS NULL
                    OR TRIM(CAST(InfectionData.cases AS TEXT)) = ''
                    OR CountryPopulation.population IS NULL
                    OR CountryPopulation.population <= 0
                  )
        """

        missing_data_count = conn.execute(
            missing_query,
            [selected_infection, selected_year, selected_economy]
        ).fetchone()["total"]

        # Table 1: country-level infection rate for the selected economic status, infection type and year.
        order_column = INFECTION_SORT_COLUMNS[sort_by]
        order_clause = f"{order_column} {sort_dir.upper()}"

        country_query = f"""
            SELECT
                Infection_Type.description AS infection_name,
                Country.name AS country_name,
                Economy.phase AS economic_phase,
                InfectionData.year,

                ROUND(
                    CAST(InfectionData.cases AS REAL)
                    / CountryPopulation.population * 100000,
                    2
                ) AS cases_per_100k

            FROM InfectionData

            JOIN Country
                ON InfectionData.country = Country.CountryID

            JOIN Economy
                ON Country.economy = Economy.economyID

            JOIN Infection_Type
                ON InfectionData.inf_type = Infection_Type.id

            JOIN CountryPopulation
                ON InfectionData.country = CountryPopulation.country
                AND InfectionData.year = CountryPopulation.year

            WHERE InfectionData.inf_type = ?
              AND InfectionData.year = ?
              AND Country.economy = ?
              AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
              AND CountryPopulation.population > 0

            ORDER BY {order_clause}
        """

        country_results = conn.execute(
            country_query,
            [selected_infection, selected_year, selected_economy]
        ).fetchall()

        # Table 2: combines Country + Economy + InfectionData to total
        # cases for every economic phase (not just the one selected above), so the user can see the full picture in one place.
        phase_query = """
            SELECT
                Infection_Type.description AS infection_name,
                Economy.phase AS economic_phase,
                InfectionData.year,
                SUM(InfectionData.cases) AS total_cases

            FROM InfectionData

            JOIN Country
                ON InfectionData.country = Country.CountryID

            JOIN Economy
                ON Country.economy = Economy.economyID

            JOIN Infection_Type
                ON InfectionData.inf_type = Infection_Type.id

            WHERE InfectionData.inf_type = ?
              AND InfectionData.year = ?
              AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''

            GROUP BY
                Economy.economyID,
                Economy.phase,
                InfectionData.year,
                Infection_Type.description

            ORDER BY Economy.economyID ASC
        """

        phase_summary = conn.execute(
            phase_query,
            [selected_infection, selected_year]
        ).fetchall()

    conn.close()

    return render_template(
        "infections.html",
        economies=economies,
        infection_types=infection_types,
        years=years,
        country_results=country_results,
        phase_summary=phase_summary,
        missing_data_count=missing_data_count,
        selected_economy=selected_economy,
        selected_infection=selected_infection,
        selected_year=selected_year,
        sort_by=sort_by,
        sort_dir=sort_dir,
        country_sort_next=country_sort_next,
        rate_sort_next=rate_sort_next
    )


# =========================
# LEVEL 3B - ABOVE-AVERAGE INFECTION RATE
# =========================

# Whitelist of sort options for the ranked country list, so the user-selected sort criterion can never be used to inject SQL.
INFECTION_RATE_SORT = {
    "rate_desc": "rate_per_100k DESC",
    "rate_asc": "rate_per_100k ASC",
    "country": "country_name ASC"
}


@app.route("/infection-rate")
def infection_rate():
    conn = get_db_connection()

    selected_infection = request.args.get("infection")
    selected_year = request.args.get("year")
    sort_option = request.args.get("sort", "rate_desc")

    if sort_option not in INFECTION_RATE_SORT:
        sort_option = "rate_desc"

    infection_types = conn.execute("""
        SELECT
            id,
            description
        FROM Infection_Type
        ORDER BY description
    """).fetchall()

    years = conn.execute("""
        SELECT DISTINCT year
        FROM InfectionData
        ORDER BY year DESC
    """).fetchall()

    infection_name = None
    global_rate = None
    above_average_countries = []

    if selected_infection and selected_year:

        infection_row = conn.execute("""
            SELECT description
            FROM Infection_Type
            WHERE id = ?
        """, [selected_infection]).fetchone()

        infection_name = infection_row["description"] if infection_row else selected_infection

        # Global reported infection rate per 100,000 people, worldwide, for the selected infection type and year.
        global_query = """
            SELECT
                ROUND(
                    SUM(InfectionData.cases) * 1.0
                    / SUM(CountryPopulation.population) * 100000,
                    2
                ) AS global_rate

            FROM InfectionData

            JOIN CountryPopulation
                ON InfectionData.country = CountryPopulation.country
                AND InfectionData.year = CountryPopulation.year

            WHERE InfectionData.inf_type = ?
              AND InfectionData.year = ?
              AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
              AND CountryPopulation.population > 0
        """

        global_row = conn.execute(
            global_query,
            [selected_infection, selected_year]
        ).fetchone()

        global_rate = global_row["global_rate"] if global_row else None

        if global_rate is not None:

            order_clause = INFECTION_RATE_SORT[sort_option]

            # A single query: the "global_stats" CTE calculates the
            # worldwide rate once, then every country's rate is compared against it in the same JOIN - no Python post-processing needed.
            rate_query = f"""
                WITH global_stats AS (
                    SELECT
                        SUM(InfectionData.cases) * 1.0
                        / SUM(CountryPopulation.population) * 100000
                        AS global_rate

                    FROM InfectionData

                    JOIN CountryPopulation
                        ON InfectionData.country = CountryPopulation.country
                        AND InfectionData.year = CountryPopulation.year

                    WHERE InfectionData.inf_type = ?
                      AND InfectionData.year = ?
                      AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
                      AND CountryPopulation.population > 0
                )

                SELECT
                    Country.name AS country_name,

                    ROUND(
                        CAST(InfectionData.cases AS REAL)
                        / CountryPopulation.population * 100000,
                        2
                    ) AS rate_per_100k,

                    ROUND(
                        (
                            CAST(InfectionData.cases AS REAL)
                            / CountryPopulation.population * 100000
                        )
                        - global_stats.global_rate,
                        2
                    ) AS rate_above_global

                FROM InfectionData

                JOIN Country
                    ON InfectionData.country = Country.CountryID

                JOIN CountryPopulation
                    ON InfectionData.country = CountryPopulation.country
                    AND InfectionData.year = CountryPopulation.year

                JOIN global_stats

                WHERE InfectionData.inf_type = ?
                  AND InfectionData.year = ?
                  AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
                  AND CountryPopulation.population > 0
                  AND (
                        CAST(InfectionData.cases AS REAL)
                        / CountryPopulation.population * 100000
                      ) > global_stats.global_rate

                ORDER BY {order_clause}
            """

            above_average_countries = conn.execute(
                rate_query,
                [
                    selected_infection,
                    selected_year,
                    selected_infection,
                    selected_year
                ]
            ).fetchall()

    conn.close()

    return render_template(
        "infection_rate.html",
        infection_types=infection_types,
        years=years,
        infection_name=infection_name,
        global_rate=global_rate,
        above_average_countries=above_average_countries,
        selected_infection=selected_infection,
        selected_year=selected_year,
        sort_option=sort_option
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)