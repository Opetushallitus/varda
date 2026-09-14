# Audit logging

Audit logs are sent to CloudWatch in respective AWS accounts.
READ audit logs are gathered from `Z5_AuditLog` and CREATE/UPDATE/DELETE
logs from historical tables of models.

## Data access logging

Data access logs are gathered from `Z12_DataAccessLog`. They are also sent to CloudWatch,
and then forwarded to SQS queue in a KOSKI account. Data access logs can be viewed
by users in https://opintopolku.fi/oma-opintopolku-loki/ (production) and
https://testiopintopolku.fi/oma-opintopolku-loki/ (QA). "Oma Opintopolku loki" service
is maintained by the KOSKI team.
