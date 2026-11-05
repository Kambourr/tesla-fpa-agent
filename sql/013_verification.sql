-- One verification report per quarter. verify_quarter replaces the row.
-- verified, flagged, unsupported and total count the narration's claims.
-- guard_hits, issues, claims and restatements are JSON lists. reasked is False
-- until narration stores whether the model was re-asked (narrative has no such column).
CREATE TABLE IF NOT EXISTS verification (
    quarter VARCHAR PRIMARY KEY,
    verified INT NOT NULL,
    flagged INT NOT NULL,
    unsupported INT NOT NULL,
    total INT NOT NULL,
    guard_hits JSON NOT NULL,
    issues JSON NOT NULL,
    claims JSON NOT NULL,
    restatements JSON NOT NULL,
    reasked BOOLEAN NOT NULL,
    created_at TIMESTAMP NOT NULL
);
