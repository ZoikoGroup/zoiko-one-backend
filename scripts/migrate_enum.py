from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    current = db.execute(text("SELECT enum_range(NULL::employeestatus)")).scalar()
    print(f"Current enum: {current}")

    for val in ["DEACTIVATED", "LOCKED", "PASSWORD_RESET_REQUIRED"]:
        try:
            db.execute(text(f"ALTER TYPE employeestatus ADD VALUE IF NOT EXISTS '{val}'"))
            db.commit()
            print(f"  Added '{val}' OK")
        except Exception as e:
            db.rollback()
            print(f"  '{val}': {e}")

    current = db.execute(text("SELECT enum_range(NULL::employeestatus)")).scalar()
    print(f"Updated enum: {current}")
finally:
    db.close()
