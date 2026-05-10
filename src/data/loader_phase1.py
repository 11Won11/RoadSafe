import pandas as pd
import logging
from pathlib import Path

log = logging.getLogger(__name__)

def load_phase1_data(path: str) -> pd.DataFrame:
    """
    사고분석-지역별.xlsx 파일을 읽고 PM 사고만 필터링, 정제하여 반환합니다.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"데이터 파일 없음: {p.resolve()}")

    log.info("엑셀 파일 로드 중... (시간이 조금 걸릴 수 있습니다)")
    df = pd.read_excel(path, engine="openpyxl")
    
    initial_rows = len(df)
    log.info(f"초기 로드: {initial_rows}행")

    # 1. PM 관련 사고 필터링
    # 가해운전자 또는 피해운전자가 '개인형이동수단(PM)'인 경우
    pm_mask = (df['가해운전자 차종'].str.contains('개인형이동수단|PM', na=False)) | \
              (df['피해운전자 차종'].str.contains('개인형이동수단|PM', na=False))
    
    df_pm = df[pm_mask].copy()
    log.info(f"PM 사고 필터링 후: {len(df_pm)}행")

    # 2. '시군구'에서 '구' 추출 (예: '서울특별시 성북구' -> '성북구')
    df_pm['구'] = df_pm['시군구'].apply(lambda x: x.split()[1] if isinstance(x, str) and len(x.split()) > 1 else '알수없음')
    
    # 서울특별시 외 지역 제거 (시군구가 '서울특별시'로 시작하는 것만)
    df_pm = df_pm[df_pm['시군구'].str.startswith('서울특별시', na=False)]
    log.info(f"서울 지역 필터링 후: {len(df_pm)}행")

    # 3. 필요없는 컬럼 제거 및 타겟 변수 생성 준비
    # 사고심각도 생성 (사망/중상 -> 1 (고위험), 경상/부상신고 -> 0 (저위험))
    df_pm['is_severe'] = df_pm['사고내용'].apply(lambda x: 1 if x in ['사망사고', '중상사고'] else 0)

    return df_pm.reset_index(drop=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = load_phase1_data("사고분석-지역별.xlsx")
    print(df.head())
    print(f"\n심각도 분포:\n{df['is_severe'].value_counts()}")
    print(f"\n구별 사고 건수:\n{df['구'].value_counts().head()}")
