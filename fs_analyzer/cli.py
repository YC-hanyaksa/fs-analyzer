"""로컬 실행: 슬랙 없이 엑셀만 생성

사용: DART_API_KEY=xxx python -m fs_analyzer.cli 005930 75000 5969782550 0
"""
import os
import sys

from .dart_client import DartClient
from .pipeline import run_analysis, slack_summary
from .slack_io import parse_request


def main():
    req = parse_request(" ".join(sys.argv[1:]))
    if not req:
        sys.exit("사용: python -m fs_analyzer.cli 종목코드 주가 발행주식수 [자기주식수]")
    dart = DartClient(os.environ["DART_API_KEY"])
    rep, path = run_analysis(dart, req["code"], req["price"], req["issued"], req["treasury"], "output")
    print(slack_summary(rep))
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
