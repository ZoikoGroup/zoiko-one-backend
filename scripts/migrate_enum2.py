from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    current = db.execute(text("SELECT enum_range(NULL::auditaction)")).scalar()
    print(f"Current auditaction enum: {current}")

    for val in ["ENABLE", "DISABLE", "LOCK", "UNLOCK", "PASSWORD_RESET"]:
        try:
            db.execute(text(f"ALTER TYPE auditaction ADD VALUE IF NOT EXISTS '{val}'"))
            db.commit()
            print(f"  Added '{val}' OK")
        except Exception as e:
            db.rollback()
            print(f"  '{val}': {e}")

    current = db.execute(text("SELECT enum_range(NULL::auditaction)")).scalar()
    print(f"Updated auditaction enum: {current}")
finally:
    db.close()
