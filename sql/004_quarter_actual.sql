-- First-reported quarter actuals. M1-T8 fills this. Restatements stay in fact.
CREATE TABLE IF NOT EXISTS quarter_actual (
    quarter VARCHAR NOT NULL,
    metric VARCHAR NOT NULL,
    value DECIMAL(24, 4) NOT NULL,
    accession VARCHAR NOT NULL,
    filing_date DATE NOT NULL,
    filing_url VARCHAR NOT NULL,
    basis VARCHAR NOT NULL,
    PRIMARY KEY (quarter, metric)
);
