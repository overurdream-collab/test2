-- Run with psql -v runtime_user=YOUR_ROLE -f deploy/setup_feature_permissions.sql
\set ON_ERROR_STOP on
SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'runtime_user') AS present
\gset
\if :present
BEGIN;
GRANT SELECT ON public.feature_catalog, public.organization_features TO :"runtime_user";
GRANT INSERT ON public.organization_features TO :"runtime_user";
GRANT UPDATE (status, effective_to, closed_by, closed_at, close_reason)
    ON public.organization_features TO :"runtime_user";
GRANT UPDATE (name) ON public.organizations TO :"runtime_user";
-- Actor row locking also requires an UPDATE privilege on one user column.
GRANT UPDATE (active) ON public.users TO :"runtime_user";
COMMIT;
\else
\echo 'Runtime role missing; feature grants skipped.'
\endif
