-- Latest stored value of each metric and period on or before a cutoff date.
-- Older fact rows stay in the table.
CREATE OR REPLACE MACRO fact_as_of(cutoff_date) AS TABLE
SELECT
    metric,
    period_start,
    period_end,
    accession,
    filing_date,
    filing_url,
    value,
    unit,
    concept,
    member
FROM fact_with_source
WHERE filing_date <= cutoff_date
QUALIFY row_number() OVER (
    PARTITION BY metric, period_start, period_end
    ORDER BY filing_date DESC, accession DESC
) = 1;
