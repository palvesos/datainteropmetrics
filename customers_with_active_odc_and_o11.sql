-- Customers running active ODC and active O11 simultaneously
-- Counts unique customers (by Salesforce account ID) that have at least one
-- active ODC tenant and at least one active O11 infrastructure,
-- and sums their total ARR (in EUR) from CUSTOMERUNIFIEDINFO.

-- Active ODC tenants are identified by a non-null TENANT_ID with active status
WITH active_odc_customers AS (
    SELECT DISTINCT COMPANY_SFDC_ID
    FROM CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTUREACTUAL
    WHERE TENANT_ID IS NOT NULL
      AND INFRASTRUCTURE_STATUS = 'active'
      AND COMPANY_SFDC_ID IS NOT NULL
),

-- O11 infrastructures have no TENANT_ID (covers on-premises, hybrid, and O11 cloud)
active_o11_customers AS (
    SELECT DISTINCT COMPANY_SFDC_ID
    FROM CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTUREACTUAL
    WHERE TENANT_ID IS NULL
      AND INFRASTRUCTURE_STATUS = 'active'
      AND COMPANY_SFDC_ID IS NOT NULL
),

-- Customers running both platforms simultaneously
customers_on_both AS (
    SELECT odc.COMPANY_SFDC_ID
    FROM active_odc_customers odc
    INNER JOIN active_o11_customers o11
        ON odc.COMPANY_SFDC_ID = o11.COMPANY_SFDC_ID
)

-- COMPANY_SFDC_ID is the Salesforce account ID used as the customer key
-- ARR_EUR is sourced from CUSTOMERUNIFIEDINFO (Netsuite conversion rate)
SELECT
    (SELECT COUNT(*) FROM active_odc_customers)  AS customers_with_active_odc,
    (SELECT COUNT(*) FROM active_o11_customers)  AS customers_with_active_o11,
    (SELECT COUNT(*) FROM customers_on_both)     AS customers_with_active_odc_and_active_o11,
    (
        SELECT SUM(cui.ARR_EUR)
        FROM customers_on_both cb
        INNER JOIN CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO cui
            ON cb.COMPANY_SFDC_ID = cui.COMPANY_SFDC_ID
    )                                            AS total_arr_eur
;
