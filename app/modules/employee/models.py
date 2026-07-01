import enum


class EmploymentType(str, enum.Enum):
    FULL_TIME  = "full_time"
    PART_TIME  = "part_time"
    CONTRACT   = "contract"
    INTERN     = "intern"
    PROBATION  = "probation"

class EmployeeStatus(str, enum.Enum):
    ACTIVE     = "active"
    INACTIVE   = "inactive"
    ON_LEAVE   = "on_leave"
    TERMINATED = "terminated"
    RESIGNED   = "resigned"

class UserRole(str, enum.Enum):
    ADMIN       = "admin"
    HR_ADMIN    = "hr_admin"
    HR_MANAGER  = "hr_manager"
    MANAGER     = "manager"
    EMPLOYEE    = "employee"
    SUPER_ADMIN = "super_admin"

class Gender(str, enum.Enum):
    MALE   = "male"
    FEMALE = "female"
    OTHER  = "other"



