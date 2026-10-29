-- Temporary, for the M3 "dbt test failure" acceptance test (spec.md): a singular
-- test fails if it returns rows, so this one always fails. Revert after the red run.
select 1 as must_fail
