"""OpenDART API 클라이언트"""
import io
import time
import zipfile
import xml.etree.ElementTree as ET

import requests

BASE = "https://opendart.fss.or.kr/api"
ANNUAL = "11011"  # 사업보고서


class DartError(Exception):
    pass


class DartClient:
    def __init__(self, api_key, session=None):
        self.key = api_key
        self.s = session or requests.Session()
        self._corp_map = None

    def _get(self, path, **params):
        params["crtfc_key"] = self.key
        for attempt in range(3):
            try:
                r = self.s.get(f"{BASE}/{path}", params=params, timeout=60)
                r.raise_for_status()
                return r
            except requests.RequestException as e:
                if attempt == 2:
                    raise DartError(f"DART 요청 실패: {e}") from e
                time.sleep(2 * (attempt + 1))

    def corp_code(self, stock_code):
        """종목코드 → (고유번호, 회사명)"""
        if self._corp_map is None:
            r = self._get("corpCode.xml")
            try:
                zf = zipfile.ZipFile(io.BytesIO(r.content))
            except zipfile.BadZipFile:
                raise DartError("기업코드 목록을 받지 못했습니다. DART API 키를 확인하세요. "
                                f"응답: {r.text[:200]}")
            root = ET.fromstring(zf.read(zf.namelist()[0]))
            m = {}
            for el in root.iter("list"):
                sc = (el.findtext("stock_code") or "").strip()
                if sc:
                    m[sc] = (el.findtext("corp_code").strip(), el.findtext("corp_name").strip())
            self._corp_map = m
        if stock_code not in self._corp_map:
            raise DartError(f"종목코드 {stock_code}를 DART 상장사 목록에서 찾지 못했습니다.")
        return self._corp_map[stock_code]

    def company(self, corp_code):
        d = self._get("company.json", corp_code=corp_code).json()
        if d.get("status") != "000":
            raise DartError(f"기업개황 조회 실패({d.get('status')}): {d.get('message')}")
        return d

    def annual_statement(self, corp_code, year, fs_div):
        """사업보고서 전체 재무제표. 없으면 None. fs_div: CFS(연결) / OFS(별도)"""
        d = self._get("fnlttSinglAcntAll.json", corp_code=corp_code, bsns_year=str(year),
                      reprt_code=ANNUAL, fs_div=fs_div).json()
        st = d.get("status")
        if st == "000":
            return d.get("list", [])
        if st == "013":   # 조회된 데이터 없음
            return None
        raise DartError(f"DART 오류({st}): {d.get('message')}")
