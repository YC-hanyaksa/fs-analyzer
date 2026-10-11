"""GitHub Actions 진입점: 슬랙 채널의 새 요청을 처리합니다.

필요 환경변수: DART_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
"""
import os
import sys
import tempfile
import traceback

from slack_sdk import WebClient

from .dart_client import DartClient, DartError
from .pipeline import NotSupported, run_analysis, slack_summary
from .slack_io import parse_request, pending_messages, react, reply, upload


def main():
    env = {k: (os.environ.get(k) or "").strip() for k in ("DART_API_KEY", "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID")}
    missing = [k for k, v in env.items() if not v]
    if missing:
        sys.exit(f"환경변수 누락: {', '.join(missing)}")
    for k in env:
        raw = os.environ[k]
        if raw != env[k]:
            print(f"[알림] {k} 값 앞뒤의 공백/줄바꿈 {len(raw) - len(env[k])}자를 제거했습니다")
    channel = env["SLACK_CHANNEL_ID"]
    slack = WebClient(token=env["SLACK_BOT_TOKEN"])
    me = slack.auth_test()
    bot_id = me["user_id"]
    # 채널 ID는 비밀값이 아니지만 GitHub가 Secret 값을 *** 로 가리므로 글자 사이를 띄워 출력
    print(f"[슬랙] 봇: {me.get('user')} ({bot_id}) / 워크스페이스: {me.get('team')}")
    print(f"[슬랙] 채널 ID: {' '.join(channel)} ({len(channel)}자)")

    msgs = pending_messages(slack, channel, bot_id)
    if not msgs:
        r = slack.conversations_history(channel=channel, limit=5)
        print(f"[진단] 기간 제한 없이 조회한 메시지: {len(r['messages'])}개")
    reqs = []
    for m in msgs:
        try:
            req = parse_request(m.get("text"))
        except ValueError as e:
            reply(slack, channel, m["ts"], f"⚠️ {e}")
            react(slack, channel, m["ts"], "x")
            continue
        if req:
            reqs.append((m, req))
        else:
            print(f"[무시] 요청 형식이 아닌 메시지: {m.get('text', '')[:60]!r}")
    if not reqs:
        print(f"처리할 요청 없음 (최근 메시지 {len(msgs)}개 확인)")
        return

    dart = DartClient(env["DART_API_KEY"])
    out_dir = tempfile.mkdtemp()
    for m, req in reqs:
        ts = m["ts"]
        react(slack, channel, ts, "eyes")
        try:
            rep, path = run_analysis(dart, req["code"], req["price"], req["issued"], req["treasury"], out_dir)
            upload(slack, channel, ts, path, slack_summary(rep))
            react(slack, channel, ts, "white_check_mark")
            print(f"완료: {req['code']} → {path}")
        except (DartError, NotSupported, ValueError) as e:
            reply(slack, channel, ts, f"⚠️ {req['code']} 분석 실패: {e}")
            react(slack, channel, ts, "x")
        except Exception as e:
            traceback.print_exc()
            reply(slack, channel, ts, f"❌ {req['code']} 처리 중 오류: {type(e).__name__}: {e}")
            react(slack, channel, ts, "x")


if __name__ == "__main__":
    main()
