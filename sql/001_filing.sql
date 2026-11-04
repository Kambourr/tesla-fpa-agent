-- One row per SEC filing. Comparatives live in fact, not as extra filing rows.
CREATE TABLE IF NOT EXISTS filing (
    accession VARCHAR PRIMARY KEY,
    form VARCHAR NOT NULL,
    period_end DATE NOT NULL,
    filing_date DATE NOT NULL,
    filing_url VARCHAR NOT NULL
);
