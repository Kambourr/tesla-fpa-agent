-- Base, bull, and bear forecasts. M2 fills this. value stays null when history is empty.
CREATE TABLE IF NOT EXISTS forecast (
    quarter VARCHAR NOT NULL,
    metric VARCHAR NOT NULL,
    scenario VARCHAR NOT NULL,
    cutoff_date DATE NOT NULL,
    value DECIMAL(24, 4),
    empty_history BOOLEAN NOT NULL,
    PRIMARY KEY (quarter, metric, scenario)
);
