"""
loader.py 단위 테스트
실행: python -m pytest tests/test_loader.py -v
"""
import json
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
from shapely.geometry import box

# 테스트 대상 임포트
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
from src.data.loader import (
    load_taas,
    load_weather,
    load_population,
    merge_all,
    _WEATHER_CATS,
)


# ---------------------------------------------------------------------------
# 픽스처: 임시 파일 생성 헬퍼
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_taas(tmp_path) -> Path:
    """유효한 TAAS CSV 픽스처"""
    p = tmp_path / "taas.csv"
    p.write_text(
        textwrap.dedent("""\
        사고일시,사고유형대분류,위도,경도,사망자수,부상자수
        2024-05-01 09:00,개인형이동장치,37.5665,126.9780,0,1
        2024-05-01 10:00,개인형이동장치,37.5700,126.9800,0,2
        2024-05-01 10:00,개인형이동장치,37.5700,126.9800,0,2
        2024-05-01 11:00,승용차,37.5600,126.9700,1,0
        """),
        encoding="utf-8-sig",
    )
    return p


@pytest.fixture
def tmp_weather(tmp_path) -> Path:
    """유효한 기상 JSON 픽스처 (표준 API 응답 구조)"""
    items = [
        {"baseDate": "20240501", "baseTime": "0900", "category": cat,
         "obsrValue": str(val)}
        for cat, val in [("T1H","20.5"),("RN1","0"),("WSD","3.2"),
                         ("REH","60"),("PTY","0")]
    ]
    raw = {"response": {"body": {"items": {"item": items}}}}
    p = tmp_path / "weather.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    return p


@pytest.fixture
def tmp_population(tmp_path) -> Path:
    """유효한 생활인구 CSV 픽스처"""
    p = tmp_path / "population.csv"
    p.write_text(
        textwrap.dedent("""\
        격자ID,기준일시,총생활인구수
        G001,2024-05-01 09:00,1500
        G001,2024-05-01 10:00,1800
        G002,2024-05-01 09:00,500
        G002,2024-05-01 10:00,-10
        """),
        encoding="utf-8-sig",
    )
    return p


@pytest.fixture
def dummy_grid() -> gpd.GeoDataFrame:
    """서울 중심부 2×2 격자 픽스처 (EPSG:4326)"""
    cells = [
        box(126.97, 37.56, 126.98, 37.57),
        box(126.98, 37.56, 126.99, 37.57),
        box(126.97, 37.57, 126.98, 37.58),
        box(126.98, 37.57, 126.99, 37.58),
    ]
    grid = gpd.GeoDataFrame(geometry=cells, crs="EPSG:4326")
    grid["grid_id"] = [0, 1, 2, 3]
    grid["centroid_x"] = grid.geometry.centroid.x
    grid["centroid_y"] = grid.geometry.centroid.y
    return grid


# ---------------------------------------------------------------------------
# load_taas 테스트
# ---------------------------------------------------------------------------

class TestLoadTaas:
    def test_returns_pm_only(self, tmp_taas):
        """PM 사고만 반환, 승용차 행 제외"""
        df = load_taas(str(tmp_taas))
        assert len(df) == 2   # 중복 제거 후 PM 사고 2건

    def test_deduplication(self, tmp_taas):
        """(datetime, lat, lon) 동일 행 중복 제거 확인"""
        df = load_taas(str(tmp_taas))
        assert df.duplicated(["datetime", "lat", "lon"]).sum() == 0

    def test_coordinate_columns(self, tmp_taas):
        df = load_taas(str(tmp_taas))
        assert "lat" in df.columns and "lon" in df.columns

    def test_invalid_coords_removed(self, tmp_path):
        """한국 영역 밖 좌표(위도 0) 제거 확인"""
        p = tmp_path / "bad.csv"
        p.write_text(
            "사고일시,사고유형대분류,위도,경도,사망자수,부상자수\n"
            "2024-05-01 09:00,개인형이동장치,0.0,0.0,0,1\n",
            encoding="utf-8-sig",
        )
        df = load_taas(str(p))
        assert len(df) == 0

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_taas("non_existent.csv")


# ---------------------------------------------------------------------------
# load_weather 테스트
# ---------------------------------------------------------------------------

class TestLoadWeather:
    def test_returns_dataframe(self, tmp_weather):
        df = load_weather(str(tmp_weather))
        assert isinstance(df, pd.DataFrame)
        assert "datetime" in df.columns

    def test_standard_columns_present(self, tmp_weather):
        df = load_weather(str(tmp_weather))
        for col in ("temp", "rain", "wind", "humidity"):
            assert col in df.columns, f"{col} 컬럼 없음"

    def test_missing_category_gets_nan_column(self, tmp_path):
        """visibility 카테고리 없어도 NaN 컬럼으로 추가"""
        items = [
            {"baseDate": "20240501", "baseTime": "0900",
             "category": "T1H", "obsrValue": "20.0"}
        ]
        raw = {"response": {"body": {"items": {"item": items}}}}
        p = tmp_path / "w.json"
        p.write_text(json.dumps(raw))
        df = load_weather(str(p))
        assert "visibility" in df.columns

    def test_rain_string_converted(self, tmp_path):
        """'강수없음' 문자열 → 0.0 변환"""
        items = [
            {"baseDate": "20240501", "baseTime": "0900",
             "category": "RN1", "obsrValue": "강수없음"},
            {"baseDate": "20240501", "baseTime": "0900",
             "category": "T1H", "obsrValue": "22.0"},
        ]
        raw = {"response": {"body": {"items": {"item": items}}}}
        p = tmp_path / "w2.json"
        p.write_text(json.dumps(raw))
        df = load_weather(str(p))
        assert df["rain"].iloc[0] == 0.0


# ---------------------------------------------------------------------------
# load_population 테스트
# ---------------------------------------------------------------------------

class TestLoadPopulation:
    def test_negative_population_clipped(self, tmp_population):
        """음수 인구 → 0 클리핑 확인"""
        df = load_population(str(tmp_population))
        assert (df["population"] >= 0).all()

    def test_time_gap_filled_with_zero(self, tmp_population):
        """시간 구멍(11:00 등) → 0 채우기 확인"""
        df = load_population(str(tmp_population))
        # 09:00, 10:00 사이 gap은 없지만 구조 확인
        assert df["population"].isna().sum() == 0

    def test_required_columns(self, tmp_population):
        df = load_population(str(tmp_population))
        for col in ("grid_id", "datetime", "population"):
            assert col in df.columns


# ---------------------------------------------------------------------------
# merge_all 테스트
# ---------------------------------------------------------------------------

class TestMergeAll:
    def test_basic_merge(self, tmp_taas, tmp_weather, tmp_population, dummy_grid):
        taas = load_taas(str(tmp_taas))
        weather = load_weather(str(tmp_weather))
        pop = load_population(str(tmp_population))
        # dummy_grid는 EPSG:4326이므로 crs_proj=4326으로 테스트
        result = merge_all(taas, weather, pop, dummy_grid, crs_proj=4326)
        assert isinstance(result, pd.DataFrame)
        assert "grid_id" in result.columns
        assert "population" in result.columns

    def test_no_negative_population_after_merge(
        self, tmp_taas, tmp_weather, tmp_population, dummy_grid
    ):
        taas = load_taas(str(tmp_taas))
        weather = load_weather(str(tmp_weather))
        pop = load_population(str(tmp_population))
        result = merge_all(taas, weather, pop, dummy_grid, crs_proj=4326)
        assert (result["population"] >= 0).all()
