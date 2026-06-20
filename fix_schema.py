from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Fix attendance_records
    result = conn.execute(text('SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "attendance_records" AND COLUMN_NAME = "total_hours"'))
    if result.scalar() == 0:
        conn.execute(text('ALTER TABLE attendance_records ADD COLUMN total_hours DECIMAL(5,2) NULL'))
        print('Added total_hours to attendance_records')
    
    result = conn.execute(text('SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "attendance_records" AND COLUMN_NAME = "is_deleted"'))
    if result.scalar() == 0:
        conn.execute(text('ALTER TABLE attendance_records ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE'))
        print('Added is_deleted to attendance_records')
    
    conn.commit()
print('attendance_records fixed')