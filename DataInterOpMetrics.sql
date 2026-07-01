-- Data Interoperability detail — one row per active O11 enterprise infrastructure.
-- Surfaces each infrastructure's interoperability contract status (contractual vs.
-- SKU entitlement) alongside its customer, architecture, and edition.
--
-- Grain: exactly one row per active, current O11 enterprise infrastructure.
-- The customer join is deduped to the current monthly snapshot (is_current_month),
-- which keeps it strictly 1:1. Environment is intentionally NOT joined: it is a
-- one-to-many relationship (~5 environments per infra, one per stage/purpose) and
-- would break the per-infra grain. All interoperability fields already live on
-- INFRASTRUCTURE.

with customers as (
    -- CORE.CUSTOMER is a monthly snapshot; keep only the current month so the
    -- join stays 1:1 on customer_sfdc_id.
    select
        customer_sfdc_id,
        name
    from canonical.core.customer
    where is_current_month = true
),

O11_customer_infras as (
    select
        infrastructure_id,
        infrastructureuid,
        company_sfdc_id,
        architecture_type,
        infrastructure_type,
        infrastructure_type_label,
        editionid,
        contractual_interoperability,
        interoperability_related_activation_code,
        has_sku_interoperability
    from canonical.customersuccess.infrastructure
    where infrastructure_type in (
        'enterprise',
        'enterprise-freemium',
        'enterprise-premium',
        'enterprise-phoenix'
    )
    and is_active = true
    and is_current = true
)

select
    i.company_sfdc_id,
    c.name as customer_name,
    i.infrastructure_id,
    i.infrastructureuid,
    i.architecture_type,
    i.infrastructure_type,
    i.infrastructure_type_label,
    i.editionid,
    i.contractual_interoperability,
    i.has_sku_interoperability,
    i.interoperability_related_activation_code
from O11_customer_infras i
left join customers c
    on i.company_sfdc_id = c.customer_sfdc_id
order by c.name, i.infrastructure_id
;
