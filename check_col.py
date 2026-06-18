from sqlalchemy import inspect
from app.database import engine
inspector = inspect(engine)
cols = inspector.get_columns("assets")
for c in cols:
    if c["name"] == "status":
        print(f"status: type={c['type']} nullable={c['nullable']} default={c['default']}")
