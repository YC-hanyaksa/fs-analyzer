"""DART 계정 매핑 표.

표준 계정코드(account_id)를 먼저 찾고, 없으면 계정명(공백 제거 후 일치)으로 찾습니다.
회사별로 계정명이 달라 매칭이 안 되면 names 목록에 추가하면 됩니다.
"""

IS = ("IS", "CIS")
BS = ("BS",)
CF = ("CF",)

# key: (표시명, 재무제표 구분, 표준 계정코드 목록, 계정명 후보)
ACCOUNTS = {
    # 손익계산서
    "revenue": ("매출액", IS, ["ifrs-full_Revenue"],
                ["매출액", "매출", "수익(매출액)", "영업수익", "매출액(영업수익)"]),
    "cogs": ("매출원가", IS, ["ifrs-full_CostOfSales"], ["매출원가"]),
    "gross_profit": ("매출총이익", IS, ["ifrs-full_GrossProfit"],
                     ["매출총이익", "매출총이익(손실)"]),
    "op_income": ("영업이익", IS,
                  ["dart_OperatingIncomeLoss", "ifrs-full_ProfitLossFromOperatingActivities"],
                  ["영업이익", "영업이익(손실)", "영업손익"]),
    "finance_cost": ("금융비용", IS, ["ifrs-full_FinanceCosts"], ["금융비용", "금융원가"]),
    "interest_expense": ("이자비용", IS, ["ifrs-full_InterestExpense"], ["이자비용"]),
    "dividend_income": ("배당금수익", IS, ["ifrs-full_RevenueFromDividends"],
                        ["배당금수익", "배당수익"]),
    "equity_method": ("지분법이익", IS,
                      ["ifrs-full_ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod"],
                      ["지분법이익", "지분법손익", "지분법투자손익", "관계기업투자손익"]),
    "pretax": ("법인세차감전순이익", IS, ["ifrs-full_ProfitLossBeforeTax"],
               ["법인세비용차감전순이익", "법인세비용차감전순이익(손실)", "법인세차감전순이익"]),
    "tax": ("법인세비용", IS, ["ifrs-full_IncomeTaxExpenseContinuingOperations"],
            ["법인세비용", "법인세비용(수익)"]),
    "net_income": ("당기순이익", IS, ["ifrs-full_ProfitLoss"],
                   ["당기순이익", "당기순이익(손실)", "당기순손익"]),
    "ni_owner": ("지배주주순이익", IS, ["ifrs-full_ProfitLossAttributableToOwnersOfParent"],
                 ["지배기업소유주지분", "지배기업의소유주지분", "지배기업의소유주에게귀속되는당기순이익"]),
    "ni_nci": ("비지배지분순이익", IS, ["ifrs-full_ProfitLossAttributableToNoncontrollingInterests"],
               ["비지배지분", "비지배지분에귀속되는당기순이익"]),

    # 재무상태표
    "total_assets": ("자산총계", BS, ["ifrs-full_Assets"], ["자산총계"]),
    "current_assets": ("유동자산", BS, ["ifrs-full_CurrentAssets"], ["유동자산"]),
    "cash": ("현금및현금성자산", BS, ["ifrs-full_CashAndCashEquivalents"], ["현금및현금성자산"]),
    "st_fin": ("단기금융상품", BS, ["dart_ShortTermDepositsNotClassifiedAsCashEquivalents"],
               ["단기금융상품"]),
    "receivables": ("매출채권", BS,
                    ["dart_ShortTermTradeReceivable", "ifrs-full_CurrentTradeReceivables",
                     "ifrs-full_TradeAndOtherCurrentReceivables"],
                    ["매출채권", "매출채권및기타채권", "매출채권및기타유동채권", "단기매출채권"]),
    "inventories": ("재고자산", BS, ["ifrs-full_Inventories"], ["재고자산"]),
    "total_liabilities": ("부채총계", BS, ["ifrs-full_Liabilities"], ["부채총계"]),
    "current_liabilities": ("유동부채", BS, ["ifrs-full_CurrentLiabilities"], ["유동부채"]),
    "payables": ("매입채무", BS,
                 ["dart_ShortTermTradePayables", "ifrs-full_CurrentTradePayables",
                  "ifrs-full_TradeAndOtherCurrentPayables"],
                 ["매입채무", "매입채무및기타채무", "매입채무및기타유동채무", "단기매입채무"]),
    "total_equity": ("자본총계", BS, ["ifrs-full_Equity"], ["자본총계"]),
    "equity_owner": ("지배주주지분", BS, ["ifrs-full_EquityAttributableToOwnersOfParent"],
                     ["지배기업소유주지분", "지배기업의소유주지분", "지배기업의소유주에게귀속되는자본"]),

    # 현금흐름표
    "cfo": ("영업활동현금흐름", CF, ["ifrs-full_CashFlowsFromUsedInOperatingActivities"],
            ["영업활동현금흐름", "영업활동으로인한현금흐름", "영업활동순현금흐름"]),
    "capex_ppe": ("유형자산 취득", CF, ["ifrs-full_PurchaseOfPropertyPlantAndEquipment"],
                  ["유형자산의취득", "유형자산취득"]),
    "capex_intan": ("무형자산 취득", CF, ["ifrs-full_PurchaseOfIntangibleAssets"],
                    ["무형자산의취득", "무형자산취득"]),
    "depreciation": ("감가상각비", CF, ["ifrs-full_AdjustmentsForDepreciationExpense"],
                     ["감가상각비", "유형자산감가상각비"]),
    "amortization": ("무형자산상각비", CF, ["ifrs-full_AdjustmentsForAmortisationExpense"],
                     ["무형자산상각비"]),
    "interest_paid": ("이자의 지급", CF,
                      ["ifrs-full_InterestPaidClassifiedAsOperatingActivities",
                       "ifrs-full_InterestPaidClassifiedAsFinancingActivities"],
                      ["이자의지급", "이자지급"]),
    "dividends_paid": ("배당금 지급", CF, ["ifrs-full_DividendsPaidClassifiedAsFinancingActivities"],
                       ["배당금의지급", "배당금지급"]),
}

# 차입금(이자부부채) 합산 대상
DEBT_IDS = {
    "ifrs-full_ShorttermBorrowings", "ifrs-full_CurrentPortionOfLongtermBorrowings",
    "ifrs-full_LongtermBorrowings", "ifrs-full_BondsIssued",
    "ifrs-full_CurrentLeaseLiabilities", "ifrs-full_NoncurrentLeaseLiabilities",
}
DEBT_NAMES = {
    "단기차입금", "유동성장기차입금", "유동성장기부채", "유동성사채", "단기사채",
    "사채", "장기사채", "장기차입금", "전환사채", "교환사채",
    "유동리스부채", "비유동리스부채", "리스부채",
}
