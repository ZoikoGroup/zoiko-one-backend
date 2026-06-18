from sqlalchemy import inspect
from app.database import engine
inspector = inspect(engine)
for table in sorted(inspector.get_table_names()):
    for fk in inspector.get_foreign_keys(table):
        if fk["referred_table"] == "learning_courses":
            print(f"{table}.{fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']} (FK: {fk['name']})")
