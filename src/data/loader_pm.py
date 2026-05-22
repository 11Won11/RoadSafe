"""
PM 사고 데이터 로더 — 전국 광역시 통합 버전
- 전국 광역시 xlsx 파일 전부 읽어 학습에 활용 (데이터 풀 확장)
- 서울 데이터는 별도로 분리하여 음성 샘플 생성 및 지도 서비스에 사용
"""
import pandas as pd
import logging
import unicodedata
from pathlib import Path

log = logging.getLogger(__name__)

# 전국 광역시 통합 xlsx 파일 (학습용 전체 데이터)
NATIONWIDE_DIR = Path("data/raw")
NATIONWIDE_SUFFIX = "_통합_2021-2024.xlsx"  # 파일명 suffix 기준으로 필터

# 서울 단독 CSV (음성 샘플 생성 및 시각화용)
SEOUL_CSV = Path("data/raw/서울특별시_2021-2024.csv")

# 도시명 추출을 위한 매핑 (파일명 → 도시 코드)
CITY_MAP = {
    "서울": "seoul",
    "부산": "busan",
    "대구": "daegu",
    "인천": "incheon",
    "광주": "gwangju",
    "대전": "daejeon",
    "울산": "ulsan",
    "세종": "sejong",
}


def _load_xlsx(path: Path, city_name: str) -> pd.DataFrame:
    """단일 xlsx 파일 로드 후 표준 컬럼 보정"""
    df = pd.read_excel(path)
    df["city"] = city_name

    # 컬럼명 통일 (파일마다 약간 다를 수 있음)
    rename_map = {
        "발생연도": "발생연도",
        "발생월": "발생월",
    }
    for old, new in rename_map.items():
        if old in df.columns and new not in df.columns:
            df.rename(columns={old: new}, inplace=True)

    return df


def load_pm_data(nationwide: bool = True) -> pd.DataFrame:
    """
    PM 사고 데이터를 로드하여 전처리된 DataFrame 반환.

    Args:
        nationwide: True이면 전국 광역시 xlsx 전체 로드 (모델 학습용),
                    False이면 서울 CSV만 로드 (음성 샘플·시각화 전용).

    Returns:
        is_hotspot=1, is_severe, is_daytime, city 컬럼 포함된 DataFrame
    """
    dfs = []

    if nationwide:
        # ── 전국 광역시 xlsx 일괄 로드 (2021-2024) ───────────────
        xlsx_files = sorted([f for f in NATIONWIDE_DIR.glob("*.xlsx") if "2021-2024" in f.name])
        if not xlsx_files:
            log.warning(f"통합 xlsx 파일 없음. 서울 CSV로 폴백합니다.")
            nationwide = False
        else:
            for fpath in xlsx_files:
                city_key = fpath.stem.split("_")[0]
                city_key = unicodedata.normalize("NFC", city_key)
                city_code = CITY_MAP.get(city_key, city_key)
                df_city = _load_xlsx(fpath, city_code)
                log.info(f"{fpath.name}: {len(df_city)}행 ({city_code})")
                dfs.append(df_city)

        # ── 신규 2025년 CSV 일괄 로드 추가 ────────────────────────
        csv_2025_files = sorted([f for f in NATIONWIDE_DIR.glob("*-2025.csv")])
        for fpath in csv_2025_files:
            city_key = fpath.stem.split("-")[0].replace("광역시", "").replace("특별시", "")
            city_key = unicodedata.normalize("NFC", city_key)
            city_code = CITY_MAP.get(city_key, city_key)
            try:
                df_city_25 = pd.read_csv(fpath, encoding="utf-8")
                df_city_25["city"] = city_code
                log.info(f"{fpath.name}: {len(df_city_25)}행 ({city_code} 2025년)")
                dfs.append(df_city_25)
            except Exception as e:
                log.error(f"2025 데이터 로드 실패 ({fpath}): {e}")

    if not nationwide or not dfs:
        # ── 서울 CSV 폴백 ─────────────────────────────────────────
        if SEOUL_CSV.exists():
            df = pd.read_csv(SEOUL_CSV, encoding="utf-8")
            df["city"] = "seoul"
            log.info(f"{SEOUL_CSV.name}: {len(df)}행 (서울 CSV 폴백)")
            dfs.append(df)
        else:
            raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {NATIONWIDE_DIR}")

    df = pd.concat(dfs, ignore_index=True)
    log.info(f"합산 총 행수: {len(df)}")

    # ── 타겟 변수 생성 ──────────────────────────────────────────
    df["is_hotspot"] = 1
    df["is_severe"] = ((df["사망자수"] > 0) | (df["중상자수"] > 0)).astype(int)
    df["is_daytime"] = (df["주야"] == "주간").astype(int)

    # ── 도시 원-핫 인코딩 (모델 Feature용) ──────────────────────
    city_dummies = pd.get_dummies(df["city"], prefix="city")
    df = pd.concat([df, city_dummies], axis=1)

    # ── 위도/경도 정리 ────────────────────────────────────────────
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["위도", "경도"])
    if len(df) < before:
        log.warning(f"좌표 결측 제거: {before - len(df)}행")

    # 도시별 현황
    log.info("도시별 샘플 수:\n" + df["city"].value_counts().to_string())
    log.info(f"최종 양성 샘플: {len(df)}건 (주간 {df['is_daytime'].sum()} / 야간 {(df['is_daytime']==0).sum()})")
    return df


def load_seoul_only() -> pd.DataFrame:
    """서울 데이터만 반환 — 음성 샘플 생성 및 시각화에 사용"""
    return load_pm_data(nationwide=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    df = load_pm_data(nationwide=True)
    print(df[["city", "위도", "경도", "is_hotspot", "is_daytime"]].head())
    print(f"\n도시별:\n{df['city'].value_counts()}")

