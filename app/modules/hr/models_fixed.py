from sqlalchemy.sql import func

from app.database import Base


# ═══════════════════════════════════════════════════════════════════════════════════
# CUSTOM ENUM TYPE - handles both uppercase (existing DB) and lowercase (new values)
# ═══════════════════════════════════════════════════════════════════════════════════

from sqlalchemy.types import TypeDecorator, VARCHAR


class CaseInsensitiveEnum(TypeDecorator):
    """Enum type that handles case-insensitive values from database.
    
    Stores enum values in database as lowercase but accepts
    both uppercase and lowercase values when reading from DB.
    """
    impl = VARCHAR
    cache_ok = True

    def __init__(self, enum_class, *args, **kwargs):
        self.enum_class = enum_class
        self._value_to_enum = {e.value.lower(): e for e in enum_class}
        self._name_to_enum = {e.name.upper(): e for e in enum_class}
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        """Convert Python enum to database value (lowercase)."""
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.value
        if isinstance(value, str):
            try:
                return self.enum_class(value).value
            except ValueError:
                pass
            try:
                return self.enum_class[value.upper()].value
            except KeyError:
                pass
        raise ValueError(f"Invalid value for {self.enum_class.__name__}: {value}")

    def process_result_value(self, value, dialect):
        """Convert database value to Python enum - handles both cases."""
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value
        val_lower = value.lower()
        if val_lower in self._value_to_enum:
            return self._value_to_enum[val_lower]
        val_upper = value.upper()
        if val_upper in self._name_to_enum:
            return self._name_to_enum[val_upper]
        try:
            return self.enum_class(value)
        except ValueError:
            raise ValueError(f"Invalid enum value for {self.enum_class.__name__}: {value}")


# ═══════════════════════════════════════════════════════════════════════════════════
# ENUMS
# ════════════════════════════════════════════════════════════════════════════════════