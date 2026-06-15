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
    return {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5, "q6": q6}
