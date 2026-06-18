"""Check actual MySQL ENUM values for all enum columns."""
from sqlalchemy import inspect, text
from app.database import engine

with engine.connect() as conn:
    inspector = inspect(engine)
    tables_with_enums = []
    
    for table_name in inspector.get_table_names():
        for col in inspector.get_columns(table_name):
            t_str = str(col["type"])
            if "ENUM" in t_str:
                tables_with_enums.append((table_name, col["name"], t_str))
                # Get SHOW COLUMNS to see actual ENUM values
                row = conn.execute(text(f"SHOW COLUMNS FROM {table_name} WHERE Field = '{col['name']}'")).fetchone()
                if row:
                    print(f"{table_name}.{col['name']}: {row.Type}")

    if not tables_with_enums:
        print("No ENUM columns found in any table")
