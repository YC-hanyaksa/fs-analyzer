"""DART 키 없이 동작 확인용 데모 (가상 회사 '데모반도체')

사용: python -m fs_analyzer.demo
별도 기준으로 본업 적자인 해가 2년 있어 '자회사 의존형' 경고가 뜨도록 만든 가상 데이터입니다.
"""
from datetime import datetime

from .accounts import ACCOUNTS
from .pipeline import KST, run_analysis, slack_summary

E = 100_000_000
DEBT_ROWS = [("st_b", "ifrs-full_ShorttermBorrowings", "단기차입금"),
             ("lt_b", "ifrs-full_LongtermBorrowings", "장기차입금"),
             ("bond", "ifrs-full_BondsIssued", "사채"),
             ("lease_c", "ifrs-full_CurrentLeaseLiabilities", "유동리스부채"),
             ("lease_n", "ifrs-full_NoncurrentLeaseLiabilities", "비유동리스부채")]
F = ["revenue", "cogs", "op_income", "pretax", "tax", "net_income", "ni_owner", "ni_nci",
     "finance_cost", "dividend_income",
     "total_assets", "current_assets", "cash", "st_fin", "receivables", "inventories",
     "total_liabilities", "current_liabilities", "payables", "total_equity", "equity_owner",
     "st_b", "lt_b", "bond", "lease_c", "lease_n",
     "cfo", "capex_ppe", "capex_intan", "depreciation", "amortization", "interest_paid", "dividends_paid"]


def _t(*rows):
    return [dict(zip(F, r)) for r in rows]


# 단위: 억원. None = 해당 계정 없음
CONS = dict(zip([2020, 2021, 2022, 2023, 2024, 2025], _t(
    (None, None, None, None, None, None, None, None, None, None,
     14000, 5500, 1400, 400, 1400, 1600, 5800, 3300, 950, 8200, 7650, 800, 1200, 1000, 50, 150,
     None, None, None, None, None, None, None),
    (10000, 7000, 1500, 1600, 350, 1250, 1150, 100, 180, None,
     15000, 6000, 1500, 500, 1500, 1800, 6000, 3500, 1000, 9000, 8400, 800, 1200, 1000, 50, 150,
     2200, 1800, 100, 900, 50, 120, 300),
    (11500, 7800, 2100, 2200, 480, 1720, 1580, 140, 190, None,
     16500, 6800, 1800, 600, 1700, 2000, 6300, 3600, 1100, 10200, 9500, 700, 1300, 1000, 50, 140,
     2900, 2000, 120, 1000, 55, 125, 320),
    (9800, 7600, 600, 550, 110, 440, 380, 60, 240, None,
     17200, 7000, 1200, 400, 1900, 2900, 7200, 4200, 950, 10000, 9300, 1500, 1600, 1000, 55, 150,
     1100, 2300, 130, 1100, 60, 160, 320),
    (12000, 8200, 2000, 2050, 440, 1610, 1450, 160, 250, None,
     18800, 7900, 1700, 500, 2300, 2800, 7600, 4300, 1200, 11200, 10400, 1300, 1700, 1200, 55, 150,
     2600, 2400, 140, 1150, 60, 170, 350),
    (14500, 9500, 3200, 3300, 720, 2580, 2350, 230, 240, None,
     21000, 9000, 2200, 600, 3300, 3100, 8300, 4700, 1400, 12700, 11700, 1200, 1800, 1200, 60, 160,
     2400, 2600, 150, 1250, 65, 165, 400),
)))
SEP = dict(zip([2020, 2021, 2022, 2023, 2024, 2025], _t(
    (None, None, None, None, None, None, None, None, None, None,
     10600, 3400, 550, 200, 850, 1000, 3400, 1950, 580, 7200, None, 500, 800, 1000, 20, 60,
     None, None, None, None, None, None, None),
    (6000, 4800, 400, 700, 120, 580, None, None, 110, 250,
     11000, 3500, 600, 200, 900, 1100, 3500, 2000, 600, 7500, None, 500, 800, 1000, 20, 60,
     700, 600, 40, 400, 20, 90, 300),
    (6300, 5200, 300, 650, 100, 550, None, None, 110, 300,
     11300, 3600, 650, 200, 950, 1200, 3600, 2050, 620, 7700, None, 450, 850, 1000, 20, 55,
     650, 650, 40, 420, 20, 92, 320),
    (5200, 5000, -300, 50, 0, 50, None, None, 140, 350,
     11400, 3400, 400, 100, 1000, 1500, 3900, 2300, 560, 7500, None, 900, 900, 1000, 22, 60,
     200, 700, 45, 440, 22, 110, 320),
    (5800, 5300, -100, 300, 40, 260, None, None, 145, 400,
     11700, 3600, 500, 150, 1100, 1450, 4100, 2350, 650, 7600, None, 800, 1000, 1200, 22, 60,
     400, 650, 45, 450, 22, 115, 350),
    (6800, 5700, 800, 1300, 250, 1050, None, None, 140, 500,
     12500, 4100, 700, 200, 1500, 1500, 4400, 2500, 750, 8100, None, 750, 1050, 1200, 24, 62,
     900, 700, 50, 470, 24, 112, 400),
)))


def _rows(cur, prev):
    rows, ord_ = [], 0
    def emit(sj, aid, nm, key):
        nonlocal ord_
        a, b = cur.get(key), (prev or {}).get(key)
        if a is None and b is None:
            return
        ord_ += 1
        fmt = lambda x: "" if x is None else str(int(x * E))
        rows.append({"sj_div": sj, "account_id": aid, "account_nm": nm, "ord": str(ord_),
                     "thstrm_amount": fmt(a), "frmtrm_amount": fmt(b)})
    if cur.get("revenue") is not None or (prev or {}).get("revenue") is not None:
        cur = dict(cur, gross_profit=None if cur.get("revenue") is None else cur["revenue"] - cur["cogs"])
        if prev and prev.get("revenue") is not None:
            prev = dict(prev, gross_profit=prev["revenue"] - prev["cogs"])
    for key, (label, sjs, ids, names) in ACCOUNTS.items():
        nm = {"op_income": "영업이익(손실)", "cfo": "영업활동현금흐름"}.get(key, names[0])
        if key in ("receivables", "payables"):
            nm = names[0]
        emit(sjs[0], ids[0] if ids else "-표준계정코드 미사용-", nm, key)
        if key == "inventories":   # 재고 다음에 차입금 계정을 부채 영역에 배치
            pass
    for k, aid, nm in DEBT_ROWS:
        emit("BS", aid, nm, k)
    return rows


class DemoDart:
    def corp_code(self, code):
        return "00000000", "데모반도체"

    def company(self, corp_code):
        return {"corp_name": "데모반도체", "induty_code": "264"}

    def annual_statement(self, corp_code, year, fs_div):
        src = CONS if fs_div == "CFS" else SEP
        if year not in src or year == 2020:
            return None
        return _rows(src[year], src.get(year - 1))


def main():
    rep, path = run_analysis(DemoDart(), "000000", 45000, 100_000_000, 6_000_000, "output",
                             today=datetime(2026, 10, 11, tzinfo=KST))
    print(slack_summary(rep))
    print(f"\n저장: {path}")
    return rep, path


if __name__ == "__main__":
    main()
