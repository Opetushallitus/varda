import enum


class ReportStatus(enum.Enum):
    PENDING = "PENDING"
    CREATING = "CREATING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
