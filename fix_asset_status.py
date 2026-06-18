from sqlalchemy import text
from app.database import engine
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE assets MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'AVAILABLE'"))
    conn.commit()
    print("[OK] assets.status changed from ENUM to VARCHAR(50)")
