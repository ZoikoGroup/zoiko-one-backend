"""
Fix ENUM/VARCHAR mismatch between MySQL columns and SQLAlchemy 2.0 behavior.
SQLAlchemy 2.0 stores enum NAMES (uppercase), but older versions stored VALUES (lowercase).
Fix: change all ENUM columns to VARCHAR to accept any string.
"""

from sqlalchemy import inspect, text
from app.database import engine

# Tables and columns that are ENUM in MySQL but need to be VARCHAR
# to match SQLAlchemy 2.0 enum storage behavior
fixes = {}

# Assets module
fixes["assets"] = ["status", "condition"]
fixes["asset_maintenance_requests"] = ["priority", "status"]
fixes["asset_requests"] = ["priority", "status"]

# Employee/HR
fixes["employees"] = ["role", "gender", "employment_type", "status"]

# Attendance, Leave, etc.
fixes["attendance_records"] = ["status"]
fixes["leave_requests"] = ["leave_type", "status"]
fixes["compliance_records"] = ["status"]
fixes["engagement_surveys"] = []
fixes["ess_requests"] = ["status"]
fixes["onboarding_records"] = ["status"]
fixes["performance_reviews"] = ["status"]
fixes["recruitment_candidates"] = ["status"]
fixes["travel_requests"] = ["status"]

# Skip learning tables (they use String columns, not ENUMs)


def get_mysql_type(col_info):
    """Get the MySQL column type as a string."""
    t = col_info["type"]
    t_str = str(t)
    if t_str.startswith("ENUM"):
        return "ENUM"
    return t_str


with engine.connect() as conn:
    inspector = inspect(engine)

    for table_name in sorted(fixes.keys()):
        cols_to_fix = fixes[table_name]
        if not cols_to_fix:
            continue

        existing_cols = {c["name"]: c for c in inspector.get_columns(table_name)}

        for col_name in cols_to_fix:
            if col_name not in existing_cols:
                print(f"  [--] {table_name}.{col_name} not found, skipping")
                continue

            col_info = existing_cols[col_name]
            mysql_type = get_mysql_type(col_info)

            if mysql_type == "ENUM":
                # Get the maximum length from the enum values
                # Convert ENUM to VARCHAR
                conn.execute(text(
                    f"ALTER TABLE {table_name} "
                    f"MODIFY COLUMN `{col_name}` VARCHAR(50) "
                    f"{'NOT NULL' if not col_info['nullable'] else 'NULL'}"
                ))
                print(f"  [OK] {table_name}.{col_name}: ENUM -> VARCHAR(50)")
            else:
                print(f"  [--] {table_name}.{col_name}: already {mysql_type}, skipping")

    print("=" * 60)
    print("[OK] All ENUM columns converted to VARCHAR")
    print("=" * 60)
