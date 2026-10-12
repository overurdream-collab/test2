-- psql variable: runtime_user (supplied by setup_rbac_permissions.sh).
-- Grant UPDATE on RBAC closure columns and organizations.name for row locks.
-- Existing triggers protect closed records and prevent deletion; they do not
-- forbid every change to open records or protect organizations.name.
\set ON_ERROR_STOP on

SELECT EXISTS (
    SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :'runtime_user'
) AS runtime_role_exists
\gset

\if :runtime_role_exists
BEGIN;

GRANT UPDATE (status, effective_to, closed_by, closed_at, close_reason, active)
    ON public.users TO :"runtime_user";

GRANT UPDATE (status, effective_to, closed_by, closed_at, close_reason)
    ON public.groups TO :"runtime_user";

GRANT UPDATE (status, effective_to, closed_by, closed_at, close_reason)
    ON public.group_permissions TO :"runtime_user";

GRANT UPDATE (status, effective_to, closed_by, closed_at, close_reason)
    ON public.user_groups TO :"runtime_user";

GRANT UPDATE (status, effective_to, closed_by, closed_at, close_reason)
    ON public.user_permissions TO :"runtime_user";

-- SELECT FOR UPDATE requires UPDATE on at least one column.
-- This grant also permits changing the organization name; it grants no id update.
GRANT UPDATE (name) ON public.organizations TO :"runtime_user";

COMMIT;
\echo 'RBAC UPDATE permissions granted to' :"runtime_user"
\else
\echo 'WARNING: runtime role' :"runtime_user" 'does not exist; skipped all GRANTs.'
\endif
