from app.database import SessionLocal
from app.modules.hr.models import Employee, EmployeeStatus
from sqlalchemy import text

db = SessionLocal()
try:
    result = db.execute(
        text("UPDATE employees SET status = 'ACTIVE' WHERE status = 'PASSWORD_RESET_REQUIRED'")
    )
    db.commit()
    print(f"Migrated {result.rowcount} users from PASSWORD_RESET_REQUIRED -> ACTIVE")
finally:
    db.close()
