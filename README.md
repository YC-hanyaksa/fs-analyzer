# 재무제표 자동 분석 봇

슬랙 채널에 `종목코드 주가 발행주식수 [자기주식수]`를 올리면, GitHub Actions가 DART에서 최근 5년 사업보고서(연결·별도)를 받아 분석하고 엑셀 파일을 해당 메시지 스레드에 올립니다.

```
005930 75000 5969782550 0
```

처리 상태는 메시지에 붙는 이모지로 확인합니다: 👀 처리 중 → ✅ 완료 / ❌ 실패(스레드에 사유)

---

## 설치 순서

### 1단계. 동작 확인 (키 없이)
```bash
pip install -r requirements.txt
python -m fs_analyzer.demo
```
`output/` 폴더에 가상 회사 '데모반도체' 엑셀이 생기면 정상입니다.

### 2단계. 실제 DART 데이터로 로컬 테스트
```bash
DART_API_KEY=발급받은키 python -m fs_analyzer.cli 005930 75000 5969782550 0
```
- 엑셀의 `원본데이터` 시트에서 **"사용한 DART 계정명"** 열이 빨간 "(매칭 실패)"인 항목이 있는지 확인하세요.
- 매칭 실패 항목은 `fs_analyzer/accounts.py`의 계정명 후보에 추가하면 됩니다.

### 3단계. 슬랙 앱 만들기
1. https://api.slack.com/apps → **Create New App** → From scratch
2. **OAuth & Permissions → Bot Token Scopes**에 추가
   - `channels:history` (비공개 채널이면 `groups:history`)
   - `chat:write`, `files:write`, `reactions:write`
3. **Install to Workspace** → `xoxb-`로 시작하는 Bot Token 복사
4. 분석 요청용 채널을 만들고 채널에서 `/invite @앱이름`
5. 채널 이름 클릭 → 맨 아래 **채널 ID**(C로 시작) 복사

### 4단계. GitHub 설정
1. 이 폴더를 저장소에 올립니다 (`.github/workflows/fs-analyzer.yml` 포함).
2. **Settings → Secrets and variables → Actions**에 추가
   - `DART_API_KEY`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
3. 채널에 요청 메시지를 올린 뒤 **Actions 탭 → 재무제표 분석 봇 → Run workflow**로 즉시 테스트

---

## 실행 주기와 Actions 사용량
- 기본: KST 07:00~23:59, **20분 간격** (응답까지 최대 20분+ 지연, GitHub 스케줄 특성상 더 늦을 수 있음)
- 요청이 없으면 몇 초 만에 종료되지만 **실행 1회당 최소 1분으로 과금**됩니다.
- 현재 설정은 월 약 1,500분 사용. **비공개 저장소 무료 한도는 월 2,000분**이고 다른 워크플로와 합산되니 확인하세요. 공개 저장소는 무제한입니다.
- 간격은 workflow 파일의 `cron`에서 바꿀 수 있습니다.

## 기준값 바꾸기
판정 기준(자회사 의존도 70%, 자사주 5%, PER 구간 등)은 모두 `fs_analyzer/config.py`에 있습니다.

## 파일 구성
| 파일 | 역할 |
|---|---|
| `dart_client.py` | OpenDART API 호출 |
| `accounts.py` | 계정 매핑 표 (매칭 실패 시 여기에 계정명 추가) |
| `mapper.py` | DART 원본 → 표준 항목 |
| `analyzer.py` | 비율·경고·연결vs별도·밸류에이션·신호등·코멘트 |
| `excel_writer.py` | 엑셀 시트 생성 |
| `slack_io.py` | 슬랙 폴링·파싱·업로드 |
| `pipeline.py` | 전체 흐름 연결 |
| `main.py` / `cli.py` / `demo.py` | Actions용 / 로컬용 / 데모 |

## 알려진 제약
- 금융업(KSIC 64~66)은 분석 대상에서 제외됩니다.
- 이자비용·감가상각비가 본문에 없으면 대체값을 쓰거나 비워두고, 요약 시트 "데이터 메모"에 표시합니다.
- 배당금수익·지분법이익이 주석에만 있으면 연결vs별도 ③항목은 '-'로 나옵니다.
- 각 연도 값은 해당 연도 사업보고서의 당기 수치입니다(이후 재작성 반영 안 됨).
