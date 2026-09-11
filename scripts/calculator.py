#!/usr/bin/env python3
"""
Institutional Deterministic Quantitative Unit Economics Calculator.
Part of the 'marketing-consultant' skill for Google Antigravity.

Computes:
  - Blended & Paid CAC
  - LTV (Traditional & Expansion/NRR Adjusted)
  - LTV/CAC Ratio and Hurdle Validation
  - Payback Period (Months)
  - SaaS Magic Number
  - Net Revenue Retention (NRR) & Gross Revenue Retention (GRR)
  - 24-Month Cohort Retention & Cumulative Gross Profit Breakeven
  - Hill Function Media Saturation Curves & Marginal Returns
  - 3-Scenario Sensitivity Modeling (Base, Bull, Bear)

Zero external dependencies. Runs on standard Python 3.8+.
"""

import sys
import os
import json
import math
import argparse


def calculate_cac(sm_spend, new_customers, paid_spend=None, paid_customers=None):
    """Calculates Blended CAC and Paid CAC."""
    if new_customers <= 0:
        blended_cac = 0.0
    else:
        blended_cac = float(sm_spend) / float(new_customers)

    paid_cac = None
    if paid_spend is not None and paid_customers is not None and paid_customers > 0:
        paid_cac = float(paid_spend) / float(paid_customers)

    return {
        "blended_cac": round(blended_cac, 2),
        "paid_cac": round(paid_cac, 2) if paid_cac is not None else None,
        "sm_spend": round(float(sm_spend), 2),
        "new_customers": int(new_customers),
    }


def calculate_ltv(arpu_monthly, gross_margin_pct, monthly_churn, monthly_expansion=0.0, max_months_cap=None):
    """
    Calculates LTV using both traditional formula and expansion-adjusted net churn.
    LTV_traditional = (ARPU * Gross Margin) / Churn
    When expansion > 0, LTV_expansion strictly models compounded net customer value over
    the expected customer relationship lifespan T = 1 / Churn (or max_months_cap if explicitly specified).
    Guarantees LTV_expansion >= LTV_traditional whenever expansion >= 0.
    """
    # Normalize percentage inputs if passed as whole numbers (e.g. 80 instead of 0.80)
    raw_gm = float(gross_margin_pct)
    gm = (raw_gm / 100.0) if raw_gm > 1.0 else raw_gm

    raw_churn = float(monthly_churn)
    if raw_churn > 1.0:
        raw_churn = raw_churn / 100.0
    churn = max(raw_churn, 0.0001)  # Prevent div-by-zero

    raw_exp = float(monthly_expansion)
    if raw_exp > 1.0:
        raw_exp = raw_exp / 100.0
    expansion = max(0.0, raw_exp)

    monthly_gp = float(arpu_monthly) * gm
    traditional_ltv = monthly_gp / churn
    traditional_lifespan_months = 1.0 / churn

    net_churn = churn - expansion
    if net_churn > 0.001:
        expansion_lifespan_months = 1.0 / net_churn
        expansion_ltv = monthly_gp / net_churn
    else:
        # Negative or zero net churn (expansion >= churn)
        # In discrete cohort terms over customer logo relationship lifespan T:
        T = traditional_lifespan_months
        if max_months_cap is not None and float(max_months_cap) > 0:
            T = min(T, float(max_months_cap))

        g = expansion - churn
        if g > 0.00001:
            # Compounding geometric sum over lifespan T: ((1 + g)^T - 1) / g
            expansion_lifespan_months = ((1.0 + g) ** T - 1.0) / g
        else:
            expansion_lifespan_months = T
        expansion_ltv = monthly_gp * expansion_lifespan_months

    # Economic invariant: expansion cannot reduce customer lifetime value
    expansion_ltv = max(traditional_ltv, expansion_ltv)
    expansion_lifespan_months = max(traditional_lifespan_months, expansion_lifespan_months)

    return {
        "arpu_monthly": round(float(arpu_monthly), 2),
        "gross_margin_pct": round(gm, 4),
        "monthly_gross_profit": round(monthly_gp, 2),
        "monthly_churn_pct": round(churn * 100, 2),
        "monthly_expansion_pct": round(expansion * 100, 2),
        "traditional_ltv": round(traditional_ltv, 2),
        "expansion_ltv": round(expansion_ltv, 2),
        "traditional_lifespan_months": round(traditional_lifespan_months, 1),
        "expansion_lifespan_months": round(expansion_lifespan_months, 1),
    }



def calculate_payback_months(cac, arpu_monthly, gross_margin_pct):
    """Payback Period = CAC / (ARPU * Gross Margin)"""
    raw_gm = float(gross_margin_pct)
    gm = (raw_gm / 100.0) if raw_gm > 1.0 else raw_gm
    monthly_gp = float(arpu_monthly) * gm
    if monthly_gp <= 0:
        return 999.0
    return round(float(cac) / monthly_gp, 1)


def calculate_magic_number(prior_q_revenue, current_q_revenue, prior_q_sm_spend):
    """
    SaaS Magic Number = ((Revenue_Q - Revenue_{Q-1}) * 4) / SM_Spend_{Q-1}
    Measures net new annualized revenue generated per dollar of sales & marketing.
    """
    if prior_q_sm_spend <= 0:
        return 0.0
    net_new_arr = (float(current_q_revenue) - float(prior_q_revenue)) * 4.0
    magic_num = net_new_arr / float(prior_q_sm_spend)
    return round(magic_num, 2)


def calculate_retention_metrics(monthly_logo_churn, monthly_expansion=0.0):
    """Computes Annualized Logo Churn, Annualized GRR, and Annualized NRR."""
    raw_c = float(monthly_logo_churn)
    if raw_c > 1.0:
        raw_c = raw_c / 100.0
    c = min(1.0, max(0.0001, raw_c))

    raw_e = float(monthly_expansion)
    if raw_e > 1.0:
        raw_e = raw_e / 100.0
    e = max(0.0, raw_e)

    # Annualized logo retention = (1 - c)^12
    ann_logo_retention = ((1.0 - c) ** 12) if c < 1.0 else 0.0
    ann_logo_churn = 1.0 - ann_logo_retention

    # Gross Revenue Retention (GRR capped at 100%)
    ann_grr = ann_logo_retention * 100.0

    # Net Revenue Retention (NRR with expansion)
    monthly_nrr_factor = max(0.0, 1.0 - c + e)
    ann_nrr = (monthly_nrr_factor ** 12) * 100.0

    return {
        "annualized_logo_churn_pct": round(ann_logo_churn * 100, 2),
        "annualized_grr_pct": round(ann_grr, 2),
        "annualized_nrr_pct": round(ann_nrr, 2),
    }


def calculate_hill_saturation(spend, max_output, half_sat_spend, shape_n):
    """
    Hill Function Diminishing Returns:
    Response(S) = K * (S^n / (S_50^n + S^n))

    Marginal Response = K * n * S^{n-1} * S_50^n / (S_50^n + S^n)^2
    Marginal CAC = 1 / Marginal Response
    """
    s = float(spend)
    k = float(max_output)
    s50 = float(half_sat_spend)
    n = float(shape_n)

    if s <= 0 or k <= 0 or s50 <= 0 or n <= 0:
        return {
            "spend": s,
            "response": 0.0,
            "saturation_pct": 0.0,
            "marginal_response": 0.0,
            "marginal_cac": None,
            "average_cpa": None
        }

    s_n = s ** n
    s50_n = s50 ** n
    denom = s50_n + s_n

    response = k * (s_n / denom)
    saturation_pct = (response / k) * 100.0

    # Derivative
    marginal_response = (k * n * (s ** (n - 1)) * s50_n) / (denom ** 2) if denom > 0 else 0.0
    marginal_cac = (1.0 / marginal_response) if marginal_response > 1e-9 else None
    avg_cpa = (s / response) if response > 0 else None

    return {
        "spend": round(s, 2),
        "response": round(response, 2),
        "saturation_pct": round(saturation_pct, 2),
        "marginal_response": round(marginal_response, 8),
        "marginal_cac": round(marginal_cac, 2) if marginal_cac is not None else None,
        "average_cpa": round(avg_cpa, 2) if avg_cpa is not None else None
    }


def simulate_cohort_trajectory(initial_cohort_size, arpu_monthly, gross_margin_pct, monthly_churn, monthly_expansion=0.0, custom_curve=None, horizon_months=24, blended_cac=0.0):
    """
    Simulates cohort decay over horizon_months.
    Tracks active customers, revenue, gross profit, cumulative gross profit, and breakeven month.
    Seamlessly continues decay from the last observed empirical retention point if custom_curve is shorter than horizon.
    """
    c0 = float(initial_cohort_size)
    gp_margin = float(gross_margin_pct)
    c = max(0.0001, min(1.0, float(monthly_churn)))
    e = max(0.0, float(monthly_expansion))

    rows = []
    cum_gp_per_customer = 0.0
    breakeven_month = None

    for m in range(horizon_months + 1):
        if custom_curve and len(custom_curve) > 0:
            if m < len(custom_curve):
                retention_rate = max(0.0, min(1.0, float(custom_curve[m])))
            else:
                # Smooth continuous decay from the last observed empirical retention point
                retention_rate = max(0.0, float(custom_curve[-1]) * ((1.0 - c) ** (m - len(custom_curve) + 1)))
        else:
            retention_rate = max(0.0, (1.0 - c) ** m)

        active_customers = round(c0 * retention_rate, 1)
        # ARPU with expansion compounding
        current_arpu = float(arpu_monthly) * ((1.0 + e) ** m)
        m_rev = active_customers * current_arpu
        m_gp = m_rev * gp_margin

        # Cumulative gross profit per initially acquired customer
        cum_gp_per_customer += (m_gp / c0) if c0 > 0 else 0.0

        if breakeven_month is None and blended_cac > 0 and cum_gp_per_customer >= blended_cac:
            breakeven_month = m

        rows.append({
            "month": m,
            "retention_rate": round(retention_rate, 4),
            "retention_pct": round(retention_rate * 100, 2),
            "active_customers": active_customers,
            "monthly_arpu": round(current_arpu, 2),
            "monthly_revenue": round(m_rev, 2),
            "monthly_gross_profit": round(m_gp, 2),
            "cum_gross_profit_per_customer": round(cum_gp_per_customer, 2)
        })

    return {
        "horizon_months": horizon_months,
        "breakeven_month": breakeven_month,
        "trajectory": rows
    }


def run_scenarios(base_inputs):
    """
    Generates Base, Bull, and Bear scenario evaluations based on multipliers.
    """
    scenarios_cfg = base_inputs.get("scenarios", {
        "base": {"arpu_multiplier": 1.0, "churn_multiplier": 1.0, "cac_multiplier": 1.0, "conversion_multiplier": 1.0},
        "bull": {"arpu_multiplier": 1.15, "churn_multiplier": 0.75, "cac_multiplier": 0.80, "conversion_multiplier": 1.25},
        "bear": {"arpu_multiplier": 0.90, "churn_multiplier": 1.40, "cac_multiplier": 1.30, "conversion_multiplier": 0.75}
    })

    ue = base_inputs.get("unit_economics", {})
    base_arpu = float(ue.get("arpu_monthly", 2500))
    base_gm = float(ue.get("gross_margin_pct", 0.80))
    base_churn = float(ue.get("monthly_logo_churn", 0.015))
    base_exp = float(ue.get("monthly_expansion_rate", 0.01))
    base_sm = float(ue.get("sales_and_marketing_monthly", 0.0))
    base_cust = float(ue.get("new_customers_monthly", 0.0))
    base_direct_cac = float(ue.get("blended_cac") or ue.get("cac", 0.0))

    results = {}
    for name, cfg in scenarios_cfg.items():
        s_arpu = base_arpu * cfg.get("arpu_multiplier", 1.0)
        s_churn = base_churn * cfg.get("churn_multiplier", 1.0)
        s_cust = max(1.0, (base_cust * cfg.get("conversion_multiplier", 1.0)) if base_cust > 0 else 1.0)

        if "spend_multiplier" in cfg and base_sm > 0:
            s_sm = base_sm * cfg["spend_multiplier"]
            s_cac = s_sm / s_cust
        elif base_sm > 0 and base_cust > 0:
            s_sm = base_sm * cfg.get("cac_multiplier", 1.0)
            s_cac = s_sm / s_cust
        elif base_direct_cac > 0:
            s_cac = base_direct_cac * cfg.get("cac_multiplier", 1.0)
        else:
            s_cac = 0.0

        s_ltv_data = calculate_ltv(s_arpu, base_gm, s_churn, base_exp)
        s_ltv = s_ltv_data["expansion_ltv"]
        s_payback = calculate_payback_months(s_cac, s_arpu, base_gm)
        s_ratio = round(s_ltv / s_cac, 2) if s_cac > 0 else 0.0

        results[name] = {
            "name": name.upper(),
            "arpu_monthly": round(s_arpu, 2),
            "monthly_churn_pct": round(s_churn * 100, 2),
            "new_customers_monthly": round(s_cust, 1),
            "blended_cac": round(s_cac, 2),
            "expansion_ltv": round(s_ltv, 2),
            "traditional_ltv": round(s_ltv_data["traditional_ltv"], 2),
            "ltv_cac_ratio": s_ratio,
            "payback_months": s_payback,
            "year1_customer_gp": round(s_arpu * base_gm * 12, 2)
        }

    return results


def evaluate_gate_hurdles(ltv_cac_ratio, payback_months, magic_number=None, business_model="b2b_saas"):
    """
    Evaluates unit economics against institutional consulting benchmarks.
    """
    # 1. LTV/CAC Hurdle
    if ltv_cac_ratio >= 3.0:
        ltv_cac_status = "PASS"
        ltv_cac_comment = f"LTV/CAC ratio of {ltv_cac_ratio}x exceeds the >= 3.0x institutional hurdle. Profitable unit economics."
    elif ltv_cac_ratio >= 1.5:
        ltv_cac_status = "CONDITIONAL"
        ltv_cac_comment = f"LTV/CAC ratio of {ltv_cac_ratio}x is below the 3.0x benchmark. Requires churn reduction or ARPU expansion."
    else:
        ltv_cac_status = "FAIL"
        ltv_cac_comment = f"LTV/CAC ratio of {ltv_cac_ratio}x destroys enterprise value. Freeze scaling until CAC and churn are restructured."

    # 2. Payback Hurdle
    max_payback = 12.0 if business_model == "b2b_saas" else 6.0
    cond_payback = 18.0 if business_model == "b2b_saas" else 10.0

    if payback_months <= max_payback:
        payback_status = "PASS"
        payback_comment = f"Payback period of {payback_months} months meets the <={max_payback} months capital liquidity standard."
    elif payback_months <= cond_payback:
        payback_status = "CONDITIONAL"
        payback_comment = f"Payback period of {payback_months} months is extended (tolerance max {cond_payback}m). Working capital strain risk."
    else:
        payback_status = "FAIL"
        payback_comment = f"Payback period of {payback_months} months exceeds {cond_payback} months. Extreme runway drain."

    # 3. Magic Number Hurdle (if applicable)
    magic_status = "N/A"
    magic_comment = "Not applicable for this model."
    if magic_number is not None:
        if magic_number >= 1.0:
            magic_status = "PASS"
            magic_comment = f"Magic Number of {magic_number} indicates top-decile sales efficiency. Scale GTM spend."
        elif magic_number >= 0.75:
            magic_status = "PASS"
            magic_comment = f"Magic Number of {magic_number} meets standard healthy efficiency hurdle (0.75 - 1.0)."
        elif magic_number >= 0.5:
            magic_status = "CONDITIONAL"
            magic_comment = f"Magic Number of {magic_number} is sluggish (0.5 - 0.75). Optimize sales cycles and lead qualification."
        else:
            magic_status = "FAIL"
            magic_comment = f"Magic Number of {magic_number} is value-destroying (<0.5). GTM engine has severe leakage."

    # Overall Audit Verdict
    statuses = [ltv_cac_status, payback_status]
    if magic_number is not None and magic_status != "N/A":
        statuses.append(magic_status)

    if "FAIL" in statuses:
        overall_verdict = "REJECTED (Structural Deficit Identified)"
    elif "CONDITIONAL" in statuses:
        overall_verdict = "CONDITIONAL PASS (Optimization Required Prior to Scale)"
    else:
        overall_verdict = "APPROVED (World-Class Unit Economics)"

    return {
        "overall_verdict": overall_verdict,
        "ltv_cac_evaluation": {"status": ltv_cac_status, "comment": ltv_cac_comment},
        "payback_evaluation": {"status": payback_status, "comment": payback_comment},
        "magic_number_evaluation": {"status": magic_status, "comment": magic_comment},
    }


def analyze_model(data):
    """
    Master function: Executes complete quantitative marketing & commercial evaluation.
    """
    model_type = data.get("business_model", "b2b_saas")
    ue = data.get("unit_economics", {})

    arpu = ue.get("arpu_monthly", 0.0)
    gm = ue.get("gross_margin_pct", 0.80)
    churn = ue.get("monthly_logo_churn", 0.02)
    exp = ue.get("monthly_expansion_rate", 0.0)
    sm_monthly = ue.get("sales_and_marketing_monthly", 0.0)
    new_cust = ue.get("new_customers_monthly", 0)
    paid_spend = ue.get("paid_ad_spend_monthly")
    paid_cust = ue.get("paid_customers_monthly")

    # 1. CAC & LTV
    cac_res = calculate_cac(sm_monthly, new_cust, paid_spend, paid_cust)
    if cac_res["blended_cac"] == 0.0 and ("blended_cac" in ue or "cac" in ue):
        direct_cac = float(ue.get("blended_cac") or ue.get("cac", 0.0))
        cac_res["blended_cac"] = round(direct_cac, 2)
        if new_cust > 0 and sm_monthly <= 0.0:
            cac_res["sm_spend"] = round(direct_cac * new_cust, 2)
    ltv_res = calculate_ltv(arpu, gm, churn, exp)

    blended_cac = cac_res["blended_cac"]
    expansion_ltv = ltv_res["expansion_ltv"]
    traditional_ltv = ltv_res["traditional_ltv"]

    ltv_cac_ratio = round(expansion_ltv / blended_cac, 2) if blended_cac > 0 else 0.0
    trad_ltv_cac = round(traditional_ltv / blended_cac, 2) if blended_cac > 0 else 0.0

    # 2. Payback
    payback = calculate_payback_months(blended_cac, arpu, gm)

    # 3. Magic Number
    magic_num = None
    if "prior_quarter_sm_spend" in ue and "prior_quarter_revenue" in ue and "current_quarter_revenue" in ue:
        magic_num = calculate_magic_number(
            ue["prior_quarter_revenue"],
            ue["current_quarter_revenue"],
            ue["prior_quarter_sm_spend"]
        )

    # 4. Retention metrics
    retention_metrics = calculate_retention_metrics(churn, exp)

    # 5. Gate Hurdle Evaluation
    audit_scorecard = evaluate_gate_hurdles(ltv_cac_ratio, payback, magic_num, model_type)

    # 6. Channels & Media Saturation
    channel_results = []
    raw_channels = data.get("channels", [])
    for ch in raw_channels:
        spend = ch.get("current_spend", 0.0)
        max_out = ch.get("max_output", 100.0)
        half_sat = ch.get("half_sat_spend", spend * 0.8)
        shape_n = ch.get("shape_n", 1.5)

        sat_metrics = calculate_hill_saturation(spend, max_out, half_sat, shape_n)

        # Spend sensitivity curve (50% to 200%)
        spend_tiers = []
        for mult in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
            t_spend = spend * mult
            t_res = calculate_hill_saturation(t_spend, max_out, half_sat, shape_n)
            spend_tiers.append({
                "multiplier": mult,
                "spend": t_res["spend"],
                "response": t_res["response"],
                "marginal_cac": t_res["marginal_cac"],
                "saturation_pct": t_res["saturation_pct"]
            })

        channel_results.append({
            "name": ch.get("name", "Channel"),
            "output_unit": ch.get("output_unit", "Outputs"),
            "current_spend": spend,
            "max_output": max_out,
            "half_sat_spend": half_sat,
            "shape_n": shape_n,
            "current_metrics": sat_metrics,
            "spend_tiers": spend_tiers
        })

    # 7. Cohort Trajectory
    cohort_curve = data.get("cohort_retention_curve")
    initial_cohort = 1000 if model_type == "b2c_d2c" else 100
    cohort_sim = simulate_cohort_trajectory(
        initial_cohort,
        arpu,
        gm,
        churn,
        exp,
        custom_curve=cohort_curve,
        horizon_months=24,
        blended_cac=blended_cac
    )

    # 8. Scenario Analysis
    scenarios = run_scenarios(data)

    return {
        "company_name": data.get("company_name", "Commercial Client"),
        "business_model": model_type,
        "currency": data.get("currency", "USD"),
        "cac": cac_res,
        "ltv": ltv_res,
        "ltv_cac_ratio": ltv_cac_ratio,
        "traditional_ltv_cac_ratio": trad_ltv_cac,
        "payback_months": payback,
        "magic_number": magic_num,
        "retention_metrics": retention_metrics,
        "audit_scorecard": audit_scorecard,
        "channels": channel_results,
        "cohort_simulation": cohort_sim,
        "scenarios": scenarios,
        "ice_experiments": data.get("ice_experiments", [])
    }


def run_tests():
    """Built-in deterministic test suite verifying math and edge cases."""
    print("================================================================")
    print(" Running Quantitative Marketing Calculator Test Suite")
    print("================================================================")

    # Test 1: CAC
    cac_test = calculate_cac(100000, 20, 75000, 15)
    assert cac_test["blended_cac"] == 5000.0, f"Expected 5000.0, got {cac_test['blended_cac']}"
    assert cac_test["paid_cac"] == 5000.0, f"Expected 5000.0, got {cac_test['paid_cac']}"
    print("[PASS] Test 1: CAC calculation verified")

    # Test 2: LTV and Payback
    # ARPU = 2000, GM = 80%, Monthly Churn = 2% (0.02)
    # Monthly GP = 1600. Lifespan = 50 months. Traditional LTV = 80,000
    ltv_test = calculate_ltv(2000, 0.80, 0.02, 0.0)
    assert ltv_test["monthly_gross_profit"] == 1600.0, f"Expected 1600.0, got {ltv_test['monthly_gross_profit']}"
    assert ltv_test["traditional_ltv"] == 80000.0, f"Expected 80000.0, got {ltv_test['traditional_ltv']}"
    assert ltv_test["traditional_lifespan_months"] == 50.0, f"Expected 50.0, got {ltv_test['traditional_lifespan_months']}"

    payback_test = calculate_payback_months(8000.0, 2000, 0.80)
    assert payback_test == 5.0, f"Expected 5.0 months, got {payback_test}"
    print("[PASS] Test 2: LTV and Payback calculation verified")

    # Test 3: Expansion LTV and Negative Net Churn Compounding
    # Churn = 0.01, Expansion = 0.02 -> Net Churn = -0.01
    # Customer lifespan T = 100 months. With 1% monthly net compounding,
    # expansion LTV must be strictly greater than traditional LTV ($160,000).
    ltv_exp = calculate_ltv(2000, 0.80, 0.01, 0.02)
    assert ltv_exp["traditional_ltv"] == 160000.0
    assert ltv_exp["expansion_ltv"] > ltv_exp["traditional_ltv"], f"Expansion LTV {ltv_exp['expansion_ltv']} must exceed traditional {ltv_exp['traditional_ltv']}"
    assert ltv_exp["expansion_lifespan_months"] > ltv_exp["traditional_lifespan_months"]
    print("[PASS] Test 3: Expansion LTV compounding & economic superiority verified")

    # Test 4: Magic Number
    # Revenue_Q = 3.5M, Revenue_Q-1 = 2.8M, Diff = 0.7M * 4 = 2.8M ARR. Spend = 0.7M. Magic = 4.0
    magic_test = calculate_magic_number(2800000, 3500000, 700000)
    assert magic_test == 4.0, f"Expected 4.0, got {magic_test}"
    print("[PASS] Test 4: SaaS Magic Number calculation verified")

    # Test 5: Hill Saturation Function
    # S = 50000, K = 100, S50 = 50000, n = 1.0 -> At half-sat spend, Response must be 50.0 (50%)
    hill_test = calculate_hill_saturation(50000, 100, 50000, 1.0)
    assert hill_test["response"] == 50.0, f"Expected 50.0, got {hill_test['response']}"
    assert hill_test["saturation_pct"] == 50.0, f"Expected 50.0%, got {hill_test['saturation_pct']}"
    assert hill_test["marginal_cac"] is not None
    print("[PASS] Test 5: Hill Saturation half-spend boundary verified")

    # Test 6: Gate Hurdle Evaluation
    scorecard_pass = evaluate_gate_hurdles(4.2, 8.5, 1.2, "b2b_saas")
    assert scorecard_pass["overall_verdict"] == "APPROVED (World-Class Unit Economics)"
    scorecard_fail = evaluate_gate_hurdles(1.1, 24.0, 0.3, "b2b_saas")
    assert "REJECTED" in scorecard_fail["overall_verdict"]
    print("[PASS] Test 6: Gate Hurdle evaluations verified")

    # Test 7: Full Model Analysis with Sample Inputs
    sample_path = os.path.join(os.path.dirname(__file__), "..", "templates", "sample_inputs.json")
    if os.path.exists(sample_path):
        with open(sample_path, "r") as f:
            raw_data = json.load(f)
        b2b_result = analyze_model(raw_data["b2b_saas"])
        assert b2b_result["ltv_cac_ratio"] > 0
        assert len(b2b_result["channels"]) == 4
        assert len(b2b_result["cohort_simulation"]["trajectory"]) == 25
        assert b2b_result["ltv"]["expansion_ltv"] >= b2b_result["ltv"]["traditional_ltv"], "B2B Expansion LTV must be >= Traditional LTV"
        print("[PASS] Test 7: Integration analysis on b2b_saas sample verified")

        b2c_result = analyze_model(raw_data["b2c_d2c"])
        assert b2c_result["ltv_cac_ratio"] > 0
        assert len(b2c_result["channels"]) == 4
        # Test 8: Cohort decay continuity assertion for B2C
        b2c_traj = b2c_result["cohort_simulation"]["trajectory"]
        assert b2c_traj[13]["retention_pct"] <= b2c_traj[12]["retention_pct"], f"Month 13 ({b2c_traj[13]['retention_pct']}%) must not jump above Month 12 ({b2c_traj[12]['retention_pct']}%)"
        print("[PASS] Test 8: Integration analysis on b2c_d2c sample verified")

    # Test 9: Cohort retention continuity regression test
    c_curve = [1.0, 0.50, 0.40, 0.30]  # ends at month 3 with 30%
    sim_res = simulate_cohort_trajectory(100, 100, 0.8, 0.10, 0.0, custom_curve=c_curve, horizon_months=6)
    sim_traj = sim_res["trajectory"]
    for idx in range(1, len(sim_traj)):
        assert sim_traj[idx]["retention_rate"] <= sim_traj[idx - 1]["retention_rate"], f"Discontinuity detected at month {idx}: {sim_traj[idx]['retention_rate']} > {sim_traj[idx-1]['retention_rate']}"
    print("[PASS] Test 9: Cohort retention monotonic continuity verified")

    # Test 10: Direct CAC fallback
    direct_cac_model = {
        "company_name": "Direct CAC Corp",
        "business_model": "b2b_saas",
        "unit_economics": {
            "blended_cac": 4500,
            "arpu_monthly": 1500,
            "gross_margin_pct": 0.80,
            "monthly_logo_churn": 0.02
        }
    }
    direct_res = analyze_model(direct_cac_model)
    assert direct_res["cac"]["blended_cac"] == 4500.0, f"Expected 4500, got {direct_res['cac']['blended_cac']}"
    assert direct_res["payback_months"] == round(4500.0 / (1500 * 0.80), 1)
    print("[PASS] Test 10: Direct CAC fallback verified")

    # Test 11: Hill saturation small marginal response sensitivity
    # Low response rate (e.g. 0.000005) must still calculate valid marginal CAC
    hill_small = calculate_hill_saturation(2000000, 10, 500000, 1.2)
    assert hill_small["marginal_response"] > 0
    assert hill_small["marginal_cac"] is not None
    print("[PASS] Test 11: Hill saturation high-spend sensitivity verified")

    # Test 12: Sub-linear Hill shape parameter (n < 1.0) and non-positive n boundary safety
    hill_sublinear = calculate_hill_saturation(50000, 100, 50000, 0.75)
    assert hill_sublinear["response"] == 50.0, f"Expected 50.0, got {hill_sublinear['response']}"
    assert hill_sublinear["marginal_response"] > 0, "Marginal response for n=0.75 must be positive"
    assert hill_sublinear["marginal_cac"] is not None, "Marginal CAC must not be None"
    # Non-positive n must return safely without error or negative derivative
    hill_zero_n = calculate_hill_saturation(50000, 100, 50000, 0.0)
    assert hill_zero_n["response"] == 0.0
    assert hill_zero_n["marginal_cac"] is None
    hill_neg_n = calculate_hill_saturation(50000, 100, 50000, -1.0)
    assert hill_neg_n["response"] == 0.0
    assert hill_neg_n["marginal_cac"] is None
    print("[PASS] Test 12: Sub-linear Hill saturation (n < 1.0) and non-positive boundary safety verified")

    # Test 13: Percentage input auto-normalization robustness
    ltv_dec = calculate_ltv(2500, 0.80, 0.02, 0.015)
    ltv_whole = calculate_ltv(2500, 80.0, 2.0, 1.5)
    assert ltv_dec["traditional_ltv"] == ltv_whole["traditional_ltv"], f"Mismatch: {ltv_dec['traditional_ltv']} != {ltv_whole['traditional_ltv']}"
    assert ltv_dec["expansion_ltv"] == ltv_whole["expansion_ltv"], f"Mismatch: {ltv_dec['expansion_ltv']} != {ltv_whole['expansion_ltv']}"
    pb_dec = calculate_payback_months(10000, 2500, 0.80)
    pb_whole = calculate_payback_months(10000, 2500, 80.0)
    assert pb_dec == pb_whole, f"Payback mismatch: {pb_dec} != {pb_whole}"
    ret_dec = calculate_retention_metrics(0.02, 0.015)
    ret_whole = calculate_retention_metrics(2.0, 1.5)
    assert ret_dec["annualized_nrr_pct"] == ret_whole["annualized_nrr_pct"]
    print("[PASS] Test 13: Percentage input auto-normalization robustness verified")

    print("\n>>> ALL CALCULATOR TESTS PASSED SUCCESSFULLY! <<<\n")


def main():
    parser = argparse.ArgumentParser(description="Deterministic Marketing & Unit Economics Calculator")
    parser.add_argument("--input", "-i", help="Path to input JSON file")
    parser.add_argument("--profile", "-p", default="b2b_saas", help="Profile key within JSON (e.g. b2b_saas or b2c_d2c)")
    parser.add_argument("--output", "-o", help="Path to write calculation results JSON")
    parser.add_argument("--test", action="store_true", help="Run internal test suite and exit")
    parser.add_argument("--print-summary", action="store_true", help="Print executive summary to stdout")

    args = parser.parse_args()

    if args.test:
        run_tests()
        sys.exit(0)

    if not args.input:
        # Fall back to template sample if available
        default_sample = os.path.join(os.path.dirname(__file__), "..", "templates", "sample_inputs.json")
        if os.path.exists(default_sample):
            args.input = default_sample
        else:
            parser.print_help()
            sys.exit(1)

    with open(args.input, "r") as f:
        raw_json = json.load(f)

    # Determine data block
    if args.profile in raw_json:
        data_block = raw_json[args.profile]
    elif "unit_economics" in raw_json:
        data_block = raw_json
    else:
        # Take first available dict
        first_key = next(iter(raw_json.keys()))
        data_block = raw_json[first_key]

    results = analyze_model(data_block)

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"[SUCCESS] Calculated unit economics written to: {args.output}")

    if args.print_summary or not args.output:
        print("\n==================================================================")
        print(f" COMMERCIAL STRATEGY UNIT ECONOMICS: {results['company_name']}")
        print(f" Model: {results['business_model'].upper()} | Status: {results['audit_scorecard']['overall_verdict']}")
        print("==================================================================")
        print(f" Blended CAC:          ${results['cac']['blended_cac']:,.2f}")
        print(f" Expansion LTV:        ${results['ltv']['expansion_ltv']:,.2f}")
        print(f" Traditional LTV:      ${results['ltv']['traditional_ltv']:,.2f}")
        print(f" LTV / CAC Ratio:      {results['ltv_cac_ratio']}x  [{results['audit_scorecard']['ltv_cac_evaluation']['status']}]")
        print(f" Payback Period:       {results['payback_months']} Months [{results['audit_scorecard']['payback_evaluation']['status']}]")
        if results['magic_number'] is not None:
            print(f" SaaS Magic Number:    {results['magic_number']} [{results['audit_scorecard']['magic_number_evaluation']['status']}]")
        print(f" Annualized NRR:       {results['retention_metrics']['annualized_nrr_pct']}%")
        print(f" Annualized GRR:       {results['retention_metrics']['annualized_grr_pct']}%")
        print("==================================================================\n")


if __name__ == "__main__":
    main()
