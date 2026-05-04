"""
공간 교차검증 Splitter
KMeans 지리 블록 군집화 + GroupKFold로 공간 데이터 누수 방지
"""
import numpy as np
import geopandas as gpd
from sklearn.cluster import KMeans
from sklearn.model_selection import GroupKFold


def assign_spatial_blocks(
    grid: gpd.GeoDataFrame,
    n_blocks: int = 5,
    seed: int = 42,
) -> gpd.GeoDataFrame:
    """
    격자 중심좌표 기준 KMeans 클러스터링 → block 컬럼 추가
    블록 = GroupKFold의 group 레이블로 사용
    """
    coords = np.stack([grid["centroid_x"], grid["centroid_y"]], axis=1)
    km = KMeans(n_clusters=n_blocks, random_state=seed, n_init=10)
    grid = grid.copy()
    grid["block"] = km.fit_predict(coords)
    print(f"✓ {n_blocks}개 공간 블록 할당 완료")
    return grid


def spatial_kfold_splits(X, y, groups, n_splits: int = 5):
    """
    블록 기반 GroupKFold 제너레이터
    groups: 각 샘플의 block 번호 (격자 ID → block 매핑)
    """
    gkf = GroupKFold(n_splits=n_splits)
    for fold, (tr_idx, va_idx) in enumerate(gkf.split(X, y, groups)):
        print(f"Fold {fold+1}: train={len(tr_idx):,}  val={len(va_idx):,}")
        yield fold, tr_idx, va_idx
