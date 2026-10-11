"""DART 원본 행(row) → 표준 항목 값으로 변환"""
import re

from .accounts import ACCOUNTS, DEBT_IDS, DEBT_NAMES

_ENUM = re.compile(r"^\s*(\(?[0-9ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩIVXivx]+[\.\)]\s*)+")


def norm(name):
    """계정명 비교용: 앞번호(Ⅰ. 1. (1)) 제거 + 공백 제거"""
    s = _ENUM.sub("", name or "")
    return re.sub(r"\s+", "", s)


def parse_amount(s):
    if s is None:
        return None
    s = str(s).strip().replace(",", "")
    if s in ("", "-"):
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _find(rows, sjs, ids, cands):
    for sj in sjs:                       # 1순위: 표준 계정코드
        for r in rows:
            if r.get("sj_div") == sj and r.get("account_id") in ids:
                return r
    cand = {norm(c) for c in cands}
    for sj in sjs:                       # 2순위: 계정명
        for r in rows:
            if r.get("sj_div") == sj and norm(r.get("account_nm")) in cand:
                return r
    return None


def _debt(rows, col):
    bs = [r for r in rows if r.get("sj_div") == "BS"]
    split_lease = any(norm(r.get("account_nm")) in ("유동리스부채", "비유동리스부채") for r in bs)
    picked, seen = [], set()
    for r in bs:
        n = norm(r.get("account_nm"))
        if n == "리스부채" and split_lease:
            continue
        if n in DEBT_NAMES or r.get("account_id") in DEBT_IDS:
            k = (r.get("ord"), n)
            if k in seen:
                continue
            seen.add(k)
            v = parse_amount(r.get(col))
            if v:
                picked.append((r.get("account_nm", "").strip(), v))
    return sum(v for _, v in picked), [n for n, _ in picked]


def map_statement(rows, col="thstrm_amount"):
    """반환: (values, names). values[key]=원 단위 금액 또는 None, names[key]=사용한 DART 계정명"""
    values, names = {}, {}
    for key, (_label, sjs, ids, cands) in ACCOUNTS.items():
        r = _find(rows, sjs, ids, cands)
        values[key] = parse_amount(r.get(col)) if r else None
        names[key] = r.get("account_nm", "").strip() if r else ""
    debt, debt_names = _debt(rows, col)
    values["debt"] = debt
    names["debt"] = " + ".join(debt_names) if debt_names else "(차입금 계정 없음 → 0)"
    return values, names
