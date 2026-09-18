# Global Immunisation Explorer

Global Immunisation Explorer is a Flask and SQLite web application created for the COSC3106 Immunisation Project.

The application allows users to explore global vaccination coverage, reported infection cases and changes in immunisation performance across different countries, regions and years.

## Team Members

| Name | Student ID |
| --- | --- |
| Nguyen Tien Thanh | s4187267 |
| Tran Hoang Dong Anh | s4180099 |

## Features

- Level 1A: Dataset overview
- Level 2A: Vaccination explorer
- Level 3A: Vaccination improvement comparison
- Level 1B: Mission, personas and team members
- Level 2B: Infection explorer
- Level 3B: Above-average infection rate analysis

## Technologies

- Python
- Flask
- SQLite
- SQL
- HTML
- CSS
- Jinja

## How to Run

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required package:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python3 app.py
```

Open the website at:

```text
http://127.0.0.1:5001
```

## Database

The included `immunisation-2.db` SQLite database contains the data required by the application. No additional database setup is required.