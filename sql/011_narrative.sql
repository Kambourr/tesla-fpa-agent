-- One narration per reported quarter. store_narration replaces the row.
-- payload is the NarrativeDraft as JSON. issues lists what validation found;
-- a row with issues is recorded, not hidden. M3-T3 reads input_hash.
CREATE TABLE IF NOT EXISTS narrative (
    quarter VARCHAR NOT NULL PRIMARY KEY,
    kind VARCHAR NOT NULL CHECK (kind IN ('memo', 'memo+qa')),
    input_hash VARCHAR NOT NULL,
    prompt_version VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    payload JSON NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    issues JSON NOT NULL,
    created_at TIMESTAMP NOT NULL
);
