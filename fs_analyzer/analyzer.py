"""규칙 기반 재무 분석"""
import math

from . import config as C

G, Y, R, O, N = "🟢", "🟡", "🔴", "🟠", "⚪"


# ── 계산 도우미 ───────────────────────────────────────
def sd(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def pct(a, b):
    r = sd(a, b)
    return None if r is None else r * 100


def avg(cur, prev):
    if cur is None:
        return None
    return cur if prev is None else (cur + prev) / 2


def growth(cur, prev):
    if cur is None or prev is None or prev <= 0:
        return None
    return (cur / prev - 1) * 100


def ssum(*xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) if xs else None


def pos(x):
    return x is not None and x > 0


def eok(x):
    return "-" if x is None else f"{x / C.UNIT:,.0f}{C.UNIT_LABEL}"


def f1(x, suffix=""):
    return "-" if x is None else f"{x:,.1f}{suffix}"


# ── 지표 정의 (엑셀 '재무비율' 시트 순서) ──────────────
RATIO_SPEC = [
    ("성장성", "rev_g", "매출 증가율", "%"),
    ("성장성", "op_g", "영업이익 증가율", "%"),
    ("성장성", "ni_g", "지배주주순이익 증가율", "%"),
    ("수익성", "gpm", "매출총이익률", "%"),
    ("수익성", "opm", "영업이익률", "%"),
    ("수익성", "npm", "순이익률", "%"),
    ("수익성", "roe", "ROE(지배)", "%"),
    ("수익성", "roa", "ROA", "%"),
    ("수익성", "roic", "ROIC", "%"),
    ("수익성", "dp_margin", "듀퐁① 순이익률(지배)", "%"),
    ("수익성", "dp_turnover", "듀퐁② 총자산회전율", "x"),
    ("수익성", "dp_lev", "듀퐁③ 재무레버리지", "x"),
    ("안정성", "debt_ratio", "부채비율", "%"),
    ("안정성", "current_ratio", "유동비율", "%"),
    ("안정성", "quick_ratio", "당좌비율", "%"),
    ("안정성", "net_debt", "순차입금(음수=순현금)", "amt"),
    ("안정성", "nd_ebitda", "순차입금/EBITDA", "x"),
    ("안정성", "icr", "이자보상배율", "x"),
    ("효율성", "dso", "매출채권 회전일수", "days"),
    ("효율성", "dio", "재고자산 회전일수", "days"),
    ("효율성", "dpo", "매입채무 회전일수", "days"),
    ("효율성", "ccc", "현금전환주기(CCC)", "days"),
    ("효율성", "ar_g", "매출채권 증가율", "%"),
    ("효율성", "inv_g", "재고자산 증가율", "%"),
    ("현금흐름", "cfo_ni", "영업CF/순이익", "x"),
    ("현금흐름", "fcf", "FCF(영업CF−CAPEX)", "amt"),
    ("현금흐름", "capex_rev", "CAPEX/매출", "%"),
    ("현금흐름", "capex_da", "CAPEX/감가상각비", "x"),
    ("현금흐름", "ebitda", "EBITDA", "amt"),
]


# ── 1. 값 보완 ────────────────────────────────────────
def enrich(v, is_cons):
    v = dict(v)
    notes = []
    if v.get("cogs") is None and v.get("revenue") is not None and v.get("gross_profit") is not None:
        v["cogs"] = v["revenue"] - v["gross_profit"]
        notes.append("매출원가 = 매출액 − 매출총이익으로 계산")
    if v.get("gross_profit") is None and v.get("revenue") is not None and v.get("cogs") is not None:
        v["gross_profit"] = v["revenue"] - v["cogs"]
    if v.get("ni_owner") is None:
        v["ni_owner"] = v.get("net_income")
        if is_cons and v.get("net_income") is not None:
            notes.append("지배주주순이익 계정 없음 → 당기순이익으로 대체")
    if v.get("equity_owner") is None:
        v["equity_owner"] = v.get("total_equity")
        if is_cons and v.get("total_equity") is not None:
            notes.append("지배주주지분 계정 없음 → 자본총계로 대체")

    if v.get("interest_expense") is not None:
        v["interest"] = abs(v["interest_expense"])
    elif v.get("interest_paid") is not None:
        v["interest"] = abs(v["interest_paid"])
        notes.append("이자비용 → 현금흐름표 '이자의 지급'으로 대체")
    elif v.get("finance_cost") is not None:
        v["interest"] = abs(v["finance_cost"])
        notes.append("이자비용 → '금융비용'으로 대체(외환손실 등 포함되어 과대 가능)")
    else:
        v["interest"] = None

    ppe, intan = v.get("capex_ppe"), v.get("capex_intan")
    v["capex"] = ssum(abs(ppe) if ppe is not None else None, abs(intan) if intan is not None else None)
    dep = v.get("depreciation")
    v["da"] = None if dep is None else abs(dep) + abs(v.get("amortization") or 0)
    if dep is None:
        notes.append("감가상각비가 현금흐름표 본문에 없음 → EBITDA 산출 불가")
    v["ebitda"] = None if v.get("op_income") is None or v["da"] is None else v["op_income"] + v["da"]
    v["cash_like"] = ssum(v.get("cash"), v.get("st_fin"))
    v["net_debt"] = None if v["cash_like"] is None else (v.get("debt") or 0) - v["cash_like"]
    te, eo = v.get("total_equity"), v.get("equity_owner")
    v["nci_equity"] = (te - eo) if te is not None and eo is not None else 0
    v["fcf"] = None if v.get("cfo") is None or v["capex"] is None else v["cfo"] - v["capex"]
    dp = v.get("dividends_paid")
    v["dividends_paid"] = abs(dp) if dp is not None else None
    v["_notes"] = notes
    return v


# ── 2. 재무비율 ───────────────────────────────────────
def _ic(d):
    if not d or d.get("total_equity") is None:
        return None
    return d["total_equity"] + (d.get("debt") or 0) - (d.get("cash_like") or 0)


def compute_ratios(years, V, prior):
    out = {}
    for i, y in enumerate(years):
        v = V[y]
        p = V[years[i - 1]] if i > 0 else (prior or {})
        g = p.get
        r = {}
        r["rev_g"] = growth(v.get("revenue"), g("revenue"))
        r["op_g"] = growth(v.get("op_income"), g("op_income"))
        r["ni_g"] = growth(v.get("ni_owner"), g("ni_owner"))
        r["gpm"] = pct(v.get("gross_profit"), v.get("revenue"))
        r["opm"] = pct(v.get("op_income"), v.get("revenue"))
        r["npm"] = pct(v.get("net_income"), v.get("revenue"))

        a_eqo = avg(v.get("equity_owner"), g("equity_owner"))
        a_ta = avg(v.get("total_assets"), g("total_assets"))
        r["roe"] = pct(v.get("ni_owner"), a_eqo) if pos(a_eqo) else None
        r["roa"] = pct(v.get("net_income"), a_ta)
        t = sd(v.get("tax"), v.get("pretax"))
        if t is None or not 0 <= t <= 0.5:
            t = C.DEFAULT_TAX_RATE
        nopat = None if v.get("op_income") is None else v["op_income"] * (1 - t)
        a_ic = avg(_ic(v), _ic(p))
        r["roic"] = pct(nopat, a_ic) if pos(a_ic) else None
        r["dp_margin"] = pct(v.get("ni_owner"), v.get("revenue"))
        r["dp_turnover"] = sd(v.get("revenue"), a_ta)
        r["dp_lev"] = sd(a_ta, a_eqo) if pos(a_eqo) else None

        te = v.get("total_equity")
        r["debt_ratio"] = pct(v.get("total_liabilities"), te) if pos(te) else None
        r["current_ratio"] = pct(v.get("current_assets"), v.get("current_liabilities"))
        ca = v.get("current_assets")
        r["quick_ratio"] = pct(None if ca is None else ca - (v.get("inventories") or 0),
                               v.get("current_liabilities"))
        r["net_debt"] = v.get("net_debt")
        r["nd_ebitda"] = sd(v.get("net_debt"), v.get("ebitda")) if pos(v.get("ebitda")) else None
        r["icr"] = sd(v.get("op_income"), v.get("interest")) if pos(v.get("interest")) else None

        cost = v.get("cogs") or v.get("revenue")
        days = lambda a, b: None if sd(a, b) is None else sd(a, b) * 365
        r["dso"] = days(avg(v.get("receivables"), g("receivables")), v.get("revenue"))
        r["dio"] = days(avg(v.get("inventories"), g("inventories")), cost)
        r["dpo"] = days(avg(v.get("payables"), g("payables")), cost)
        r["ccc"] = (r["dso"] + r["dio"] - r["dpo"]
                    if None not in (r["dso"], r["dio"], r["dpo"]) else None)
        r["ar_g"] = growth(v.get("receivables"), g("receivables"))
        r["inv_g"] = growth(v.get("inventories"), g("inventories"))

        r["cfo_ni"] = sd(v.get("cfo"), v.get("net_income")) if pos(v.get("net_income")) else None
        r["fcf"] = v.get("fcf")
        r["capex_rev"] = pct(v.get("capex"), v.get("revenue"))
        r["capex_da"] = sd(v.get("capex"), v.get("da"))
        r["ebitda"] = v.get("ebitda")
        out[y] = r
    return out


def cagr(first, last, n):
    if not pos(first) or not pos(last) or n <= 0:
        return None
    return ((last / first) ** (1 / n) - 1) * 100


# ── 3. 경고 신호 ──────────────────────────────────────
def find_warnings(years, V, Rt):
    W = []
    add = lambda y, kind, msg: W.append({"year": y, "kind": kind, "detail": msg})
    for i, y in enumerate(years):
        v, r = V[y], Rt[y]
        p = V[years[i - 1]] if i > 0 else None
        if p:
            ni0, ni1, cf0, cf1 = p.get("net_income"), v.get("net_income"), p.get("cfo"), v.get("cfo")
            if None not in (ni0, ni1, cf0, cf1) and ni1 > ni0 and cf1 < cf0:
                add(y, "이익-현금 괴리",
                    f"순이익 {eok(ni0)}→{eok(ni1)} 증가, 영업CF {eok(cf0)}→{eok(cf1)} 감소")
            dr0 = Rt[years[i - 1]].get("debt_ratio")
            if dr0 is not None and r.get("debt_ratio") is not None \
                    and r["debt_ratio"] - dr0 >= C.DEBT_RATIO_JUMP_PCTP:
                add(y, "부채비율 급증", f"부채비율 {dr0:.0f}% → {r['debt_ratio']:.0f}%")
        if r.get("rev_g") is not None:
            if r.get("ar_g") is not None and r["ar_g"] - r["rev_g"] >= C.GROWTH_GAP_PCTP:
                add(y, "매출채권 과다 증가",
                    f"매출채권 {r['ar_g']:+.1f}% vs 매출 {r['rev_g']:+.1f}%")
            if r.get("inv_g") is not None and r["inv_g"] - r["rev_g"] >= C.GROWTH_GAP_PCTP:
                add(y, "재고 과다 증가",
                    f"재고자산 {r['inv_g']:+.1f}% vs 매출 {r['rev_g']:+.1f}% (다운사이클 선행 신호 가능)")
        if r.get("icr") is not None and r["icr"] < C.INTEREST_COVERAGE_MIN:
            add(y, "이자보상배율 1배 미만", f"이자보상배율 {r['icr']:.2f}배")

    for key, kind, label in (("op_income", "연속 영업적자", "영업이익"),
                             ("fcf", "연속 FCF 마이너스", "FCF")):
        streak = []
        for y in years + [None]:
            val = V[y].get(key) if y else None
            if val is not None and val < 0:
                streak.append(y)
                continue
            if len(streak) >= C.CONSEC_LOSS_YEARS:
                add(streak[-1], kind,
                    f"FY{streak[0]}~FY{streak[-1]} {len(streak)}년 연속 {label} 마이너스")
            streak = []
    return sorted(W, key=lambda w: (w["year"], w["kind"]))


# ── 4. 연결 vs 별도 ───────────────────────────────────
def compare_cons_sep(years, VC, VS, RC, RS):
    rows = {}
    for y in years:
        c, s = VC.get(y), VS.get(y)
        if not c or not s:
            continue
        cop, sop = c.get("op_income"), s.get("op_income")
        d = {}
        d["c_rev"], d["s_rev"] = c.get("revenue"), s.get("revenue")
        d["c_op"], d["s_op"] = cop, sop
        d["c_ni"], d["s_ni"] = c.get("ni_owner"), s.get("net_income")
        d["c_cfo"], d["s_cfo"] = c.get("cfo"), s.get("cfo")
        d["dep"] = pct(cop - sop, cop) if pos(cop) and sop is not None else None
        d["sep_loss"] = sop is not None and cop is not None and sop < 0 < cop
        div = ssum(s.get("dividend_income"), s.get("equity_method"))
        d["div_dep"] = pct(div, s.get("net_income")) if pos(s.get("net_income")) and div is not None else None
        d["cfo_ratio"] = sd(s.get("cfo"), c.get("cfo")) if pos(c.get("cfo")) else None
        d["cfo_flag"] = (s.get("cfo") is not None and c.get("cfo") is not None
                         and s["cfo"] < 0 < c["cfo"])
        d["nci"] = pct(c.get("ni_nci"), c.get("net_income")) if pos(c.get("net_income")) else None
        cd, sdr = RC[y].get("debt_ratio"), RS[y].get("debt_ratio")
        d["debt_gap"] = None if cd is None or sdr is None else cd - sdr
        d["cons_worse"] = (pos(sop) and cop is not None
                           and cop < sop * (1 - C.CONS_WORSE_PCT / 100))
        rows[y] = d

    verdicts = []
    if not rows:
        return rows, verdicts
    latest = max(rows)
    L = rows[latest]
    loss_years = [y for y, d in rows.items() if d["sep_loss"]]
    if len(loss_years) >= C.SEP_LOSS_MIN_YEARS or (L["dep"] is not None and L["dep"] >= C.SUB_DEPENDENCY_PCT):
        why = []
        if len(loss_years) >= C.SEP_LOSS_MIN_YEARS:
            why.append(f"별도 영업적자·연결 흑자 {len(loss_years)}년"
                       f"({', '.join('FY' + str(y) for y in loss_years)})")
        if L["dep"] is not None and L["dep"] >= C.SUB_DEPENDENCY_PCT:
            why.append(f"FY{latest} 자회사 이익 의존도 {L['dep']:.0f}%")
        if L["cfo_flag"]:
            why.append("별도 영업CF 마이너스(자회사 현금이 모회사로 안 올라옴)")
        verdicts.append((R, "자회사 의존형", " / ".join(why)))
    if L["div_dep"] is not None and L["div_dep"] >= C.DIVIDEND_DEPENDENCY_PCT:
        verdicts.append((Y, "지주사형",
                         f"FY{latest} 별도 순이익 중 배당·지분법 비중 {L['div_dep']:.0f}% "
                         "(지주회사라면 정상)"))
    if L["cons_worse"]:
        verdicts.append((O, "자회사 부실형",
                         f"FY{latest} 연결 영업이익 {eok(L['c_op'])} < 별도 {eok(L['s_op'])}"
                         f" (−{C.CONS_WORSE_PCT}% 이상)"))
    if not verdicts:
        verdicts.append((G, "특이사항 없음", "연결 기준 분석이 적절합니다"))
    return rows, verdicts


# ── 5. 밸류에이션 ─────────────────────────────────────
def valuation(v, price, issued, treasury):
    out = {"price": price, "issued_shares": issued, "treasury": treasury,
           "float_shares": issued - treasury,
           "treasury_pct": treasury / issued * 100 if issued else None}
    for basis, sh in (("float", issued - treasury), ("issued", issued)):
        mcap = price * sh
        eps = sd(v.get("ni_owner"), sh)
        bps = sd(v.get("equity_owner"), sh)
        ev = mcap + (v.get("debt") or 0) - (v.get("cash_like") or 0) + (v.get("nci_equity") or 0)
        out[basis] = {
            "mcap": mcap, "eps": eps, "bps": bps,
            "per": price / eps if pos(eps) else None,
            "pbr": price / bps if pos(bps) else None,
            "ev": ev,
            "ev_ebitda": ev / v["ebitda"] if pos(v.get("ebitda")) else None,
        }
    dp = v.get("dividends_paid")
    out["payout"] = pct(dp, v.get("ni_owner")) if pos(v.get("ni_owner")) else None
    out["div_yield"] = pct(dp, out["float"]["mcap"])
    return out


# ── 6. 신호등 ─────────────────────────────────────────
def signals(years, V, Rt, cg, val, warnings, cs_verdicts):
    S = []
    last, first = years[-1], years[0]
    L = Rt[last]

    rc, oc = cg.get("revenue"), cg.get("op_income")
    op_up = (V[last].get("op_income") or 0) > (V[first].get("op_income") or 0)
    if rc is None:
        S.append(("성장성", N, "매출 데이터 부족"))
    else:
        light = G if rc >= C.GROWTH_GREEN_CAGR and op_up else R if rc < 0 and not op_up else Y
        S.append(("성장성", light, f"매출 CAGR {rc:.1f}%, 영업이익 "
                  + (f"CAGR {oc:.1f}%" if oc is not None else ("증가" if op_up else "감소"))))

    roe = L.get("roe")
    if roe is None:
        S.append(("수익성", R if (V[last].get("ni_owner") or 0) < 0 else N, "ROE 산출 불가(적자 또는 자본잠식)"))
    else:
        light = G if roe >= C.ROE_GREEN else Y if roe >= C.ROE_YELLOW else R
        S.append(("수익성", light, f"ROE {roe:.1f}%, 영업이익률 {f1(L.get('opm'), '%')}"))

    dr, cr, ic = L.get("debt_ratio"), L.get("current_ratio"), L.get("icr")
    gk, rk = C.STAB_GREEN, C.STAB_RED
    red = (dr is not None and dr > rk["debt_ratio"]) or (cr is not None and cr < rk["current_ratio"]) \
        or (ic is not None and ic < rk["icr"])
    green = (dr is not None and dr <= gk["debt_ratio"]) and (cr is not None and cr >= gk["current_ratio"]) \
        and (ic is None or ic >= gk["icr"])
    S.append(("안정성", R if red else G if green else Y,
              f"부채비율 {f1(dr, '%')}, 유동비율 {f1(cr, '%')}, 이자보상배율 {f1(ic, '배')}"))

    ccc = [Rt[y].get("ccc") for y in years]
    past = [x for x in ccc[:-1] if x is not None]
    if ccc[-1] is None or not past:
        S.append(("효율성", N, "CCC 산출 불가"))
    else:
        diff = ccc[-1] - sum(past) / len(past)
        light = R if diff >= C.CCC_RED_DAYS else Y if diff >= C.CCC_YELLOW_DAYS else G
        S.append(("효율성", light, f"CCC {ccc[-1]:.0f}일 (과거 평균 대비 {diff:+.0f}일)"))

    fcfs = [V[y].get("fcf") for y in years if V[y].get("fcf") is not None]
    cn = [Rt[y]["cfo_ni"] for y in years if Rt[y].get("cfo_ni") is not None]
    if not fcfs:
        S.append(("현금흐름", N, "FCF 산출 불가"))
    else:
        pos_n = sum(1 for x in fcfs if x > 0)
        cn_avg = sum(cn) / len(cn) if cn else None
        light = (G if pos_n >= len(fcfs) - 1 and (cn_avg or 0) >= 1
                 else R if (len(fcfs) - pos_n) >= 3 or (cn_avg is not None and cn_avg < 0.7) else Y)
        S.append(("현금흐름", light, f"FCF 플러스 {pos_n}/{len(fcfs)}년, 영업CF/순이익 평균 {f1(cn_avg, '배')}"))

    per, pbr = val["float"]["per"], val["float"]["pbr"]
    if per is None:
        S.append(("밸류에이션", R, f"적자로 PER 산출 불가, PBR {f1(pbr, '배')}"))
    else:
        light = G if per < C.PER_GREEN else Y if per <= C.PER_YELLOW else R
        S.append(("밸류에이션", light, f"PER {per:.1f}배, PBR {f1(pbr, '배')} (유통주식 기준)"))

    recent = {w["kind"] for w in warnings if w["year"] >= years[-2 if len(years) > 1 else -1]}
    n = len(recent)
    S.append(("경고신호", G if n == 0 else Y if n <= 2 else R,
              "최근 2년 경고 없음" if n == 0 else f"최근 2년 {n}종: " + ", ".join(sorted(recent))))

    if cs_verdicts is not None:
        worst = cs_verdicts[0]
        S.append(("연결vs별도", worst[0], " / ".join(t for _, t, _ in cs_verdicts)))
    return S


# ── 7. 해석 코멘트 ────────────────────────────────────
def _dupont_driver(r0, r1):
    parts = {"순이익률": ("dp_margin", r0, r1), "자산회전율": ("dp_turnover", r0, r1),
             "재무레버리지": ("dp_lev", r0, r1)}
    best, mag = None, 0
    for name, (k, a, b) in parts.items():
        x, y = a.get(k), b.get(k)
        if x is None or y is None or x <= 0 or y <= 0:
            continue
        m = abs(math.log(y / x))
        if m > mag:
            best, mag = (name, "상승" if y > x else "하락"), m
    return best


def comments(years, V, Rt, cg, val, warnings, cs_verdicts, basis):
    out = []
    last, first = years[-1], years[0]
    L = Rt[last]
    n = len(years) - 1
    rc = cg.get("revenue")
    if rc is not None:
        oc = cg.get("op_income")
        out.append(f"[성장성] FY{first}→FY{last} 매출은 연평균 {abs(rc):.1f}% {'증가' if rc >= 0 else '감소'}했고, "
                   + (f"영업이익은 연평균 {abs(oc):.1f}% {'증가' if oc >= 0 else '감소'}했습니다." if oc is not None
                      else f"영업이익은 {eok(V[first].get('op_income'))} → {eok(V[last].get('op_income'))}입니다."))
    opms = [Rt[y]["opm"] for y in years if Rt[y].get("opm") is not None]
    if L.get("opm") is not None and opms:
        s = (f"[수익성] FY{last} 영업이익률 {L['opm']:.1f}% ({len(years)}년 평균 {sum(opms) / len(opms):.1f}%), "
             f"ROE {f1(L.get('roe'), '%')}, ROIC {f1(L.get('roic'), '%')}.")
        if len(years) > 1:
            d = _dupont_driver(Rt[years[-2]], L)
            if d:
                s += f" 전년 대비 ROE 변화는 주로 {d[0]} {d[1]} 영향입니다."
        out.append(s)
    nd = V[last].get("net_debt")
    out.append(f"[안정성] 부채비율 {f1(L.get('debt_ratio'), '%')}, "
               + ("순현금 상태" if nd is not None and nd < 0 else f"순차입금/EBITDA {f1(L.get('nd_ebitda'), '배')}")
               + f", 이자보상배율 {f1(L.get('icr'), '배')}.")
    if L.get("ccc") is not None:
        s = f"[효율성] CCC {L['ccc']:.0f}일 (매출채권 {L['dso']:.0f}일 + 재고 {L['dio']:.0f}일 − 매입채무 {L['dpo']:.0f}일)."
        if any(w["kind"] == "재고 과다 증가" and w["year"] == last for w in warnings):
            s += " 재고가 매출보다 빠르게 늘어 업황 둔화 가능성을 점검할 필요가 있습니다."
        out.append(s)
    fcfs = [V[y].get("fcf") for y in years if V[y].get("fcf") is not None]
    if fcfs:
        out.append(f"[현금흐름] {len(fcfs)}년 누적 FCF {eok(sum(fcfs))}, "
                   f"FY{last} CAPEX/매출 {f1(L.get('capex_rev'), '%')}, CAPEX/감가상각비 {f1(L.get('capex_da'), '배')}"
                   + (" (감가상각 이상으로 투자 확대 중)" if (L.get("capex_da") or 0) > 1.5 else "") + ".")
    fv = val["float"]
    s = (f"[밸류에이션] 현재가 {val['price']:,}원 기준 PER {f1(fv['per'], '배')}, PBR {f1(fv['pbr'], '배')}, "
         f"EV/EBITDA {f1(fv['ev_ebitda'], '배')} (유통주식 기준).")
    if val["treasury_pct"] and val["treasury_pct"] >= C.TREASURY_WARN_PCT:
        iv = val["issued"]
        s += (f" 자사주 비중 {val['treasury_pct']:.1f}%로 높아 발행주식 기준 PER {f1(iv['per'], '배')}도 함께 보세요."
              " 소각 여부를 확인하세요.")
    out.append(s)
    if cs_verdicts:
        for light, title, detail in cs_verdicts:
            out.append(f"[연결vs별도] {light} {title}: {detail}")
    elif basis == "별도":
        out.append("[연결vs별도] 연결재무제표가 없는 회사라 별도 기준으로 분석했습니다.")
    return out


# ── 전체 실행 ─────────────────────────────────────────
def analyze(meta, mapped, price, issued, treasury):
    """mapped = {"CFS": {"years": {y: values}, "names": {...}, "prior": values|None}, "OFS": {...}}"""
    has_cons = bool(mapped.get("CFS") and mapped["CFS"]["years"])
    basis_key = "CFS" if has_cons else "OFS"
    basis = "연결" if has_cons else "별도"

    def prep(key):
        blk = mapped[key]
        is_c = key == "CFS"
        V = {y: enrich(v, is_c) for y, v in blk["years"].items()}
        prior = enrich(blk["prior"], is_c) if blk.get("prior") else None
        yrs = sorted(V)
        return yrs, V, prior

    years, V, prior = prep(basis_key)
    if len(years) < 2:
        raise ValueError("분석 가능한 사업보고서가 2개년 미만입니다.")
    Rt = compute_ratios(years, V, prior)
    n = len(years) - 1
    cg = {k: cagr(V[years[0]].get(k), V[years[-1]].get(k), n) for k in ("revenue", "op_income", "ni_owner")}

    sep = None
    cs_rows, cs_verdicts = {}, None
    if has_cons and mapped.get("OFS") and mapped["OFS"]["years"]:
        sy, SV, sprior = prep("OFS")
        SR = compute_ratios(sy, SV, sprior)
        sep = {"years": sy, "V": SV, "R": SR}
        cs_rows, cs_verdicts = compare_cons_sep(years, V, SV, Rt, SR)

    warnings = find_warnings(years, V, Rt)
    val = valuation(V[years[-1]], price, issued, treasury)
    sig = signals(years, V, Rt, cg, val, warnings, cs_verdicts)
    com = comments(years, V, Rt, cg, val, warnings, cs_verdicts, basis)

    notes = {}
    for y in years:
        for nt in V[y]["_notes"]:
            notes.setdefault(nt, []).append(y)

    return {
        "meta": meta, "basis": basis, "years": years, "V": V, "R": Rt, "cagr": cg,
        "names": mapped[basis_key]["names"], "sep": sep,
        "sep_names": mapped["OFS"]["names"] if sep else None,
        "cs_rows": cs_rows, "cs_verdicts": cs_verdicts,
        "warnings": warnings, "valuation": val, "signals": sig, "comments": com, "notes": notes,
    }
