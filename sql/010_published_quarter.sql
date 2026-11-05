-- Quarters the publish step may show. M2-T10 fills this on every model run.
-- kind is 'backtest' for a reported quarter, or 'forward' for the next quarter,
-- which appears only when PUBLISH_FORWARD_FORECAST is true.
CREATE TABLE IF NOT EXISTS published_quarter (
    quarter VARCHAR NOT NULL PRIMARY KEY,
    kind VARCHAR NOT NULL CHECK (kind IN ('backtest', 'forward')),
    has_forecast BOOLEAN NOT NULL
);
