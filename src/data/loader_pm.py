"""
Phase 2 데이터 로더
서울특별시 PM 사고 CSV (2021-2024) 로드 및 전처리
"""
import pandas as pd
import logging
from pathlib import Path

log = logging.getLogger(__name__)

DATA_FILES = [
    "data/raw/서울특별시_2021-2023.csv",
    "data/raw/서울특별시-2024.csv",
]

def load_pm_data() -> pd.DataFrame:
    """
    PM 사고 CSV 2개를 합산하여 전처리된 DataFrame 반환.
    - is_hotspot=1 (이진 분류 양성 샘플 레이블)
    - is_severe=1 (사망 or 중상 → 보조 심각도 레이블)
    - is_daytime=1 (주간), 0 (야간)
    """
    dfs = []
    for f in DATA_FILES:
        p = Path(f)
        if not p.exists():
            log.warning(f"파일 없음, 건너뜀: {f}")
            continue
        df = pd.read_csv(p, encoding="utf-8")
        log.info(f"{p.name} 로드: {len(df)}행")
        dfs.append(df)

    if not dfs:
        raise FileNotFoundError("PM 사고 CSV 파일을 찾을 수 없습니다. data/raw/ 폴더를 확인하세요.")

    df = pd.concat(dfs, ignore_index=True)
    log.info(f"합산 총 행수: {len(df)}")

    # ── 타겟 변수 생성 ──────────────────────────────────────────
    # 이진 분류용: 이 데이터는 전부 사고 지점이므로 양성(1) 레이블
    df["is_hotspot"] = 1

    # 심각도 보조 레이블 (사망 or 중상이면 1)
    df["is_severe"] = ((df["사망자수"] > 0) | (df["중상자수"] > 0)).astype(int)

    # 주/야간 플래그
    df["is_daytime"] = (df["주야"] == "주간").astype(int)

    # ── 컬럼 정리 ────────────────────────────────────────────────
    # 위도/경도 float 보장
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")

    # 결측 좌표 제거
    before = len(df)
    df = df.dropna(subset=["위도", "경도"])
    if len(df) < before:
        log.warning(f"좌표 결측 제거: {before - len(df)}행")

    log.info(f"최종 양성 샘플 수: {len(df)} (주간 {df['is_daytime'].sum()} / 야간 {(~df['is_daytime'].astype(bool)).sum()})")
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    df = load_pm_data()
    print(df[["위도", "경도", "주야", "기상상태", "도로형태", "is_hotspot", "is_severe", "is_daytime"]].head())
    print(f"\nis_severe 분포:\n{df['is_severe'].value_counts()}")
