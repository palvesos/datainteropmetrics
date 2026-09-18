import pandas as pd
import pytest


@pytest.fixture
def sample_data():
    q1 = pd.DataFrame({
        "MONTH_START": pd.to_datetime(["2026-06-01", "2026-05-01", "2026-04-01", "2026-03-01"]),
        "INTEROP_CUSTOMERS": [582, 573, 555, 517],
        "SKU_INTEROP_CUSTOMERS": [522, 513, 497, 461],
        "TOTAL_CUSTOMERS": [2884, 2913, 2914, 2927],
        "ADOPTION_PCT": [20.18, 19.67, 19.05, 17.66],
    })
    q2 = pd.DataFrame({
        "PRODUCT_FAMILY": ["O11/ODC", "O11", "ODC", "O11", "O11"],
        "PRODUCT_CATEGORY": ["O11/ODC", "O11 Cloud", "ODC", "O11 On-Prem", "O11 Mix"],
        "TOTAL_CUSTOMERS": [775, 668, 469, 913, 45],
        "INTEROP_ACTIVE": [582, 0, 0, 0, 0],
        "HAS_SKU_INTEROP": [522, 0, 0, 0, 0],
    })
    q3 = pd.DataFrame({
        "INFRA_ARCH_TYPE": ["cloud", "cloud", "on-premises", "hybrid"],
        "PRODUCT_FAMILY": ["ODC", "O11", "O11", "O11"],
        "COMPANIES": [1241, 1263, 1212, 31],
        "INTEROP_COMPANIES": [582, 414, 163, 6],
        "SKU_INTEROP": [522, 370, 146, 4],
    })
    q4 = pd.DataFrame({
        "MONTH": pd.to_datetime(["2026-06-01", "2026-05-01", "2026-04-01", "2026-03-01"]),
        "ACTIVE_INFRA": [157, 237, 215, 311],
        "PROD_EXECUTIONS": [38462, 114734, 74750, 34260],
        "DEV_EXECUTIONS": [33788, 119536, 98094, 40394],
        "NONPROD_EXECUTIONS": [4208, 16460, 8502, 13002],
        "PROD_AO_USAGE": [1788454, 4952590, 4138558, 4454132],
    })
    q5 = pd.DataFrame({
        "REPORT_MONTH": pd.to_datetime(["2026-06-01", "2026-05-01", "2026-04-01", "2026-03-01"]),
        "ACTIVE_INFRA": [1153, 1141, 1095, 1028],
        "PROD_AO_LAST_WEEK": [2050181, 2033225, 1996318, 1915323],
        "DEV_AO_LAST_WEEK": [3517256, 3508328, 3368541, 3210840],
        "PROD_AO_MAX_WEEK": [2060337, 2122011, 2050587, 1964686],
        "DEV_AO_MAX_WEEK": [3534152, 3543463, 3413880, 3225250],
    })
    q6 = pd.DataFrame({
        "IS_INTEROPERABILITY": [False, True, True],
        "HAS_SKU_INTEROPERABILITY": [False, False, True],
        "COMPANY_COUNT": [182420, 430, 3451],
    })
    q7 = pd.DataFrame({
        "MONTH": pd.to_datetime(["2026-06-01", "2026-05-01", "2026-04-01", "2026-03-01"]),
        "UNIQUE_TENANTS": [160, 178, 150, 120],
        "UNIQUE_CUSTOMERS": [140, 155, 130, 100],
        "TOTAL_CONNECTORS": [18000, 21000, 17500, 14000],
    })
    q8 = pd.DataFrame({
        "PROVIDER": ["o11cloud_mssql", "o11cloud_oracle", "o11selfhosted_mssql", "o11selfhosted_oracle"],
        "HOSTING": ["cloud", "cloud", "self-hosted", "self-hosted"],
        "ENGINE": ["mssql", "oracle", "mssql", "oracle"],
        "UNIQUE_TENANTS": [158, 11, 6, 2],
        "UNIQUE_CUSTOMERS": [140, 10, 5, 2],
        "TOTAL_CONNECTORS": [18307, 1136, 412, 112],
    })
    q9 = pd.DataFrame({
        "USAGE_DEPLOYMENT_OPTION": ["O11", "ODC", "O11/ODC"],
        "TOTAL_CUSTOMERS": [900, 400, 658],
        "CUSTOMERS_WITH_AGENTS": [50, 300, 409],
        "ADOPTION_RATE_PCT": [5.6, 75.0, 62.2],
        "TOTAL_AGENTS": [200, 8000, 11852],
        "TOTAL_EXECUTIONS": [150, 6000, 9077],
    })
    q10 = pd.DataFrame({
        "COMPANY_SFDC_ID": ["001A", "001B", "001C"],
        "COMPANY_NAME": ["Acme Corp", "Globex", "Initech"],
        "SEGMENT": ["Enterprise", "Mid-Market", "Enterprise"],
        "USAGE_DEPLOYMENT_OPTION": ["O11/ODC", "O11", "O11/ODC"],
        "ARR_EUR": [500000.0, 250000.0, 120000.0],
    })
    q11 = pd.DataFrame({
        "ACTIVATION_CODE": ["AC1", "AC2"],
        "COMPANY_SFDC_ID": ["001D", "001E"],
        "COMPANY_NAME": ["Umbrella", "Stark Ind"],
        "ARCHITECTURE_TYPE": ["cloud", "on-premises"],
        "INFRASTRUCTURE_STATUS": ["active", "active"],
        "USAGE_DEPLOYMENT_OPTION": ["O11", "O11/ODC"],
    })
    q12 = pd.DataFrame({
        "MONTH": pd.to_datetime(["2026-06-01", "2026-05-01", "2026-04-01", "2026-03-01"]),
        "UNIQUE_TENANTS": [22, 25, 20, 15],
        "UNIQUE_CUSTOMERS": [18, 20, 16, 12],
        "TOTAL_CONNECTORS": [1100, 1300, 1000, 800],
    })
    q13 = pd.DataFrame({
        "MONTH": pd.to_datetime(["2026-06-01", "2026-05-01", "2026-04-01", "2026-03-01"]),
        "DEV_CUSTOMERS": [153, 133, 110, 86],
        "NONPROD_CUSTOMERS": [141, 118, 99, 81],
        "PROD_CUSTOMERS": [119, 97, 78, 63],
        "O11_ODC_CUSTOMERS": [785, 756, 739, 714],
    })
    q14 = pd.DataFrame({
        "MONTH": pd.to_datetime(["2026-06-01", "2026-05-01", "2026-04-01", "2026-03-01"]),
        "DEV_CUSTOMERS": [109, 94, 83, 57],
        "PROD_CUSTOMERS": [36, 34, 27, 23],
        "DEV_APPS": [125, 112, 94, 62],
        "PROD_APPS": [38, 36, 28, 23],
        "O11_ODC_CUSTOMERS": [785, 756, 739, 714],
    })
    q15 = pd.DataFrame({
        "DAY": pd.to_datetime([
            "2026-06-02", "2026-06-03", "2026-06-06", "2026-05-05", "2026-05-12"]),  # Tue, Wed, Sat, Tue, Tue
        "ADD_REMOVE_EVENTS": [3, 2, 1, 4, 2],
        "RECONFIGURE_EVENTS": [5, 1, 0, 3, 4],
    })
    q16 = pd.DataFrame({
        "MONTH": pd.to_datetime([
            "2026-06-01", "2026-06-01", "2026-06-01", "2026-06-01", "2026-06-01",
            "2026-06-01", "2026-06-01", "2026-06-01", "2026-05-01", "2026-05-01"]),
        "RING": ["ga", "ga", "ga", "ea", "ga", "ea", "ga", "ea", "ga", "ea"],
        "REGION": ["EU (Frankfurt)", "US East (N. Virginia)", "EU (Ireland)",
                   "AP (Singapore)", "EU (London)", "Canada (Central)", "AP (Tokyo)",
                   "AP (Mumbai)", "EU (Frankfurt)", "US East (N. Virginia)"],
        "ADD_REMOVE_EVENTS": [40, 22, 10, 8, 16, 16, 0, 2, 9, 5],
        "RECONFIGURE_EVENTS": [90, 49, 26, 25, 13, 4, 3, 0, 14, 8],
    })
    q17 = pd.DataFrame({
        "REGION": ["EU (Frankfurt)", "US East (N. Virginia)", "EU (Ireland)",
                   "EU (Frankfurt)", "US East (N. Virginia)", "AP (Sydney)"],
        "RING": ["ga", "ga", "ga", "ea", "ea", "ga"],
        "AVG_CHANGES_PER_TENANT": [3.64, 3.25, 3.27, 22.0, 6.0, 1.33],
        "MEDIAN_CHANGES_PER_TENANT": [2.0, 2.0, 2.0, 22.0, 6.0, 1.0],
        "N_TENANTS": [36, 20, 11, 1, 1, 6],
        "TOTAL_CHANGES": [131, 65, 36, 22, 6, 8],
    })
    q18 = pd.DataFrame({
        "WINDOW_KEY": ["all", "all", "all", "all", "all", "all", "1m", "1m"],
        "REGION": ["EU (Frankfurt)", "EU (Frankfurt)", "EU (Frankfurt)",
                   "US East (N. Virginia)", "US East (N. Virginia)", "EU (Ireland)",
                   "EU (Frankfurt)", "EU (Frankfurt)"],
        "RING": ["ga", "ga", "ea", "ga", "ga", "ga", "ga", "ga"],
        "WEEKDAY": [2, 3, 2, 3, 4, 2, 2, 3],  # Tue, Wed, Tue, Wed, Thu, Tue, Tue, Wed
        "CHANGE_TYPE": ["add_remove", "reconfigure", "add_remove",
                        "add_remove", "reconfigure", "reconfigure",
                        "add_remove", "reconfigure"],
        "EVENTS": [8, 20, 4, 10, 6, 5, 3, 5],
        "N_TENANTS": [10, 10, 2, 5, 5, 4, 8, 8],
    })
    q19 = pd.DataFrame({
        "COMPANY_NAME": ["Umbrella", "Stark Ind"],
        "COMPANY_SFDC_ID": ["001D", "001E"],
        "TENANT_ID": ["ten-1", "ten-2"],
        "N_O11_ENVS": [1, 2],
        "PEAK_CONNECTORS": [1, 2],
        "LAST_KNOWN_CONNECTORS": [1, 1],
        "LAST_CONNECTOR_TELEMETRY_DAY": pd.to_datetime(["2026-01-28", "2026-04-07"]),
        "DAYS_SINCE_CONNECTOR_TELEMETRY": [170, 101],
        "LAST_PLATFORM_USAGE_DAY": pd.to_datetime(["2026-06-15", "2026-06-15"]),
    })
    q20 = pd.DataFrame({
        "COMPANY_NAME": ["Umbrella", "Stark Ind", "Wayne Enterprises"],
        "COMPANY_SFDC_ID": ["001D", "001E", "001F"],
        "REMOVAL_EVENTS": [4, 3, 3],
        "TOTAL_CONNECTORS_REMOVED": [5, 3, 2],
        "PEAK_TOTAL_CONNECTORS": [8, 6, 2],
        "CONNECTORS_TODAY": [8, 3, 0],
    })
    q21 = pd.DataFrame({
        "COMPANY_NAME": ["Cyberdyne", "Tyrell Corp", "Weyland"],
        "COMPANY_SFDC_ID": ["001G", "001H", "001I"],
        "NUM_O11_INFRAS": [2, 5, 3],
        "NUM_DF_PROVIDERS": [1, 1, 2],
        "CURRENT_DF_CONNECTORS": [10, 4, 4],
    })
    q22 = pd.DataFrame({
        "COMPANY_NAME": ["MultiCorp A", "MultiCorp B"],
        "COMPANY_SFDC_ID": ["001J", "001K"],
        "NUM_O11_INFRAS": [3, 2],
        "REMOVAL_EVENTS": [2, 1],
        "TOTAL_CONNECTORS_REMOVED": [3, 1],
        "PEAK_TOTAL_CONNECTORS": [10, 4],
        "CONNECTORS_TODAY": [7, 3],
    })
    q23 = pd.DataFrame({
        "COMPANY_NAME": ["MultiRemoved"],
        "COMPANY_SFDC_ID": ["001L"],
        "TENANT_ID": ["ten-9"],
        "NUM_O11_INFRAS": [11],
        "N_O11_ENVS": [1],
        "PEAK_CONNECTORS": [1],
        "LAST_KNOWN_CONNECTORS": [1],
        "LAST_CONNECTOR_TELEMETRY_DAY": pd.to_datetime(["2026-04-07"]),
        "DAYS_SINCE_CONNECTOR_TELEMETRY": [101],
        "LAST_PLATFORM_USAGE_DAY": pd.to_datetime(["2026-06-15"]),
    })
    return {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5, "q6": q6,
            "q7": q7, "q8": q8, "q9": q9, "q10": q10, "q11": q11, "q12": q12,
            "q13": q13, "q14": q14, "q15": q15, "q16": q16, "q17": q17, "q18": q18,
            "q19": q19, "q20": q20, "q21": q21, "q22": q22, "q23": q23}
