-- One value per metric, period, and filing. A later comparative is another row.
CREATE TABLE IF NOT EXISTS fact (
    metric VARCHAR NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    accession VARCHAR NOT NULL REFERENCES filing (accession),
    value DECIMAL(24, 4) NOT NULL,
    unit VARCHAR NOT NULL,
    concept VARCHAR NOT NULL,
    member VARCHAR,
    PRIMARY KEY (metric, period_start, period_end, accession)
);
