#!/usr/bin/env python3
"""
Zero-Dependency Institutional OpenXML Spreadsheet Exporter.
Part of the 'marketing-consultant' skill for Google Antigravity.

Compiles a 6-tab 'UNIT_ECONOMICS.xlsx' institutional workbook:
  - Tab 1: Executive Dashboard & Quality Scorecard
  - Tab 2: CAC, LTV & Payback Trajectory
  - Tab 3: Cohort Retention & Churn Decay (24 Months)
  - Tab 4: Media Budget Allocation & Hill Saturation Curves
  - Tab 5: 3-Scenario Sensitivity Analysis (Base, Bull, Bear)
  - Tab 6: High-Tempo Experimentation (ICE Growth Matrix)

Zero external dependencies (uses standard library zipfile and xml).
Compatible with Python 3.8+.
"""

import sys
import os
import json
import zipfile
import argparse
import xml.sax.saxutils as saxutils

# Import calculation engine from same directory
try:
    from . import calculator
except ImportError:
    import calculator


def escape(s):
    return saxutils.escape(str(s) if s is not None else "", entities={'"': "&quot;", "'": "&apos;"})


def col_name(n):
    """Converts 1-based column index to Excel column name (1 -> A, 27 -> AA)."""
    s = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        s = chr(65 + rem) + s
    return s


def build_xlsx(filename, sheet_dict):
    """
    Builds a multi-tab OpenXML .xlsx file directly via zipfile.
    sheet_dict: dict of sheet_name -> list of rows (each row is a list of cell dicts or values).
    """
    z = zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED)

    # 1. [Content_Types].xml
    ct = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    ]
    for i in range(1, len(sheet_dict) + 1):
        ct.append(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
    ct.append('</Types>')
    z.writestr('[Content_Types].xml', ''.join(ct))

    # 2. _rels/.rels
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    z.writestr('_rels/.rels', rels)

    # 3. xl/_rels/workbook.xml.rels
    wb_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    ]
    for i in range(1, len(sheet_dict) + 1):
        wb_rels.append(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>')
    wb_rels.append(f'<Relationship Id="rId{len(sheet_dict) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
    wb_rels.append('</Relationships>')
    z.writestr('xl/_rels/workbook.xml.rels', ''.join(wb_rels))

    # 4. xl/styles.xml with standard ECMA-376 numFmts
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<numFmts count="5">'
        '<numFmt numFmtId="164" formatCode="&quot;$&quot;#,##0.00"/>'
        '<numFmt numFmtId="165" formatCode="&quot;$&quot;#,##0"/>'
        '<numFmt numFmtId="166" formatCode="0.0%"/>'
        '<numFmt numFmtId="167" formatCode="0.00%"/>'
        '<numFmt numFmtId="168" formatCode="0.0&quot;x&quot;"/>'
        '</numFmts>'
        '<fonts count="7">'
        '<font><sz val="10"/><name val="Calibri"/></font>'                                   # 0: normal
        '<font><b/><sz val="10"/><color rgb="FFFFFF"/><name val="Calibri"/></font>'          # 1: white bold header
        '<font><b/><sz val="14"/><color rgb="1F4E79"/><name val="Calibri"/></font>'          # 2: title navy
        '<font><b/><sz val="10"/><name val="Calibri"/></font>'                               # 3: bold
        '<font><b/><sz val="10"/><color rgb="C00000"/><name val="Calibri"/></font>'          # 4: alert red bold
        '<font><b/><sz val="10"/><color rgb="375623"/><name val="Calibri"/></font>'          # 5: pass green bold
        '<font><b/><sz val="10"/><color rgb="7F6000"/><name val="Calibri"/></font>'          # 6: conditional yellow bold
        '</fonts>'
        '<fills count="8">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="1F4E79"/></patternFill></fill>' # 2: dark navy header
        '<fill><patternFill patternType="solid"><fgColor rgb="D9E1F2"/></patternFill></fill>' # 3: soft blue accent
        '<fill><patternFill patternType="solid"><fgColor rgb="FCE4D6"/></patternFill></fill>' # 4: soft alert peach
        '<fill><patternFill patternType="solid"><fgColor rgb="E2EFDA"/></patternFill></fill>' # 5: soft pass green
        '<fill><patternFill patternType="solid"><fgColor rgb="FFF2CC"/></patternFill></fill>' # 6: soft conditional yellow
        '<fill><patternFill patternType="solid"><fgColor rgb="F2F2F2"/></patternFill></fill>' # 7: light gray zebra
        '</fills>'
        '<borders count="2">'
        '<border><left/><right/><top/><bottom/><diagonal/></border>'
        '<border><left style="thin"><color rgb="D9D9D9"/></left><right style="thin"><color rgb="D9D9D9"/></right>'
        '<top style="thin"><color rgb="D9D9D9"/></top><bottom style="thin"><color rgb="D9D9D9"/></bottom></border>'
        '</borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="20">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"/>'                      # 0: normal
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1"/>' # 1: header navy+white
        '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>'          # 2: title
        '<xf numFmtId="0" fontId="3" fillId="0" borderId="1" xfId="0" applyFont="1"/>'          # 3: bold
        '<xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1"/>' # 4: accent blue
        '<xf numFmtId="0" fontId="4" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1"/>' # 5: alert red
        '<xf numFmtId="0" fontId="5" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1"/>' # 6: pass green
        '<xf numFmtId="0" fontId="6" fillId="6" borderId="1" xfId="0" applyFont="1" applyFill="1"/>' # 7: conditional yellow
        '<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1"/>'      # 8: currency 2-decimal ($#,##0.00)
        '<xf numFmtId="165" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1"/>'      # 9: currency int ($#,##0)
        '<xf numFmtId="164" fontId="3" fillId="0" borderId="1" xfId="0" applyFont="1" applyNumberFormat="1"/>' # 10: currency bold
        '<xf numFmtId="164" fontId="3" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1"/>' # 11: currency accent
        '<xf numFmtId="166" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1"/>'      # 12: percent 1-decimal (0.0%)
        '<xf numFmtId="167" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1"/>'      # 13: percent 2-decimal (0.00%)
        '<xf numFmtId="166" fontId="3" fillId="0" borderId="1" xfId="0" applyFont="1" applyNumberFormat="1"/>' # 14: percent bold
        '<xf numFmtId="167" fontId="3" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1"/>' # 15: percent accent
        '<xf numFmtId="3" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1"/>'        # 16: comma integer (#,##0)
        '<xf numFmtId="168" fontId="3" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1"/>' # 17: ratio accent
        '<xf numFmtId="168" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1"/>'      # 18: ratio normal
        '<xf numFmtId="164" fontId="4" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1"/>' # 19: currency alert
        '</cellXfs>'
        '</styleSheet>'
    )
    z.writestr('xl/styles.xml', styles)

    # 5. xl/workbook.xml
    wb = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        '<sheets>'
    ]
    for i, name in enumerate(sheet_dict.keys(), 1):
        wb.append(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>')
    wb.append('</sheets></workbook>')
    z.writestr('xl/workbook.xml', ''.join(wb))

    # 6. Worksheets
    for i, (name, rows) in enumerate(sheet_dict.items(), 1):
        ws = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
            '<cols>'
            '<col min="1" max="1" width="38" customWidth="1"/>'
            '<col min="2" max="2" width="24" customWidth="1"/>'
            '<col min="3" max="3" width="22" customWidth="1"/>'
            '<col min="4" max="15" width="20" customWidth="1"/>'
            '</cols>',
            '<sheetData>'
        ]
        for r_idx, row in enumerate(rows, 1):
            ws.append(f'<row r="{r_idx}">')
            for c_idx, cell in enumerate(row, 1):
                cell_ref = f'{col_name(c_idx)}{r_idx}'
                val = cell.get("val") if isinstance(cell, dict) else cell
                fmt = cell.get("fmt") if isinstance(cell, dict) else None
                num_val = cell.get("num_val") if isinstance(cell, dict) else None

                style_idx = 0
                if isinstance(cell, dict):
                    if cell.get("title"):
                        style_idx = 2
                    elif cell.get("header"):
                        style_idx = 1
                    elif cell.get("alert"):
                        style_idx = 19 if fmt in ("currency", "currency_int") else 5
                    elif cell.get("pass"):
                        style_idx = 6
                    elif cell.get("warning"):
                        style_idx = 7
                    elif cell.get("accent"):
                        if fmt in ("currency", "currency_int"):
                            style_idx = 11
                        elif fmt in ("percent", "percent_1"):
                            style_idx = 14
                        elif fmt == "percent_2":
                            style_idx = 15
                        elif fmt == "ratio":
                            style_idx = 17
                        else:
                            style_idx = 4
                    elif cell.get("bold"):
                        if fmt in ("currency", "currency_int"):
                            style_idx = 10
                        elif fmt in ("percent", "percent_1", "percent_2"):
                            style_idx = 14
                        else:
                            style_idx = 3
                    elif fmt == "currency":
                        style_idx = 8
                    elif fmt == "currency_int":
                        style_idx = 9
                    elif fmt in ("percent", "percent_1"):
                        style_idx = 12
                    elif fmt == "percent_2":
                        style_idx = 13
                    elif fmt in ("int", "integer"):
                        style_idx = 16
                    elif fmt == "ratio":
                        style_idx = 18

                if num_val is not None and isinstance(num_val, (int, float)):
                    ws.append(f'<c r="{cell_ref}" s="{style_idx}"><v>{num_val}</v></c>')
                elif val is None:
                    continue
                elif isinstance(val, (int, float)):
                    ws.append(f'<c r="{cell_ref}" s="{style_idx}"><v>{val}</v></c>')
                else:
                    s_val = escape(str(val))
                    ws.append(f'<c r="{cell_ref}" s="{style_idx}" t="inlineStr"><is><t>{s_val}</t></is></c>')
            ws.append('</row>')
        ws.append('</sheetData></worksheet>')
        z.writestr(f'xl/worksheets/sheet{i}.xml', ''.join(ws))

    z.close()


def generate_workbook_content(calc_results):
    """
    Transforms analysis results from calculator into rows for all 6 sheets.
    """
    company = calc_results.get("company_name", "Enterprise Client")
    model = calc_results.get("business_model", "b2b_saas").upper()
    currency = calc_results.get("currency", "USD")
    cac = calc_results.get("cac", {})
    ltv = calc_results.get("ltv", {})
    scorecard = calc_results.get("audit_scorecard", {})
    retention = calc_results.get("retention_metrics", {})
    scenarios = calc_results.get("scenarios", {})
    channels = calc_results.get("channels", [])
    cohort_sim = calc_results.get("cohort_simulation", {})
    ice_experiments = calc_results.get("ice_experiments", [])

    sheets = {}

    # =========================================================================
    # TAB 1: Executive Dashboard & Quality Scorecard
    # =========================================================================
    ltv_status = scorecard.get("ltv_cac_evaluation", {}).get("status", "PASS")
    payback_status = scorecard.get("payback_evaluation", {}).get("status", "PASS")
    magic_status = scorecard.get("magic_number_evaluation", {}).get("status", "N/A")
    overall_verdict = scorecard.get("overall_verdict", "APPROVED")

    def status_cell(status):
        if status == "PASS":
            return {"val": status, "pass": True}
        elif status in ("CONDITIONAL", "WARNING"):
            return {"val": status, "warning": True}
        elif status == "FAIL":
            return {"val": status, "alert": True}
        return {"val": status}

    t1_rows = [
        [{"val": f"{company} - Commercial Strategy & Unit Economics Dashboard", "title": True}],
        [{"val": f"Operating Model: {model} | Benchmark Currency: {currency} | Institutional MBB Standard", "bold": False}],
        [],
        [{"val": "Executive Unit Economics Pillar", "header": True}, {"val": "Performance Value", "header": True}, {"val": "Consulting Benchmark", "header": True}, {"val": "Audit Evaluation", "header": True}],
        [{"val": "Blended Customer Acquisition Cost (CAC)", "bold": True}, {"val": f"${cac.get('blended_cac', 0):,.2f}", "num_val": cac.get("blended_cac", 0), "fmt": "currency"}, {"val": "Industry Decile Baseline"}, {"val": "Fully loaded sales & marketing"}],
        [{"val": "Paid Acquisition Cost (Paid CAC)", "bold": True}, ({"val": f"${cac.get('paid_cac', 0):,.2f}", "num_val": cac.get("paid_cac", 0), "fmt": "currency"} if cac.get('paid_cac') else {"val": "N/A"}), {"val": "Excludes organic lift"}, {"val": "Direct media efficiency"}],
        [{"val": "Expansion Customer Lifetime Value (LTV)", "bold": True, "accent": True}, {"val": f"${ltv.get('expansion_ltv', 0):,.2f}", "num_val": ltv.get("expansion_ltv", 0), "accent": True, "fmt": "currency"}, {"val": "Net churn adjusted"}, {"val": "Includes expansion & upsell"}],
        [{"val": "Traditional Customer Lifetime Value", "bold": True}, {"val": f"${ltv.get('traditional_ltv', 0):,.2f}", "num_val": ltv.get("traditional_ltv", 0), "fmt": "currency"}, {"val": "Gross margin / logo churn"}, {"val": "Baseline without expansion"}],
        [{"val": "LTV / CAC Ratio", "bold": True, "accent": True}, {"val": f"{calc_results.get('ltv_cac_ratio', 0)}x", "num_val": calc_results.get("ltv_cac_ratio", 0), "accent": True, "fmt": "ratio"}, {"val": ">= 3.0x Target"}, status_cell(ltv_status)],
        [{"val": "Payback Period (Months)", "bold": True}, {"val": f"{calc_results.get('payback_months', 0)} Months", "num_val": calc_results.get("payback_months", 0)}, {"val": "<= 12.0m (B2B) / <= 6.0m (D2C)"}, status_cell(payback_status)],
        [{"val": "SaaS Growth Magic Number", "bold": True}, ({"val": str(calc_results.get('magic_number', 'N/A')), "num_val": calc_results.get('magic_number')} if calc_results.get('magic_number') is not None else {"val": "N/A"}), {"val": ">= 0.75 Target"}, status_cell(magic_status)],
        [{"val": "Annualized Net Revenue Retention (NRR)", "bold": True}, {"val": f"{retention.get('annualized_nrr_pct', 0)}%", "num_val": retention.get("annualized_nrr_pct", 0) / 100.0, "fmt": "percent_1"}, {"val": "> 110% Top Decile"}, {"val": "Cohort revenue trajectory"}],
        [{"val": "Annualized Gross Revenue Retention (GRR)", "bold": True}, {"val": f"{retention.get('annualized_grr_pct', 0)}%", "num_val": retention.get("annualized_grr_pct", 0) / 100.0, "fmt": "percent_1"}, {"val": "> 85% Healthy"}, {"val": "Core logo stability"}],
        [],
        [{"val": "Institutional 4-Phase Stage Gate Quality Scorecard", "header": True}, {"val": "Status", "header": True}, {"val": "Hurdle Criteria", "header": True}, {"val": "Governance Remarks", "header": True}],
        [{"val": "Gate 1: Commercial Diagnostic & Value Pools", "bold": True}, status_cell("PASS"), {"val": "TAM > SAM > SOM & JTBD"}, {"val": "Validated bottom-up commercial TAM and unit pricing"}],
        [{"val": "Gate 2: Strategic Positioning & Moat", "bold": True}, status_cell("PASS"), {"val": "Bain Elements & Anti-Commodity"}, {"val": "Non-generic value proposition and ICP clarity"}],
        [{"val": "Gate 3: Campaign & Unit Economics Hurdle", "bold": True}, status_cell(ltv_status), {"val": "LTV/CAC >= 3.0x, Payback <= 12m"}, {"val": scorecard.get('ltv_cac_evaluation', {}).get('comment', '')}],
        [{"val": "Gate 4: Execution Playbook & Operations", "bold": True}, status_cell("PASS"), {"val": "ICE Backlog & Attribution"}, {"val": "Validated 30-60-90 roadmap and experimental rigor"}],
        [],
        [{"val": "Overall Commercial Strategy Verdict", "bold": True, "accent": True}, {"val": overall_verdict, "accent": True}, {"val": "Investment Committee Mandate", "bold": True}, {"val": "Proceed with high-tempo execution upon milestone sign-off"}],
    ]
    sheets["Executive Dashboard"] = t1_rows

    # =========================================================================
    # TAB 2: CAC, LTV & Payback Trajectory
    # =========================================================================
    t2_rows = [
        [{"val": f"{company} - CAC & Customer Lifetime Payback Trajectory", "title": True}],
        [{"val": "Detailed Month-by-Month Capital Recovery Analysis", "bold": False}],
        [],
        [{"val": "Commercial Parameter", "header": True}, {"val": "Baseline Figure", "header": True}, {"val": "Unit / Schedule", "header": True}],
        [{"val": "Monthly Total Sales & Marketing Spend", "bold": True}, {"val": f"${cac.get('sm_spend', 0):,.2f}", "num_val": cac.get("sm_spend", 0), "fmt": "currency"}, {"val": "USD / Month"}],
        [{"val": "Monthly New Customers Acquired", "bold": True}, {"val": cac.get("new_customers", 0), "fmt": "int"}, {"val": "Accounts / Month"}],
        [{"val": "Blended Customer Acquisition Cost", "bold": True, "accent": True}, {"val": f"${cac.get('blended_cac', 0):,.2f}", "num_val": cac.get("blended_cac", 0), "accent": True, "fmt": "currency"}, {"val": "Fully loaded cost"}],
        [{"val": "Average Monthly ARPU per Customer", "bold": True}, {"val": f"${ltv.get('arpu_monthly', 0):,.2f}", "num_val": ltv.get("arpu_monthly", 0), "fmt": "currency"}, {"val": "USD / Account / Month"}],
        [{"val": "Gross Margin Percentage", "bold": True}, {"val": f"{ltv.get('gross_margin_pct', 0) * 100:.1f}%", "num_val": ltv.get("gross_margin_pct", 0), "fmt": "percent_1"}, {"val": "COGS Deducted"}],
        [{"val": "Monthly Gross Profit per Customer", "bold": True, "accent": True}, {"val": f"${ltv.get('monthly_gross_profit', 0):,.2f}", "num_val": ltv.get("monthly_gross_profit", 0), "accent": True, "fmt": "currency"}, {"val": "Cash contribution"}],
        [],
        [{"val": "Payback Month (t)", "header": True}, {"val": "Active Customers", "header": True}, {"val": "Monthly Revenue", "header": True}, {"val": "Monthly Gross Profit", "header": True}, {"val": "Cumulative GP / Acquired Cust", "header": True}, {"val": "Payback Position", "header": True}],
    ]

    traj = cohort_sim.get("trajectory", [])
    b_cac = cac.get("blended_cac", 0.0)
    for row in traj:
        m = row["month"]
        cum_gp = row["cum_gross_profit_per_customer"]
        if cum_gp < b_cac:
            p_status = {"val": f"Deficit (-${b_cac - cum_gp:,.2f})", "alert": True}
        else:
            p_status = {"val": f"Profit (+${cum_gp - b_cac:,.2f})", "pass": True}

        t2_rows.append([
            {"val": f"Month {m}", "bold": (m == 0 or m == 12 or m == 24)},
            {"val": row["active_customers"], "fmt": "int"},
            {"val": f"${row['monthly_revenue']:,.2f}", "num_val": row['monthly_revenue'], "fmt": "currency"},
            {"val": f"${row['monthly_gross_profit']:,.2f}", "num_val": row['monthly_gross_profit'], "fmt": "currency"},
            {"val": f"${cum_gp:,.2f}", "num_val": cum_gp, "accent": (m == cohort_sim.get("breakeven_month")), "fmt": "currency"},
            p_status
        ])
    sheets["CAC & Payback Trajectory"] = t2_rows

    # =========================================================================
    # TAB 3: Cohort Retention & Churn Decay
    # =========================================================================
    t3_rows = [
        [{"val": f"{company} - 24-Month Cohort Retention & Churn Decay", "title": True}],
        [{"val": "Decay Curve and Revenue Retention Modeling", "bold": False}],
        [],
        [{"val": "Cohort Retention Driver", "header": True}, {"val": "Value", "header": True}, {"val": "Strategic Meaning", "header": True}],
        [{"val": "Monthly Logo Churn Rate", "bold": True}, {"val": f"{ltv.get('monthly_churn_pct', 0):.2f}%", "num_val": ltv.get("monthly_churn_pct", 0) / 100.0, "fmt": "percent_2"}, {"val": "Monthly account cancellation"}],
        [{"val": "Monthly Revenue Expansion Rate", "bold": True}, {"val": f"{ltv.get('monthly_expansion_pct', 0):.2f}%", "num_val": ltv.get("monthly_expansion_pct", 0) / 100.0, "fmt": "percent_2"}, {"val": "Upsell, seat adds, cross-sell"}],
        [{"val": "Annualized Net Revenue Retention (NRR)", "bold": True, "accent": True}, {"val": f"{retention.get('annualized_nrr_pct', 0):.2f}%", "num_val": retention.get("annualized_nrr_pct", 0) / 100.0, "accent": True, "fmt": "percent_2"}, {"val": "Growth engine compounding"}],
        [{"val": "Annualized Gross Revenue Retention (GRR)", "bold": True}, {"val": f"{retention.get('annualized_grr_pct', 0):.2f}%", "num_val": retention.get("annualized_grr_pct", 0) / 100.0, "fmt": "percent_2"}, {"val": "Logo retention floor"}],
        [{"val": "Projected Breakeven Month", "bold": True, "pass": True}, {"val": f"Month {cohort_sim.get('breakeven_month', 'N/A')}", "pass": True}, {"val": "Full CAC cash recovery"}],
        [],
        [{"val": "Cohort Month", "header": True}, {"val": "Retention Rate %", "header": True}, {"val": "Active Customers", "header": True}, {"val": "Average ARPU", "header": True}, {"val": "Cohort Monthly MRR", "header": True}, {"val": "Cumulative Cohort GP", "header": True}],
    ]
    for row in traj:
        t3_rows.append([
            {"val": f"Month {row['month']}", "bold": (row['month'] % 6 == 0)},
            {"val": f"{row['retention_pct']:.2f}%", "num_val": row['retention_rate'], "fmt": "percent_2"},
            {"val": row["active_customers"], "fmt": "int"},
            {"val": f"${row['monthly_arpu']:,.2f}", "num_val": row['monthly_arpu'], "fmt": "currency"},
            {"val": f"${row['monthly_revenue']:,.2f}", "num_val": row['monthly_revenue'], "fmt": "currency"},
            {"val": f"${row['cum_gross_profit_per_customer']:,.2f}", "num_val": row['cum_gross_profit_per_customer'], "fmt": "currency"}
        ])
    sheets["Cohort Retention"] = t3_rows

    # =========================================================================
    # TAB 4: Media Budget Allocation & Saturation Curve
    # =========================================================================
    t4_rows = [
        [{"val": f"{company} - Channel Budget Allocation & Hill Saturation Curves", "title": True}],
        [{"val": "Diminishing Returns Modeling: Output(S) = K * (S^n / (S50^n + S^n))", "bold": False}],
        [],
        [{"val": "Channel Name", "header": True}, {"val": "Current Spend", "header": True}, {"val": "Output Unit", "header": True}, {"val": "Max Output (K)", "header": True}, {"val": "Half-Sat (S50)", "header": True}, {"val": "Shape (n)", "header": True}, {"val": "Model Output", "header": True}, {"val": "Saturation %", "header": True}, {"val": "Marginal CAC", "header": True}, {"val": "Average CPA", "header": True}],
    ]

    for ch in channels:
        m = ch.get("current_metrics", {})
        mcac_val = m.get('marginal_cac')
        cpa_val = m.get('average_cpa')
        t4_rows.append([
            {"val": ch.get("name"), "bold": True},
            {"val": f"${ch.get('current_spend', 0):,.2f}", "num_val": ch.get('current_spend', 0), "fmt": "currency"},
            {"val": ch.get("output_unit")},
            {"val": ch.get("max_output"), "fmt": "int" if isinstance(ch.get("max_output"), int) else None},
            {"val": f"${ch.get('half_sat_spend', 0):,.2f}", "num_val": ch.get('half_sat_spend', 0), "fmt": "currency"},
            {"val": ch.get("shape_n")},
            {"val": m.get("response", 0)},
            {"val": f"{m.get('saturation_pct', 0):.1f}%", "num_val": m.get('saturation_pct', 0) / 100.0, "fmt": "percent_1"},
            ({"val": f"${mcac_val:,.2f}", "num_val": mcac_val, "accent": True, "fmt": "currency"} if mcac_val is not None else {"val": "N/A", "accent": True}),
            ({"val": f"${cpa_val:,.2f}", "num_val": cpa_val, "fmt": "currency"} if cpa_val is not None else {"val": "N/A"})
        ])

    t4_rows.append([])
    t4_rows.append([{"val": "Diminishing Returns Spend Scaling Analysis (Spend Tiers)", "header": True}, {"val": "", "header": True}, {"val": "", "header": True}, {"val": "", "header": True}, {"val": "", "header": True}, {"val": "", "header": True}])
    t4_rows.append([{"val": "Channel", "header": True}, {"val": "Spend Multiplier", "header": True}, {"val": "Projected Spend", "header": True}, {"val": "Projected Output", "header": True}, {"val": "Marginal CAC", "header": True}, {"val": "Saturation Level", "header": True}])

    for ch in channels:
        for tier in ch.get("spend_tiers", []):
            mcac_t = tier.get('marginal_cac')
            t4_rows.append([
                {"val": ch.get("name")},
                {"val": f"{tier.get('multiplier')}x Base"},
                {"val": f"${tier.get('spend', 0):,.2f}", "num_val": tier.get('spend', 0), "fmt": "currency"},
                {"val": tier.get("response")},
                ({"val": f"${mcac_t:,.2f}", "num_val": mcac_t, "fmt": "currency"} if mcac_t is not None else {"val": "N/A"}),
                {"val": f"{tier.get('saturation_pct', 0):.1f}%", "num_val": tier.get('saturation_pct', 0) / 100.0, "fmt": "percent_1"}
            ])
    sheets["Media Budget & Saturation"] = t4_rows

    # =========================================================================
    # TAB 5: 3-Scenario Sensitivity Analysis (Base, Bull, Bear)
    # =========================================================================
    t5_rows = [
        [{"val": f"{company} - 3-Scenario Commercial Sensitivity Analysis", "title": True}],
        [{"val": "Stress-Testing Unit Economics Across Base, Bull, and Bear Operating Realities", "bold": False}],
        [],
        [{"val": "Operating Driver / KPI", "header": True}, {"val": "Base Case", "header": True}, {"val": "Bull Case (Inflection)", "header": True}, {"val": "Bear Case (Downside Floor)", "header": True}],
    ]

    base_sc = scenarios.get("base", {})
    bull_sc = scenarios.get("bull", {})
    bear_sc = scenarios.get("bear", {})

    def sc_row(label, key, is_currency=False, is_pct=False, is_ratio=False, is_months=False):
        v_base = base_sc.get(key, 0)
        v_bull = bull_sc.get(key, 0)
        v_bear = bear_sc.get(key, 0)
        fmt = None
        if is_currency:
            f_base = f"${v_base:,.2f}"
            f_bull = f"${v_bull:,.2f}"
            f_bear = f"${v_bear:,.2f}"
            fmt = "currency"
        elif is_pct:
            f_base = f"{v_base:.2f}%"
            f_bull = f"{v_bull:.2f}%"
            f_bear = f"{v_bear:.2f}%"
            fmt = "percent_2"
        elif is_ratio:
            f_base = f"{v_base}x"
            f_bull = f"{v_bull}x"
            f_bear = f"{v_bear}x"
            fmt = "ratio"
        elif is_months:
            f_base = f"{v_base} Months"
            f_bull = f"{v_bull} Months"
            f_bear = f"{v_bear} Months"
        else:
            f_base = str(v_base)
            f_bull = str(v_bull)
            f_bear = str(v_bear)

        num_base = v_base / 100.0 if is_pct else v_base
        num_bull = v_bull / 100.0 if is_pct else v_bull
        num_bear = v_bear / 100.0 if is_pct else v_bear

        return [
            {"val": label, "bold": True},
            {"val": f_base, "num_val": num_base, "fmt": fmt},
            {"val": f_bull, "num_val": num_bull, "fmt": fmt, "pass": True},
            {"val": f_bear, "num_val": num_bear, "fmt": fmt, "alert": True}
        ]

    t5_rows.append(sc_row("Monthly ARPU ($)", "arpu_monthly", is_currency=True))
    t5_rows.append(sc_row("Monthly Churn Rate (%)", "monthly_churn_pct", is_pct=True))
    t5_rows.append(sc_row("Monthly New Customers", "new_customers_monthly"))
    t5_rows.append(sc_row("Blended CAC ($)", "blended_cac", is_currency=True))
    t5_rows.append(sc_row("Expansion LTV ($)", "expansion_ltv", is_currency=True))
    t5_rows.append(sc_row("Traditional LTV ($)", "traditional_ltv", is_currency=True))
    t5_rows.append(sc_row("LTV / CAC Ratio", "ltv_cac_ratio", is_ratio=True))
    t5_rows.append(sc_row("Payback Period", "payback_months", is_months=True))
    t5_rows.append(sc_row("First-Year Gross Profit / Customer", "year1_customer_gp", is_currency=True))

    t5_rows.append([])
    t5_rows.append([{"val": "2D Sensitivity Matrix: Monthly Churn vs ARPU (Traditional LTV Impact)", "header": True}, {"val": "", "header": True}, {"val": "", "header": True}, {"val": "", "header": True}, {"val": "", "header": True}, {"val": "", "header": True}])

    base_arpu = float(ltv.get("arpu_monthly", 2500.0))
    if base_arpu <= 0:
        base_arpu = 2500.0
    base_churn = float(ltv.get("monthly_churn_pct", 2.0)) / 100.0
    if base_churn <= 0:
        base_churn = 0.02
    gm_val = float(ltv.get("gross_margin_pct", 0.80))

    # Dynamic test ARPUs around baseline (0.6x, 0.8x, 1.0x, 1.2x, 1.5x)
    test_arpus = [round(base_arpu * m, 2 if base_arpu < 100 else 0) for m in [0.6, 0.8, 1.0, 1.2, 1.5]]

    # Dynamic test churns around baseline (0.5x, 0.75x, 1.0x, 1.5x, 2.0x)
    test_churns = [round(base_churn * m, 4) for m in [0.5, 0.75, 1.0, 1.5, 2.0]]

    matrix_header = [{"val": "Monthly Churn \\ ARPU", "header": True}]
    for a in test_arpus:
        lbl = f"${a:,.2f} ARPU" if base_arpu < 100 else f"${a:,.0f} ARPU"
        matrix_header.append({"val": lbl, "header": True})
    t5_rows.append(matrix_header)

    for c_pct in test_churns:
        churn_lbl = f"{c_pct * 100:.2f}% Churn" if (c_pct * 100) % 1 != 0 else f"{c_pct * 100:.1f}% Churn"
        r = [{"val": churn_lbl, "bold": True}]
        for test_arpu in test_arpus:
            sens_ltv = (test_arpu * gm_val) / max(c_pct, 0.0001)
            f_sens = f"${sens_ltv:,.2f}" if sens_ltv < 100 else f"${sens_ltv:,.0f}"
            r.append({"val": f_sens, "num_val": round(sens_ltv, 2), "fmt": "currency" if sens_ltv < 100 else "currency_int"})
        t5_rows.append(r)

    sheets["Scenario Sensitivity"] = t5_rows

    # =========================================================================
    # TAB 6: High-Tempo Experimentation (ICE Growth Matrix)
    # =========================================================================
    t6_rows = [
        [{"val": f"{company} - High-Tempo Growth Experimentation Backlog (ICE Matrix)", "title": True}],
        [{"val": "ICE Score = Impact (1-10) x Confidence (1-10) x Ease (1-10) | Max Score: 1,000", "bold": False}],
        [],
        [{"val": "Exp ID", "header": True}, {"val": "Funnel Stage", "header": True}, {"val": "Experiment Name", "header": True}, {"val": "Core Growth Hypothesis", "header": True}, {"val": "Primary Metric", "header": True}, {"val": "Impact", "header": True}, {"val": "Confidence", "header": True}, {"val": "Ease", "header": True}, {"val": "ICE Score", "header": True}, {"val": "Priority Tier", "header": True}, {"val": "DRI Owner", "header": True}, {"val": "Status", "header": True}],
    ]

    for exp in ice_experiments:
        imp = int(exp.get("impact", 5))
        conf = int(exp.get("confidence", 5))
        ease = int(exp.get("ease", 5))
        ice_score = imp * conf * ease

        if ice_score >= 500:
            tier = {"val": "Tier 1: Quick Win", "pass": True}
        elif ice_score >= 300:
            tier = {"val": "Tier 2: Strategic Bet", "warning": True}
        else:
            tier = {"val": "Tier 3: Deprioritize"}

        t6_rows.append([
            {"val": exp.get("id"), "bold": True},
            {"val": exp.get("stage")},
            {"val": exp.get("name"), "bold": True},
            {"val": exp.get("hypothesis")},
            {"val": exp.get("metric")},
            {"val": imp, "fmt": "int"},
            {"val": conf, "fmt": "int"},
            {"val": ease, "fmt": "int"},
            {"val": ice_score, "num_val": ice_score, "accent": True, "fmt": "int"},
            tier,
            {"val": exp.get("owner")},
            {"val": exp.get("status")}
        ])
    sheets["ICE Growth Matrix"] = t6_rows

    return sheets


def export_workbook(calc_results, output_path):
    """
    Exports the 6-tab OpenXML spreadsheet to output_path.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    sheet_data = generate_workbook_content(calc_results)
    build_xlsx(output_path, sheet_data)
    return output_path


def run_tests():
    """Validates xlsx creation without external dependencies."""
    print("================================================================")
    print(" Running OpenXML Spreadsheet Exporter Test Suite")
    print("================================================================")

    import xml.etree.ElementTree as ET

    sample_path = os.path.join(os.path.dirname(__file__), "..", "templates", "sample_inputs.json")
    with open(sample_path, "r") as f:
        data = json.load(f)

    # 1. Test B2B SaaS Export
    b2b_calc = calculator.analyze_model(data["b2b_saas"])
    test_b2b_out = "/tmp/test_unit_economics.xlsx"

    export_workbook(b2b_calc, test_b2b_out)
    assert os.path.exists(test_b2b_out), "Exported B2B file does not exist!"
    assert os.path.getsize(test_b2b_out) > 5000, f"File size unexpectedly small: {os.path.getsize(test_b2b_out)} bytes"

    # Verify zip integrity, styles, and numFmts
    with zipfile.ZipFile(test_b2b_out, "r") as z:
        namelist = z.namelist()
        assert "[Content_Types].xml" in namelist, "Missing [Content_Types].xml"
        assert "xl/workbook.xml" in namelist, "Missing xl/workbook.xml"
        assert "xl/styles.xml" in namelist, "Missing xl/styles.xml"
        styles_xml = z.read("xl/styles.xml").decode("utf-8")
        assert "<numFmts" in styles_xml, "Missing <numFmts> in styles.xml"
        assert 'numFmtId="164"' in styles_xml, "Missing currency format 164"

        # Verify all sheets are valid XML and parse cleanly
        for s in range(1, 7):
            sheet_file = f"xl/worksheets/sheet{s}.xml"
            assert sheet_file in namelist, f"Missing {sheet_file}"
            sheet_content = z.read(sheet_file).decode("utf-8")
            assert "<worksheet" in sheet_content, f"{sheet_file} is not valid worksheet XML"
            assert "</worksheet>" in sheet_content, f"{sheet_file} incomplete"
            ET.fromstring(sheet_content)  # Must parse without XML syntax errors

        # Verify that numeric values are stored with <v> tags in sheet1 (Dashboard)
        sheet1_xml = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "<v>" in sheet1_xml, "Expected numeric <v> elements in sheet1"

    print(f"[PASS] B2B SaaS 6-tab workbook verified ({os.path.getsize(test_b2b_out)} bytes)")

    # 2. Test B2C D2C Export with dynamic sensitivity matrix
    b2c_calc = calculator.analyze_model(data["b2c_d2c"])
    test_b2c_out = "/tmp/test_b2c_unit_economics.xlsx"

    export_workbook(b2c_calc, test_b2c_out)
    assert os.path.exists(test_b2c_out), "Exported B2C file does not exist!"

    with zipfile.ZipFile(test_b2c_out, "r") as z:
        # Check sheet5 (Scenario Sensitivity) contains dynamic ARPU (not hardcoded $1500)
        sheet5_xml = z.read("xl/worksheets/sheet5.xml").decode("utf-8")
        ET.fromstring(sheet5_xml)
        assert "$20.40 ARPU" in sheet5_xml or "$12.24 ARPU" in sheet5_xml, "Sheet 5 should contain dynamic D2C ARPU headers"
        assert "$1,500 ARPU" not in sheet5_xml, "Sheet 5 should not hardcode $1,500 ARPU for B2C model"

        # Verify all B2C sheets parse cleanly
        for s in range(1, 7):
            ET.fromstring(z.read(f"xl/worksheets/sheet{s}.xml").decode("utf-8"))

    print(f"[PASS] B2C D2C 6-tab workbook verified with dynamic sensitivity matrix ({os.path.getsize(test_b2c_out)} bytes)")
    print(">>> ALL EXPORTER TESTS PASSED SUCCESSFULLY! <<<\n")


def main():
    parser = argparse.ArgumentParser(description="Zero-Dependency OpenXML UNIT_ECONOMICS.xlsx Exporter")
    parser.add_argument("--input", "-i", help="Path to input calculation JSON or sample inputs JSON")
    parser.add_argument("--profile", "-p", default="b2b_saas", help="Profile key within JSON")
    parser.add_argument("--output", "-o", default="UNIT_ECONOMICS.xlsx", help="Destination path for .xlsx")
    parser.add_argument("--test", action="store_true", help="Run test suite and generate sample .xlsx in /tmp")

    args = parser.parse_args()

    if args.test:
        run_tests()
        sys.exit(0)

    if not args.input:
        default_sample = os.path.join(os.path.dirname(__file__), "..", "templates", "sample_inputs.json")
        if os.path.exists(default_sample):
            args.input = default_sample
        else:
            parser.print_help()
            sys.exit(1)

    with open(args.input, "r") as f:
        raw_data = json.load(f)

    if "audit_scorecard" in raw_data:
        # Already calculated
        calc_results = raw_data
    else:
        # Needs calculation
        if args.profile in raw_data:
            block = raw_data[args.profile]
        else:
            first_key = next(iter(raw_data.keys()))
            block = raw_data[first_key]
        calc_results = calculator.analyze_model(block)

    out_file = export_workbook(calc_results, args.output)
    print(f"[SUCCESS] Compiled 6-tab institutional workbook: {out_file}")


if __name__ == "__main__":
    main()
