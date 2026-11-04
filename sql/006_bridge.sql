-- Variance bars. M2 fills this. One row per quarter, bridge, and driver.
CREATE TABLE IF NOT EXISTS bridge (
    quarter VARCHAR NOT NULL,
    bridge VARCHAR NOT NULL,
    driver VARCHAR NOT NULL,
    value DECIMAL(24, 4) NOT NULL,
    favorable BOOLEAN NOT NULL,
    PRIMARY KEY (quarter, bridge, driver)
);
