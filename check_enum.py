"""Check MySQL enum definition for employees.role and fix if needed."""
from app.database import engine
from sqlalchemy import inspect, text

inspector = inspect(engine)
cols = inspector.get_columns("employees")
for c in cols:
    if c["name"] == "role":
        print(f"Column: {c}")
        print(f"Type: {c['type']}")

# Show enum values
with engine.connect() as conn:
    result = conn.execute(text("SHOW COLUMNS FROM employees LIKE 'role'"))
    for row in result:
        print(f"SHOW COLUMNS: {row}")
        # Extract ENUM values from the Type field
        type_str = str(row[1])
        print(f"Type string: {type_str}")
