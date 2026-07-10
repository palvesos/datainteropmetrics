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
        "PROD_CUSTOMERS": [119, 97, 78, 63],
        "O11_ODC_CUSTOMERS": [785, 756, 739, 714],
    })
    return {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5, "q6": q6,
            "q7": q7, "q8": q8, "q9": q9, "q10": q10, "q11": q11, "q12": q12, "q13": q13}
