"""슬랙 채널 폴링 · 요청 파싱 · 결과 업로드"""
import re
import time

from . import config as C

DONE = {"white_check_mark", "x"}        # 봇이 이 이모지를 달면 처리 완료로 간주
USAGE = ("입력 형식: `종목코드 주가 발행주식수 [자기주식수]`\n"
         "예) `005930 75000 5969782550 0`  (쉼표 허용, 자기주식수 생략 시 0)")
_REQ = re.compile(r"^(\d{6})\s+([\d,]+)\s+([\d,]+)(?:\s+([\d,]+))?$")


def clean_text(text):
    """슬랙 서식(코드 `, 굵게 *, 기울임 _, 취소선 ~)과 특수 공백 제거"""
    t = re.sub(r"[`*_~]", "", text or "")
    t = re.sub(r"[ ​  　]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def parse_request(text):
    """요청이 아니면 None, 형식 오류면 ValueError, 정상이면 dict"""
    t = clean_text(text)
    if not re.match(r"^\d{6}(\s|$)", t):
        return None
    m = _REQ.match(t)
    if not m:
        raise ValueError("입력 형식이 맞지 않습니다.\n" + USAGE)
    num = lambda s: int(s.replace(",", "")) if s else 0
    price, issued, treasury = num(m.group(2)), num(m.group(3)), num(m.group(4))
    if price <= 0 or issued <= 0:
        raise ValueError("주가와 발행주식수는 0보다 커야 합니다.\n" + USAGE)
    if treasury >= issued:
        raise ValueError("자기주식수가 발행주식수보다 크거나 같습니다.\n" + USAGE)
    return {"code": m.group(1), "price": price, "issued": issued, "treasury": treasury}


def pending_messages(client, channel, bot_user_id):
    # 실행 서버의 시계가 틀어져 있을 수 있어서, 기간 기준을 서버 시각이 아니라
    # '슬랙의 가장 최근 메시지 시각'으로 잡습니다. (oldest 파라미터는 쓰지 않음)
    msgs, cursor, cutoff = [], None, None
    for _page in range(5):
        # 마켓플레이스 미등록 앱은 슬랙 정책상 한 번에 15개까지만 조회 가능
        resp = client.conversations_history(channel=channel, limit=15, cursor=cursor)
        page = resp["messages"]
        if page and cutoff is None:
            newest = float(page[0]["ts"])
            cutoff = newest - C.LOOKBACK_HOURS * 3600
            skew = time.time() - newest
            if abs(skew) > 3600 * 24:
                print(f"[알림] 실행 서버 시계가 슬랙과 {skew / 3600:+.1f}시간 차이 납니다(무시하고 진행)")
        msgs.extend(m for m in page if float(m["ts"]) >= cutoff)
        cursor = (resp.get("response_metadata") or {}).get("next_cursor")
        if not cursor or not resp.get("has_more") or (page and float(page[-1]["ts"]) < cutoff):
            break
        time.sleep(1)
    print(f"[슬랙] 채널에서 받은 메시지 {len(msgs)}개")
    out = []
    for m in msgs:
        if m.get("subtype") or m.get("bot_id"):
            continue
        if any(r["name"] in DONE and bot_user_id in r.get("users", []) for r in m.get("reactions", [])):
            continue
        out.append(m)
    return sorted(out, key=lambda m: float(m["ts"]))


def react(client, channel, ts, name):
    try:
        client.reactions_add(channel=channel, timestamp=ts, name=name)
    except Exception as e:   # already_reacted 등은 무시
        if "already_reacted" not in str(e):
            print(f"[warn] 리액션 실패 {name}: {e}")


def reply(client, channel, ts, text):
    client.chat_postMessage(channel=channel, thread_ts=ts, text=text)


def upload(client, channel, ts, path, comment):
    client.files_upload_v2(channel=channel, thread_ts=ts, file=path,
                           filename=path.split("/")[-1], initial_comment=comment)
