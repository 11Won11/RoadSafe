# <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/Kick%20Scooter.png" alt="Kick Scooter" width="45" height="45" style="vertical-align: middle;"/> SAFERIDE — PM 사고 공간 위험도 예측 플랫폼

![Python](https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&logo=python)
![XGBoost](https://img.shields.io/badge/XGBoost-AUROC_0.896-red?style=for-the-badge)
![Optuna](https://img.shields.io/badge/Optuna-Bayesian_HPO-blue?style=for-the-badge)
![SHAP](https://img.shields.io/badge/SHAP-Explainable_AI-brightgreen?style=for-the-badge)
![OSMnx](https://img.shields.io/badge/OSMnx-Spatial_Feature-orange?style=for-the-badge)
![Folium](https://img.shields.io/badge/Folium-Grid_Heatmap-green?style=for-the-badge)

> **"사고가 나기 전에 위험한 공간을 먼저 바꿉니다."**
>
> SAFERIDE는 서울시 PM(개인형 이동장치) 사고 좌표 데이터와 도로망 공간 정보를 결합하여,
> **사고가 없었던 지점도 포함해** 서울 전역의 공간적 PM 사고 위험도를 0~100점으로 예측하는 AI 플랫폼입니다.

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/Rocket.png" alt="Rocket" width="30" height="30" style="vertical-align: middle;"/> 핵심 기술 및 성과

| 항목 | 내용 |
|---|---|
| **모델** | XGBoost 이진 분류 (사고 발생 지점 vs 비사고 지점) |
| **AUROC** | **0.896** (랜덤 예측 0.5 대비 대폭 향상) |
| **Accuracy / F1** | **82% / 0.82** (균형 잡힌 성능) |
| **데이터** | 서울시 PM 사고 2021–2024 (1,799건, 위도·경도 전수 보유) |
| **음성 샘플** | 3단계 매칭 샘플링으로 공간 편향 없이 비사고 지점 자동 생성 |
| **Feature** | OSMnx 기반 교차로 수(반경 100/200/500m), 도로 등급, 차선 수 등 지점 단위 정밀 공간 Feature |
| **시각화** | 서울 전체 6,528개 500m 격자 위험도 히트맵 (브라우저 대시보드) |

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Light%20Bulb.png" alt="Light Bulb" width="30" height="30" style="vertical-align: middle;"/> 주요 기능

### 🗺️ 1. 서울 전역 격자 위험도 히트맵
* 서울을 **500m × 500m 격자** 6,500여 개로 나눠 **사고가 없었던 지점도 예측**
* 초록(안전) → 노랑 → 주황 → 빨강(위험)의 직관적 색상 스케일
* 격자를 클릭하면 해당 구역의 **위험 요인 Top-5 (SHAP 값 기반 자동 해설)** 팝업 표시

### 🧠 2. SHAP 기반 설명 가능한 AI (XAI)
* 모델이 왜 이 지점을 위험하다고 판단했는지 **SHAP 값으로 정량화**
* Feature Importance Bar 차트 + 방향성 Dot 차트 자동 생성
* 보고서·발표 자료로 바로 활용 가능한 그래프 저장

### 🏗️ 3. OSMnx 기반 공간 Feature 자동 추출
* **외부 API 키 없이** OpenStreetMap에서 서울 전체 도로망을 파이썬이 자동 다운로드
* 각 지점 기준 반경 100m / 200m / 500m 내 교차로 수, 최근접 교차로 거리, 도로 등급, 차선 수 등 추출
* 최초 실행 후 `data/interim/`에 **캐싱**되어 이후 실행은 즉시 로드

### 🔴 4. 이륜차 사고 다발 구역 Geofencing 레이어
* 경찰청 이륜차 사고 다발 지역 데이터를 레이어로 오버레이
* PM 기업 API와 연동 시 **고위험 구역 진입 자동 감속(Geofencing)** 구현 가능

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Hammer%20and%20Wrench.png" alt="Hammer and Wrench" width="30" height="30" style="vertical-align: middle;"/> 파이프라인 아키텍처

```
[STEP 1] PM 사고 CSV 로드 (2021~2024, 1,799건)
        ↓
[STEP 2] 3단계 매칭 샘플링 → 음성 샘플 생성 (1:1 균형)
        ↓
[STEP 3] 지점 단위 OSMnx 공간 Feature 추출 (캐시)
        ↓
[STEP 4] Optuna(n_trials=50) + XGBoost 학습 → SHAP 분석
        ↓
[STEP 5] 서울 전체 6,528개 격자 위험도 예측 → 히트맵 대시보드 생성
```

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Laptop.png" alt="Laptop" width="30" height="30" style="vertical-align: middle;"/> 실행 방법

### 1. 환경 설정

```bash
# 가상환경 생성 및 활성화
conda create -n roadsafe python=3.10 -y
conda activate roadsafe

# 공간 라이브러리 우선 설치 (충돌 방지)
conda install -c conda-forge geopandas osmnx pyproj shapely -y

# 나머지 패키지 설치
pip install -r requirements.txt
```

### 2. 데이터 준비

`data/raw/` 폴더에 아래 파일을 배치합니다.
*(해당 폴더는 `.gitignore` 처리되어 GitHub에 업로드되지 않습니다.)*

```
data/raw/
├── 서울특별시_2021-2023.csv   # PM 사고 좌표 데이터
├── 서울특별시-2024.csv        # PM 사고 좌표 데이터
└── 이륜차_사고다발지역_utf8.csv  # 이륜차 사고 다발 지역 (선택)
```

### 3. 전체 파이프라인 실행

```bash
python scripts/run.py
```

> **⏱️ 소요 시간 안내**
> - 최초 실행: 서울 도로망 다운로드 + 격자 Feature 추출로 **약 15~20분** 소요
> - 재실행: 모든 중간 결과가 `data/interim/`에 캐싱되어 **약 30초** 이내 완료

### 4. 결과물 확인

`outputs/` 폴더에 생성됩니다:

| 파일 | 설명 |
|---|---|
| `seoul_pm_risk_map.html` | 서울 전역 격자 위험도 히트맵 (브라우저에서 열기) |
| `shap_risk_bar.png` | Feature 중요도 순위 그래프 |
| `shap_risk_dot.png` | Feature 값에 따른 위험도 영향 방향성 그래프 |

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Open%20File%20Folder.png" alt="Folder" width="30" height="30" style="vertical-align: middle;"/> 폴더 구조

```text
RoadSafe/
├── scripts/
│   ├── run.py                   # 🚀 전체 파이프라인 실행 (메인 진입점)
│   └── setup_project.py         # 프로젝트 디렉토리 초기 설정
├── src/
│   ├── data/
│   │   ├── loader_pm.py         # PM 사고 CSV 로더 (2021-2024 병합)
│   │   └── negative_sampler.py  # 3단계 매칭 샘플링 (비사고 지점 생성)
│   ├── features/
│   │   ├── engineer_point.py    # 사고/비사고 지점 OSMnx Feature 추출
│   │   ├── engineer_grid.py     # 서울 전역 격자 위험도 예측
│   │   └── engineer_osmnx.py    # 구별 도로망 통계 (보조)
│   ├── models/
│   │   └── train_xgb_point.py   # XGBoost 학습 + Optuna HPO + SHAP
│   └── visualization/
│       └── visualize.py         # 격자 히트맵 대시보드 생성
├── data/
│   ├── raw/                     # 원본 데이터 (Git 제외)
│   └── interim/                 # 캐시 파일 (Git 제외)
├── outputs/                     # 결과물 (Git 제외)
├── tests/
└── requirements.txt
```

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Bar%20Chart.png" alt="Bar Chart" width="30" height="30" style="vertical-align: middle;"/> 모델 성능

| 모델 | AUROC | 비고 |
|---|---|---|
| **XGBoost (최종)** | **0.896** | Optuna 50회 탐색 |
| Random Forest | 0.892 | 비교 모델 |
| Logistic Regression | 0.816 | 비교 모델 |

> 기존 구(區) 단위 집계 기반 모델(AUROC 0.59) 대비, 지점 단위 정밀 좌표 + OSMnx 공간 Feature 도입으로 **AUROC 0.896**으로 대폭 향상.

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Books.png" alt="Books" width="30" height="30" style="vertical-align: middle;"/> 참고 문헌

* Chengula et al. (2024). *Spatial instability of crash prediction models: A case of scooter crashes.* Machine Learning with Applications, 17.
* Lacherre et al. (2024). *Factors, Prediction, and Explainability of Vehicle Accident Risk Due to Driving Behavior through Machine Learning.* Computation, 12, 131.
* Kim et al. (2024). *SST-GCN: The Sequential based Spatio-Temporal Graph Convolutional Networks for Minute-level and Road-level Traffic Accident Risk Prediction.* arXiv:2405.18602.
* Abdullah et al. (2026). *Identifying accident and safety risks in urban micromobility.* Sustainable Futures, 11.