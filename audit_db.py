"""Run workforce seed and audit results with fresh sessions."""
import sys
from app.database import engine, SessionLocal, Base
from sqlalchemy import inspect, text

print("=" * 60)
print("WORKFORCE PLANNING DATA AUDIT")
print("=" * 60)

# Check tables exist
inspector = inspect(engine)
wf_tables = [t for t in inspector.get_table_names() if t.startswith("wf_")]
print(f"\nWF tables ({len(wf_tables)}): {wf_tables}")

# Pre-seed count
db = SessionLocal()
try:
    for t in wf_tables:
        count = db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"  PRE-SEED {t}: {count} rows")
finally:
    db.close()

from app.main import _seed_workforce
print("\n--- Running _seed_workforce() ---")
_seed_workforce()
print("--- Seed completed ---\n")

# Fresh session to check post-seed
db = SessionLocal()
try:
    for t in wf_tables:
        count = db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"  POST-SEED {t}: {count} rows")
    
    from app.modules.hr.models import WfPlan, WfHeadcount, WfSuccession, WfReport, Department, Organization
    
    org = db.query(Organization).first()
    print(f"\nOrganization: {org.id} {org.name}")
    
    depts = db.query(Department).all()
    print(f"Departments ({len(depts)}):")
    for d in depts:
        print(f"  [{d.id}] {d.name} ({d.code})")
    
    plans = db.query(WfPlan).all()
    print(f"\nWfPlans ({len(plans)}):")
    for p in plans:
        print(f"  [{p.id}] {p.title} | Year={p.plan_year} | Status={p.status} | Budget=${p.budget} | Target={p.target_headcount} | Current={p.current_headcount}")
    
    hcs = db.query(WfHeadcount).all()
    print(f"\nWfHeadcounts ({len(hcs)}):")
    for h in hcs:
        print(f"  [{h.id}] FY={h.fiscal_year} | Dept={h.department_id} | Approved={h.approved_positions} | Filled={h.filled_positions} | Vacant={h.vacant_positions} | Planned={h.planned_hires} | Cost=${h.projected_cost}")
    
    succs = db.query(WfSuccession).all()
    print(f"\nWfSuccessions ({len(succs)}):")
    for s in succs:
        print(f"  [{s.id}] Emp={s.employee_id} -> Succ={s.successor_employee_id} | Readiness={s.readiness_level} | Risk={s.risk_level} | Position={s.target_position}")
    
    reports = db.query(WfReport).all()
    print(f"\nWfReports ({len(reports)}):")
    for r in reports:
        print(f"  [{r.id}] {r.report_name} | Type={r.report_type}")

finally:
    db.close()
