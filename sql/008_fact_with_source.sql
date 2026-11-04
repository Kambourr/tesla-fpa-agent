-- Filing date and URL sit on the filing row. This view is the stored fact with its source.
CREATE OR REPLACE VIEW fact_with_source AS
SELECT
    fact.metric,
    fact.period_start,
    fact.period_end,
    fact.accession,
    filing.filing_date,
    filing.filing_url,
    fact.value,
    fact.unit,
    fact.concept,
    fact.member
FROM fact
INNER JOIN filing ON filing.accession = fact.accession;
