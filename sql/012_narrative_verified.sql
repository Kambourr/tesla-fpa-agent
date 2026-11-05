-- M3-T3: a stored narration is reused only after its claims are verified.
-- verified is FALSE until mark_verified sets it for the row's input_hash.
-- DuckDB rejects NOT NULL together with IF NOT EXISTS, so the column is added
-- first and then set NOT NULL. Both statements can run again on every apply.
ALTER TABLE narrative ADD COLUMN IF NOT EXISTS verified BOOLEAN DEFAULT FALSE;
ALTER TABLE narrative ALTER COLUMN verified SET NOT NULL;
