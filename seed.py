from datetime import date

from passlib.context import CryptContext
from sqlalchemy import func

from app.database import engine, SessionLocal, Base
from app.modules.hr.models import (
    Department, Employee, EmploymentType, EmployeeStatus, UserRole, Gender
)

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

    db = SessionLocal()
    try:
        existing = db.query(Employee).filter(Employee.email == "admin@zoiko.com").first()
        if existing:
            print(f"Admin already exists (id={existing.id}). Skipping.")
            return

        dept = Department(name="Management", code="MGMT", description="Company management")
        db.add(dept)
        db.commit()
        db.refresh(dept)

        max_code = db.query(func.max(Employee.employee_code)).scalar()
        next_num = 1
        if max_code:
            next_num = int(max_code.split("-")[1]) + 1
        emp_code = f"ZK-{next_num:04d}"

        admin = Employee(
            email="admin@zoiko.com",
            hashed_password=bcrypt_context.hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
            first_name="System",
            last_name="Admin",
            phone="0000000000",
            date_of_birth=date(1990, 1, 1),
            gender=Gender.MALE,
            address="Head Office",
            employee_code=emp_code,
            job_title="System Administrator",
            employment_type=EmploymentType.FULL_TIME,
            status=EmployeeStatus.ACTIVE,
            date_of_joining=date(2024, 1, 1),
            department_id=dept.id,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Admin created! Email: admin@zoiko.com / Password: admin123")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
