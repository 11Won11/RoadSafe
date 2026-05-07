"""
Feature Engineering 모듈
(grid_id, datetime) 단위로 시간/기상/인구/사고이력 feature 조립
"""
import numpy as np
import pandas as pd


def add_temporal(df: pd.DataFrame, col: str = "datetime") -> pd.DataFrame:
    """시간 관련 feature 추가 (순환 인코딩, 요일, 출퇴근)"""
    h = df[col].dt.hour
    df["hour_sin"]  = np.sin(2 * np.pi * h / 24)
    df["hour_cos"]  = np.cos(2 * np.pi * h / 24)
    df["dow"]       = df[col].dt.dayofweek
    df["is_weekend"]= (df["dow"] >= 5).astype(int)
    df["is_rush"]   = h.isin([7, 8, 9, 17, 18, 19]).astype(int)
    return df


def add_weather(df: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """기상 feature 추가 (강수 여부, 풍속 등급)"""
    w = weather.copy()
    w["is_rain"]    = (w["rain"].astype(float) > 0).astype(int)
    w["wind_grade"] = pd.cut(
        w["wind"].astype(float),
        bins=[0, 3, 8, 14, np.inf], labels=[0, 1, 2, 3]
    ).astype(int)
    return df.merge(
        w[["datetime", "rain", "temp", "wind", "is_rain", "wind_grade"]],
        on="datetime", how="left"
    )


def add_accident_history(
    df: pd.DataFrame,
    taas: pd.DataFrame,
    window_days: int = 90
) -> pd.DataFrame:
    """격자별 최근 N일 사고 건수 (이력 feature)"""
    cutoff = taas["datetime"].max() - pd.Timedelta(days=window_days)
    hist = (taas[taas["datetime"] >= cutoff]
            .groupby("grid_id").size()
            .rename(f"acc_hist_{window_days}d"))
    return df.merge(hist, on="grid_id", how="left").fillna(
        {f"acc_hist_{window_days}d": 0}
    )


def add_population_change(df: pd.DataFrame) -> pd.DataFrame:
    """격자별 직전 1시간 대비 유동인구 변화율"""
    df = df.sort_values(["grid_id", "datetime"])
    df["pop_change_rate"] = (
        df.groupby("grid_id")["population"]
          .pct_change()
          .fillna(0)
          .clip(-2, 2)
    )
    return df
