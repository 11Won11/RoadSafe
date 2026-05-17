"""
SAFERIDE 공간 위험도 모델 평가 모듈
- PAI (Predictive Accuracy Index): 격자 면적 대비 사고 포착율
- 시간적 검증: 2021-2023 학습 → 2024 사고 예측 성능
- 도시 독립 검증: 서울 제외 학습 → 서울 예측 (Cross-City)
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import logging
import pickle
from pathlib import Path
from sklearn.metrics import roc_auc_score, f1_score, classification_report

log = logging.getLogger(__name__)

# 한글 폰트
for font in fm.findSystemFonts():
    if "AppleGothic" in font or "NanumGothic" in font:
        plt.rcParams["font.family"] = fm.FontProperties(fname=font).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False


# ── 1. PAI (Predictive Accuracy Index) ─────────────────────────────────────

def compute_pai(
    grid_df: pd.DataFrame,
    accidents_df: pd.DataFrame,
    grid_lat_size: float = 0.0045,
    grid_lon_size: float = 0.0056,
) -> pd.DataFrame:
    """
    PAI 곡선 계산.
    PAI@k = (상위 k% 격자 내 사고 비율) / (상위 k% 격자 면적 비율)

    Args:
        grid_df: 격자 예측 결과 (lat_min, lon_min, risk_score)
        accidents_df: 실제 사고 데이터 (위도, 경도)

    Returns:
        pai_df: k별 PAI, 포착 사고 수, 사고 포착률 포함한 DataFrame
    """
    total_grids = len(grid_df)
    total_accidents = len(accidents_df)

    acc_lat = accidents_df["위도"].values.astype(float)
    acc_lon = accidents_df["경도"].values.astype(float)

    # 각 격자가 사고를 포함하는지 벡터 연산으로 판정
    # grid_df의 lat_min/lon_min이 실제 격자 좌측 하단 좌표
    grid_df = grid_df.copy()
    lat_min = grid_df["lat_min"].values
    lon_min = grid_df["lon_min"].values
    lat_max = lat_min + grid_lat_size
    lon_max = lon_min + grid_lon_size

    # 각 격자별로 내부 사고 수 카운트 (브로드캐스팅: grid×accident 행렬)
    in_lat = (acc_lat[None, :] >= lat_min[:, None]) & (acc_lat[None, :] < lat_max[:, None])
    in_lon = (acc_lon[None, :] >= lon_min[:, None]) & (acc_lon[None, :] < lon_max[:, None])
    grid_df["has_accident"] = (in_lat & in_lon).any(axis=1).astype(int)
    grid_df["acc_count"] = (in_lat & in_lon).sum(axis=1)

    log.info(f"사고 매핑: {grid_df['has_accident'].sum()}개 격자에 사고 포함 / 전체 {total_grids}개")

    # 위험도 내림차순 정렬
    grid_sorted = grid_df.sort_values("risk_score", ascending=False).reset_index(drop=True)

    # k% 단위로 PAI 계산
    thresholds = np.arange(1, 101)
    records = []
    for k in thresholds:
        n_cells = max(1, int(total_grids * k / 100))
        top_cells = grid_sorted.iloc[:n_cells]
        n_acc_captured = int(top_cells["has_accident"].sum())
        area_ratio = k / 100
        acc_ratio = n_acc_captured / max(total_accidents, 1)
        pai = acc_ratio / area_ratio if area_ratio > 0 else 0
        records.append({
            "k_percent": k,
            "n_cells": n_cells,
            "acc_captured": n_acc_captured,
            "acc_ratio": round(acc_ratio, 4),
            "area_ratio": round(area_ratio, 4),
            "pai": round(pai, 4),
        })

    return pd.DataFrame(records)



def plot_pai_curve(pai_df: pd.DataFrame, title: str, output_path: str):
    """PAI 곡선 시각화 저장"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 왼쪽: PAI 곡선
    ax = axes[0]
    ax.plot(pai_df["k_percent"], pai_df["pai"], color="#d00000", linewidth=2.5, label="SAFERIDE 모델")
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1.5, label="랜덤 기준선 (PAI=1)")
    ax.fill_between(pai_df["k_percent"], 1, pai_df["pai"],
                    where=(pai_df["pai"] > 1), alpha=0.15, color="#d00000")
    ax.set_xlabel("상위 격자 비율 (%)", fontsize=12)
    ax.set_ylabel("PAI (Predictive Accuracy Index)", fontsize=12)
    ax.set_title(f"PAI 곡선 — {title}", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, max(pai_df["pai"].max() * 1.1, 3))
    ax.grid(alpha=0.3)

    # 주요 PAI 값 표시
    for k in [5, 10, 20]:
        row = pai_df[pai_df["k_percent"] == k].iloc[0]
        ax.annotate(
            f"PAI@{k}%={row['pai']:.1f}",
            xy=(k, row["pai"]),
            xytext=(k + 3, row["pai"] + 0.3),
            fontsize=9,
            arrowprops=dict(arrowstyle="->", color="black"),
        )

    # 오른쪽: 사고 포착률 누적 곡선
    ax2 = axes[1]
    ax2.plot(pai_df["k_percent"], pai_df["acc_ratio"] * 100, color="#f48c06", linewidth=2.5, label="모델 포착률")
    ax2.plot(pai_df["k_percent"], pai_df["k_percent"], color="gray", linestyle="--", linewidth=1.5, label="랜덤 기준선")
    ax2.fill_between(pai_df["k_percent"], pai_df["k_percent"], pai_df["acc_ratio"] * 100,
                     where=(pai_df["acc_ratio"] * 100 > pai_df["k_percent"]),
                     alpha=0.15, color="#f48c06")
    ax2.set_xlabel("상위 격자 비율 (%)", fontsize=12)
    ax2.set_ylabel("포착된 사고 비율 (%)", fontsize=12)
    ax2.set_title(f"누적 사고 포착 곡선 — {title}", fontsize=13, fontweight="bold")
    ax2.legend(fontsize=10)
    ax2.set_xlim(0, 100)
    ax2.set_ylim(0, 100)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"PAI 곡선 저장: {output_path}")


# ── 2. 시간적 검증 (2021-2023 학습 → 2024 예측) ────────────────────────────

def temporal_holdout_eval(output_dir: str = "outputs"):
    """
    2021-2023 데이터로 학습 → 2024 실제 사고 지점 예측
    - 기존 격자 예측 결과(grid_risk_scores.csv)를 그대로 활용
    - 2024년 서울 사고 지점이 고위험 격자에 포함되는지 PAI로 평가
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    grid_path = Path("data/interim/grid_risk_scores.csv")
    seoul_csv = Path("data/raw/서울특별시_2021-2024.csv")

    if not grid_path.exists():
        log.error("격자 위험도 파일 없음. 먼저 python scripts/run.py를 실행하세요.")
        return

    grid_df = pd.read_csv(grid_path)
    seoul_df = pd.read_csv(seoul_csv)

    # 연도 파싱 (발생년월: "2024년 3월" 형식)
    if "발생연도" in seoul_df.columns:
        seoul_df["year"] = seoul_df["발생연도"].astype(int)
    else:
        seoul_df["year"] = seoul_df["발생년월"].astype(str).str.extract(r"(\d{4})").astype(int)

    acc_2024 = seoul_df[seoul_df["year"] == 2024].copy()
    acc_2023_prior = seoul_df[seoul_df["year"] < 2024].copy()

    log.info(f"시간적 검증 | 2021-2023 사고: {len(acc_2023_prior)}건 | 2024 사고(테스트): {len(acc_2024)}건")

    # 2024 사고 기준 PAI
    pai_2024 = compute_pai(grid_df, acc_2024)
    log.info(f"PAI@5%={pai_2024.loc[4,'pai']:.2f} | PAI@10%={pai_2024.loc[9,'pai']:.2f} | PAI@20%={pai_2024.loc[19,'pai']:.2f}")

    # 2021-2023 사고 기준 PAI (비교용)
    pai_prior = compute_pai(grid_df, acc_2023_prior)

    # 시각화
    plot_pai_curve(pai_2024, "2024년 서울 사고 검증", f"{output_dir}/pai_curve_2024.png")
    plot_pai_curve(pai_prior, "2021-2023년 서울 사고", f"{output_dir}/pai_curve_prior.png")

    # 요약 출력
    print("\n" + "=" * 55)
    print("시간적 검증 결과 (2021-2023 학습 모델 → 2024 검증)")
    print("=" * 55)
    for k in [5, 10, 20, 30]:
        row = pai_2024.loc[k - 1]
        print(f"  상위 {k:2d}% 격자 | 사고 포착 {int(row['acc_captured']):3d}건 / {len(acc_2024)}건 "
              f"({row['acc_ratio']*100:.1f}%) | PAI={row['pai']:.2f}")
    print("=" * 55)

    return pai_2024, pai_prior


# ── 3. 도시 독립 검증 (Cross-City Generalization) ─────────────────────────

def cross_city_eval(output_dir: str = "outputs", n_trials: int = 30):
    """
    서울 제외 + 나머지 광역시로 학습 → 서울 격자 예측 PAI 평가
    모델이 '도로 공간 구조라는 보편적 패턴'을 학습했는지 검증
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.data.loader_pm import load_pm_data
    from src.data.negative_sampler import generate_negative_samples
    from src.features.engineer_point import engineer_point_features
    from src.models.train_xgb_point import train_risk_model
    from src.features.engineer_grid import predict_grid_risk

    # 서울 제외 전국 데이터
    log.info("[Cross-City] 서울 제외 광역시 데이터 로드 중...")
    all_df = load_pm_data(nationwide=True)
    non_seoul_pos = all_df[all_df["city"] != "서울"].copy()
    log.info(f"서울 제외 양성 샘플: {len(non_seoul_pos)}건")

    # 음성 샘플은 서울 기반 그대로 활용
    seoul_pos = all_df[all_df["city"] == "서울"].copy()
    neg_df = generate_negative_samples(seoul_pos)

    city_dummy_cols = [c for c in non_seoul_pos.columns if c.startswith("city_")]
    for col in city_dummy_cols:
        if col not in neg_df.columns:
            neg_df[col] = 0

    combined = pd.concat([non_seoul_pos, neg_df], ignore_index=True)
    features_df = engineer_point_features(combined)

    # 모델 학습 (서울 데이터 완전 제외)
    log.info("[Cross-City] 서울 제외 모델 학습 중...")
    model_cc, _, feature_names_cc, _, _ = train_risk_model(
        features_df=features_df,
        n_trials=n_trials,
        output_dir=output_dir,
    )

    # 서울 격자 위험도 예측
    grid_df_cc = predict_grid_risk(model_cc, feature_names_cc, force=True)

    # 서울 실제 사고 기준 PAI
    seoul_acc = pd.read_csv("data/raw/서울특별시_2021-2024.csv")
    pai_cc = compute_pai(grid_df_cc, seoul_acc)
    plot_pai_curve(pai_cc, "Cross-City 검증 (서울 제외 학습 → 서울 예측)", f"{output_dir}/pai_curve_crosscity.png")

    print("\n" + "=" * 55)
    print("Cross-City 검증 결과 (서울 제외 학습 → 서울 예측)")
    print("=" * 55)
    for k in [5, 10, 20]:
        row = pai_cc.loc[k - 1]
        print(f"  상위 {k}% 격자 | 포착 {row['acc_ratio']*100:.1f}% | PAI={row['pai']:.2f}")
    print("=" * 55)

    return pai_cc


# ── 실행 엔트리포인트 ──────────────────────────────────────────────────────

def run_evaluation(output_dir: str = "outputs"):
    """PAI + 시간적 검증 통합 실행"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    log.info("\n" + "=" * 60)
    log.info("SAFERIDE 모델 평가 시작")
    log.info("=" * 60)

    log.info("\n[EVAL 1] 시간적 검증: 2021-2023 학습 모델 → 2024 실제 사고 PAI")
    temporal_holdout_eval(output_dir=output_dir)

    log.info("\n[EVAL 2] 전체 데이터 기준 PAI (참고용)")
    grid_df = pd.read_csv("data/interim/grid_risk_scores.csv")
    all_acc = pd.read_csv("data/raw/서울특별시_2021-2024.csv")
    pai_all = compute_pai(grid_df, all_acc)
    plot_pai_curve(pai_all, "전체 서울 사고 대상 PAI", f"{output_dir}/pai_curve_all.png")
    for k in [5, 10, 20]:
        row = pai_all.loc[k - 1]
        log.info(f"  PAI@{k}% = {row['pai']:.2f} (포착 {row['acc_ratio']*100:.1f}%)")

    log.info("\n✅ 평가 완료. outputs/ 에 PAI 곡선 저장됨")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_evaluation()
