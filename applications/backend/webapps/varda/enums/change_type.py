import enum


class ChangeType(enum.Enum):
    UNCHANGED = "UNCHANGED"
    CREATED = "CREATED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    MOVED = "MOVED"
