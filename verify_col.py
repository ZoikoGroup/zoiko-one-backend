from sqlalchemy import inspect
from app.database import engine
inspector = inspect(engine)
for c in inspector.get_columns("assets"):
    if c["name"] == "status":
        print(f"status: type={c['type']} nullable={c['nullable']}")
