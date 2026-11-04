-- Forecast-versus-actual error. M2 fills this.
CREATE TABLE IF NOT EXISTS backtest (
    quarter VARCHAR NOT NULL,
    metric VARCHAR NOT NULL,
    actual DECIMAL(24, 4),
    forecast DECIMAL(24, 4),
    absolute_pct_error DECIMAL(24, 4),
    PRIMARY KEY (quarter, metric)
);
