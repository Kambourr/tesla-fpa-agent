-- Manual production and deliveries. Column names match data/manual/deliveries.csv.
CREATE TABLE IF NOT EXISTS deliveries (
    quarter VARCHAR PRIMARY KEY,
    production_total BIGINT NOT NULL,
    deliveries_total BIGINT NOT NULL,
    release_date DATE NOT NULL,
    source_url VARCHAR NOT NULL
);
