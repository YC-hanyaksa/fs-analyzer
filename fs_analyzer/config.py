"""분석 기준값. 숫자만 바꾸면 판정 기준이 바뀝니다."""

# ── 기본 설정 ─────────────────────────────────────────
YEARS = 5                      # 분석 연도 수
UNIT = 100_000_000             # 금액 표시 단위 (억원)
UNIT_LABEL = "억원"
DEFAULT_TAX_RATE = 0.22        # ROIC 계산 시 실효세율을 못 구하면 쓰는 값

# ── 연결 vs 별도 판정 ─────────────────────────────────
SUB_DEPENDENCY_PCT = 70        # ① 자회사 이익 의존도가 이 % 이상이면 🔴
SEP_LOSS_MIN_YEARS = 2         # ② 별도 적자·연결 흑자가 이 연수 이상이면 🔴
DIVIDEND_DEPENDENCY_PCT = 50   # ③ 별도 순이익 중 배당·지분법 비중이 이 % 이상이면 🟡
CONS_WORSE_PCT = 30            # ⑦ 연결 영업이익이 별도보다 이 % 이상 낮으면 🟠

# ── 밸류에이션 ────────────────────────────────────────
TREASURY_WARN_PCT = 5          # 자기주식 비중 경고 기준(%)
PER_GREEN = 10                 # PER 이 값 미만 🟢
PER_YELLOW = 20                # PER 이 값 이하 🟡, 초과 🔴

# ── 경고 신호 ─────────────────────────────────────────
GROWTH_GAP_PCTP = 10           # 매출채권·재고 증가율이 매출 증가율보다 이 %p 이상 높으면 경고
INTEREST_COVERAGE_MIN = 1.0    # 이자보상배율 경고 기준
CONSEC_LOSS_YEARS = 2          # 영업적자·FCF 마이너스 연속 연수
DEBT_RATIO_JUMP_PCTP = 50      # 부채비율 전년 대비 급증 기준(%p)

# ── 신호등 기준 ───────────────────────────────────────
GROWTH_GREEN_CAGR = 5          # 매출 CAGR 이상이고 영업이익이 늘었으면 🟢
ROE_GREEN = 10
ROE_YELLOW = 5
STAB_GREEN = dict(debt_ratio=100, current_ratio=150, icr=5)
STAB_RED = dict(debt_ratio=200, current_ratio=100, icr=1.5)
CCC_YELLOW_DAYS = 10           # 최근 CCC가 과거 평균보다 이 일수 이상 늘면 🟡
CCC_RED_DAYS = 30              # 이 일수 이상 늘면 🔴

# ── 슬랙 ──────────────────────────────────────────────
LOOKBACK_HOURS = 48            # 이 시간 이내 메시지만 확인
