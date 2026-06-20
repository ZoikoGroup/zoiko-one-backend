from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Fix performance_appraisals - add missing columns
    result = conn.execute(text('SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "performance_appraisals" AND COLUMN_NAME = "salary_hike"'))
    if result.scalar() == 0:
        conn.execute(text('ALTER TABLE performance_appraisals ADD COLUMN salary_hike DECIMAL(10,2) NULL'))
        print('Added salary_hike to performance_appraisals')
    
    result = conn.execute(text('SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "performance_appraisals" AND COLUMN_NAME = "self_score"'))
    if result.scalar() == 0:
        conn.execute(text('ALTER TABLE performance_appraisals ADD COLUMN self_score DECIMAL(5,2) NULL'))
        print('Added self_score to performance_appraisals')
    
    result = conn.execute(text('SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "performance_appraisals" AND COLUMN_NAME = "manager_score"'))
    if result.scalar() == 0:
        conn.execute(text('ALTER TABLE performance_appraisals ADD COLUMN manager_score DECIMAL(5,2) NULL'))
        print('Added manager_score to performance_appraisals')
    
    result = conn.execute(text('SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "performance_appraisals" AND COLUMN_NAME = "final_score"'))
    if result.scalar() == 0:
        conn.execute(text('ALTER TABLE performance_appraisals ADD COLUMN final_score DECIMAL(5,2) NULL'))
        print('Added final_score to performance_appraisals')
    
    result = conn.execute(text('SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "performance_appraisals" AND COLUMN_NAME = "recommendation"'))
    if result.scalar() == 0:
        conn.execute(text('ALTER TABLE performance_appraisals ADD COLUMN recommendation VARCHAR(50) NULL'))
        print('Added recommendation to performance_appraisals')
    
    result = conn.execute(text('SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "performance_appraisals" AND COLUMN_NAME = "comments"'))
    if result.scalar() == 0:
        conn.execute(text('ALTER TABLE performance_appraisals ADD COLUMN comments TEXT NULL'))
        print('Added comments to performance_appraisals')
    
    conn.commit()
print('performance_appraisals fixed')