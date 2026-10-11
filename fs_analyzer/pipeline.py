"""종목코드 → DART 수집 → 매핑 → 분석 → 엑셀"""
from datetime import datetime, timedelta, timezone

from . import config as C
from .analyzer import analyze
from .dart_client import DartError
from .excel_writer import write_excel
from .mapper import map_statement

KST = timezone(timedelta(hours=9))
FINANCIAL_KSIC = ("64", "65", "66")   # 금융업, 보험업, 금융·보험 서비스업


class NotSupported(Exception):
    pass


def fetch_statements(dart, corp_code, n_years, today):
    latest, first_rows = None, None
    for y in (today.year - 1, today.year - 2):
        rows = dart.annual_statement(corp_code, y, "OFS")
        if rows:
            latest, first_rows = y, rows
            break
    if latest is None:
        raise DartError("최근 2년 내 사업보고서를 찾지 못했습니다.")
    years = list(range(latest - n_years + 1, latest + 1))
    raw = {"OFS": {latest: first_rows}, "CFS": {}}
    for y in years:
        if y != latest:
            rows = dart.annual_statement(corp_code, y, "OFS")
            if rows:
                raw["OFS"][y] = rows
    for y in sorted(years, reverse=True):
        rows = dart.annual_statement(corp_code, y, "CFS")
        if rows:
            raw["CFS"][y] = rows
        elif y == latest:
            break   # 최근 연도에 연결이 없으면 연결 미작성 회사로 판단
    return raw


def map_raw(raw):
    mapped = {}
    for fs, by_year in raw.items():
        if not by_year:
            mapped[fs] = None
            continue
        years = sorted(by_year)
        vals, names = {}, {}
        for y in years:
            vals[y], nm = map_statement(by_year[y], "thstrm_amount")
            if y == years[-1]:
                names = nm
        prior, _ = map_statement(by_year[years[0]], "frmtrm_amount")
        mapped[fs] = {"years": vals, "names": names, "prior": prior}
    return mapped


def run_analysis(dart, stock_code, price, issued, treasury, out_dir=".", today=None):
    today = today or datetime.now(KST)
    corp_code, corp_name = dart.corp_code(stock_code)
    info = dart.company(corp_code)
    if (info.get("induty_code") or "").startswith(FINANCIAL_KSIC):
        raise NotSupported(f"{corp_name}은(는) 금융업이라 재무제표 구조가 달라 이번 버전의 분석 대상이 아닙니다.")
    raw = fetch_statements(dart, corp_code, C.YEARS, today)
    mapped = map_raw(raw)
    meta = {"name": corp_name, "code": stock_code, "date": today.strftime("%Y-%m-%d")}
    report = analyze(meta, mapped, price, issued, treasury)
    path = write_excel(report, out_dir)
    return report, path


def slack_summary(rep):
    y = rep["years"]
    lines = [f"*{rep['meta']['name']}({rep['meta']['code']}) 재무 분석* · {rep['basis']} 기준 · "
             f"FY{y[0]}~FY{y[-1]}"]
    for cat, light, why in rep["signals"]:
        lines.append(f"{light} *{cat}* — {why}")
    v = rep["valuation"]
    if v["treasury_pct"] and v["treasury_pct"] >= C.TREASURY_WARN_PCT:
        lines.append(f"⚠️ 자사주 비중 {v['treasury_pct']:.1f}% — 소각 여부 확인 필요")
    return "\n".join(lines)
