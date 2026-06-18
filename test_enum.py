"""Test what SQLAlchemy sends for the AssetStatus enum."""
from sqlalchemy import inspect
from app.database import engine
from app.modules.hr.models import Asset, AssetStatus

# Test 1: What does the MySQL ENUM definition look like?
inspector = inspect(engine)
cols = inspector.get_columns("assets")
for c in cols:
    if c["name"] == "status":
        print(f"MySQL type: {c['type']}")

# Test 2: What value does SQLAlchemy send?
from sqlalchemy import text
a = Asset(name="Test", asset_tag="TST-XXX", status=AssetStatus.AVAILABLE)
print(f"Asset.status type: {type(a.status)}")
print(f"Asset.status value: {a.status}")
print(f"Asset.status.value: {a.status.value if hasattr(a.status, 'value') else 'N/A'}")
print(f"Asset.status.name: {a.status.name if hasattr(a.status, 'name') else 'N/A'}")

# Test 3: Check what SQLAlchemy Column type expects
from sqlalchemy import Enum as SAEnum
from app.database import Base
for mapper in Base.registry.mappers:
    if mapper.class_ == Asset:
        for prop in mapper.attrs:
            if prop.key == "status":
                col_type = prop.columns[0].type
                print(f"Column type: {col_type}")
                print(f"Enum values: {col_type.enums}")
