"""
서울 전체를 500m×500m 격자로 분할
EPSG:5186 (한국 평면직각좌표 - 미터 단위)으로 투영 후 격자 생성
"""
import numpy as np
import geopandas as gpd
from shapely.geometry import box


def create_seoul_grid(
    boundary_path: str = "data/raw/seoul_boundary.shp",
    cell_size: int = 500,
    crs_proj: int = 5186,
) -> gpd.GeoDataFrame:
    """
    서울 경계 shapefile 기준 500m×500m 격자 생성

    Returns:
        grid_id, centroid_x, centroid_y, geometry 컬럼 포함 GeoDataFrame
    """
    seoul = gpd.read_file(boundary_path).to_crs(epsg=crs_proj)
    minx, miny, maxx, maxy = seoul.total_bounds

    xs = np.arange(minx, maxx, cell_size)
    ys = np.arange(miny, maxy, cell_size)

    cells = [
        box(x, y, x + cell_size, y + cell_size)
        for x in xs for y in ys
    ]
    grid = gpd.GeoDataFrame(geometry=cells, crs=f"EPSG:{crs_proj}")

    # 서울 경계와 교차하는 격자만 유지
    seoul_union = seoul.union_all()
    grid = grid[grid.intersects(seoul_union)].reset_index(drop=True)
    grid["grid_id"]    = grid.index
    grid["centroid_x"] = grid.geometry.centroid.x
    grid["centroid_y"] = grid.geometry.centroid.y

    print(f"✓ 격자 생성 완료: {len(grid):,}개 ({cell_size}m×{cell_size}m)")
    return grid
