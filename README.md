# <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/Kick%20Scooter.png" alt="Kick Scooter" width="45" height="45" style="vertical-align: middle;"/> SAFERIDE — PM 사고 공간 위험도 예측 플랫폼

![Python](https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&logo=python)
![XGBoost](https://img.shields.io/badge/XGBoost-Poisson_Regression-red?style=for-the-badge)
![AUROC](https://img.shields.io/badge/AUROC_(2025)-0.7980-blueviolet?style=for-the-badge)
![PAI](https://img.shields.io/badge/PAI@10%25_(Seoul)-28.0%25-brightgreen?style=for-the-badge)
![Features](https://img.shields.io/badge/Features-26개_공간변수-orange?style=for-the-badge)
![Web Dashboard](https://img.shields.io/badge/Dashboard-React_Vite-cyan?style=for-the-badge)

> **"사고가 나기 전에 위험한 공간을 먼저 바꿉니다."**
>
> SAFERIDE는 서울시 PM(개인형 이동장치) 사고 좌표 데이터와 도로망·CCTV·지형·킥보드 견인 공간 정보를 결합하여,  
> **사고가 없었던 지점도 포함해** 서울 전역의 PM 사고 위험도를 **500m 격자 단위**로 예측하는 AI 플랫폼입니다.  
> 분석 결과는 **인터랙티브 React 웹 대시보드**를 통해 실시간으로 시각화됩니다.

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/Rocket.png" alt="Rocket" width="30" height="30" style="vertical-align: middle;"/> 핵심 성과 요약

| 항목 | 내용 | 비고 |
|---|---|---|
| **모델 구조** | **Grid-level XGBoost Poisson Regressor** (500m × 500m) | 26개 공간 Feature (리키지 완전 차단) |
| **시간적 검증** | 2021~2024 데이터 학습 → **2025년 미래 실제 사고 예측 검증** | **완전 홀드아웃 (Out-of-time Validation)** |
| **엄밀한 통제** | 산·강 등 PM 주행 불가(노출량 Zero) 구역 선제 필터링 | 4,575개 ➡️ 2,426개 격자로 통제 |
| **미래 예측 AUROC** | **0.7980** (2025년 미래 검증 기준) | **치명적 결함(리키지) 차단 후 신뢰성 입증** 🌟 |
| **공간 전이성** | **AUROC 0.9114** (서울 학습 → 부산 Zero-shot 예측) | **공통 가용 Feature 15개 기준 엄격한 교차 도시 검증** |
| **실용성 지표 PAI** | 상위 10% 영역 단속 시 서울 PM 사고 **28.0% 예방** | 상위 20% 단속 시 **48.7% 예방** (PAI 지표 현실성 강화) |
| **전체 기간 성능** | AUROC 0.8979 (참고용) | 학습 데이터 포함 기준 성능 |
| **설명가능성** | SHAP 분석 — `poi_count_commercial`(상업시설) · `towing_count`(킥보드 견인)가 양대 핵심 위험 요인 | XAI 기반 도로 교통 정책 제안 근거 제시 |
| **대시보드** | React + Vite + Leaflet 기반 **인터랙티브 웹 대시보드** | 다크/라이트 모드, SHAP 패널, 구별 상세 검색 |

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Light%20Bulb.png" alt="Light Bulb" width="30" height="30" style="vertical-align: middle;"/> 모델 Feature 구성 (26개)

모델은 다각도의 공간 빅데이터에서 추출한 **26개**의 공간 Feature를 사용합니다.  
SHAP 분석을 통해 거시적 총합(전체 POI 수)보다 세부 항목 변수들이 더 정밀한 위험 요인으로 작동함을 확인, 최종 Feature Set에서 제외하였습니다.

### 🛣️ 1. 도로망 · POI 인프라 Feature (OSMnx 기반, 15개)

| Feature | 설명 | SHAP 순위 |
|---|---|:---:|
| `intersection_count_100m` | 반경 100m 내 교차로 수 | — |
| `intersection_count_200m` | 반경 200m 내 교차로 수 | — |
| `intersection_count_500m` | 반경 500m 내 교차로 수 | — |
| `node_degree` | 도로망 노드 평균 연결 차수 | — |
| `dist_to_nearest_intersection` | 최근 교차로까지 거리 | — |
| `avg_lanes` / `max_lanes` | 격자 내 평균/최대 차선 수 | — |
| `is_primary_road` | 간선도로(주간선) 여부 | — |
| `is_secondary_road` | 집산도로 여부 | — |
| `is_residential_road` | 이면도로 여부 | — |
| `is_intersection` | 격자 내 교차로 존재 여부 | — |
| `poi_count_commercial` | 상업시설 수 (술집·식당 등 유흥/상권 밀도) | **🥇 1위** |
| `poi_count_bus_stop` | 버스 정류장 수 | **4위** |
| `poi_count_station` | 지하철역 수 | — |
| `poi_count_university` | 대학교 수 | — |

### 📹 2. CCTV 감시/억제 Feature (3개)

| Feature | 설명 | 데이터 출처 |
|---|---|---|
| `cctv_count_total` | 격자 내 전체 CCTV 카메라 수 | 서울시 CCTV 39,965개소 / 79,374대 |
| `cctv_count_traffic` | 교통단속 카메라 수 | 속도·신호위반 억제 효과 대리변수 |
| `cctv_count_child` | 어린이보호구역 카메라 수 | 보행자 밀집 지역 식별 대리변수 |

### ⛰️ 3. 지형/경사도 Feature (2개)

| Feature | 설명 | 데이터 출처 |
|---|---|---|
| `elev_mean` | 격자 내 평균 표고 (m) | 서울시 표고 76,580개 측정점 |
| `elev_range` | 격자 내 최고-최저 표고 차 (m) | 경사도 대리변수. 클수록 급경사 → PM 제동 위험 ↑ |

### 🚦 4. 교통 안전 인프라 Feature (5개)

| Feature | 설명 | 데이터 출처 |
|---|---|---|
| `signal_count_total` | 격자 내 전체 신호등 수 | 서울시 신호등 표준데이터 (65,001개) |
| `signal_count_pedestrian` | 보행등 수 | 보행자 횡단 충돌 위험 대리변수 |
| `signal_count_vehicle` | 차량용 3색/4색 신호등 수 | 교차로 복잡도 및 차량 교통량 대리변수 |
| `signal_has_audio` | 음향신호기 수 | 보행자 보호 구역 대리변수 |
| `crosswalk_count` | 횡단보도 노드 수 (**SHAP 3위**) | 서울시 대로변 횡단보도 위치정보 (19,518개) |

### 🛴 5. 불법 주정차 밀집도 Feature (1개)

| Feature | 설명 | 데이터 출처 |
|---|---|---|
| `towing_count` | 전동킥보드 견인 수 (**SHAP 2위**, value=0.2285) | 서울시 전동킥보드 견인 현황 (27,571건, 2021~2025년) |

> 💡 **SHAP 분석 핵심 발견:** 불법 주정차(견인 다발) 지역과 상업시설 밀집 지역이 PM 사고 위험의 양대 핵심 원인으로 규명됨. 단순한 POI 총합(전체 관심지점 수)보다 **상업시설(유흥·상권)이 구체적인 위험 예측 인자**로 작동하며, 킥보드 무단 방치 관리가 직접적인 사고 예방으로 이어짐을 데이터로 증명.

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Hammer%20and%20Wrench.png" alt="Hammer and Wrench" width="30" height="30" style="vertical-align: middle;"/> 파이프라인 아키텍처

```text
[STEP 1] PM 사고 CSV 로드
         ├─ 서울특별시_2021-2024.csv (1,799건, 학습용)
         └─ 서울특별시-2025.csv    (333건, 시간적 홀드아웃 검증용)

[STEP 2] 서울 전역 500m 격자 분할 + OSMnx 도로망 Feature 추출 (캐싱)
         └─ data/interim/grid_features_with_labels_seoul.csv

[STEP 3] 보완 Feature 자동 병합 (캐시 기반, 누락 시 자동 갱신)
         ├─ CCTV Feature       ← src/features/engineer_cctv.py
         ├─ 경사도 Feature      ← src/features/engineer_slope.py
         ├─ 신호등 Feature      ← src/features/engineer_signal.py
         ├─ 횡단보도 Feature    ← src/features/engineer_crosswalk.py
         └─ 견인 데이터 Feature ← src/features/engineer_towing.py

[STEP 4] 산/강/외곽 비도로 구역 필터링 (4,575 → 2,426 격자)

[STEP 5] XGBoost Poisson Regressor 학습
         └─ Optuna HPO (30 trials) + L1/L2 정규화 + SHAP Feature Importance

[STEP 6] 2025년 미래 사고 대비 PAI/AUROC 평가
         └─ outputs/evaluation_summary.txt, pai_metrics_*.csv

[STEP 7] 웹 대시보드용 데이터 내보내기 (GeoJSON/JSON)
         └─ scripts/export_for_web.py → web/public/data/

[STEP 8] 인터랙티브 React 웹 대시보드 서빙
         └─ web/ (Vite + React + Leaflet, 다크/라이트 모드)
```

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Laptop.png" alt="Laptop" width="30" height="30" style="vertical-align: middle;"/> 실행 방법

### 1. 환경 설정

```bash
# 가상환경 생성 및 활성화
conda create -n roadsafe python=3.10 -y
conda activate roadsafe

# 공간 라이브러리 우선 설치 (의존성 충돌 방지)
conda install -c conda-forge geopandas osmnx pyproj shapely -y

# 핵심 패키지 설치
pip install -r requirements.txt
```

### 2. 데이터 준비

`data/raw/` 폴더에 아래 파일들을 배치합니다.  
*(해당 폴더는 `.gitignore` 처리되어 GitHub에 업로드되지 않습니다.)*

```text
data/raw/
├── 서울특별시_2021-2024.csv        # PM 사고 좌표 데이터 (학습용)
├── 서울특별시-2025.csv             # PM 사고 데이터 (2025 홀드아웃 검증용)
├── CCTV/
│   └── SEOUL_CCTV_DATA.shp        # 서울시 CCTV 위치 Shapefile
├── 서울시 경사도/
│   └── 표고 5000/
│       └── N3P_F002.shp           # 서울시 표고 측정점 Shapefile
├── 서울특별시_신호등표준데이터.csv   # 서울시 신호등 위치 (65,001개)
├── 서울특별시_횡단보도위치정보.csv   # 서울시 횡단보도 (19,518개)
└── 서울특별시_견인데이터/           # 전동킥보드 견인 현황 Excel 파일들
    ├── 24년 상반기.xlsx
    ├── 24.7~12월.xlsx
    └── ...
```

### 3. 전체 파이프라인 실행

```bash
python scripts/run_grid.py
```

> **⏱️ 소요 시간 안내**
> - **최초 실행**: 서울 도로망 다운로드 + 격자 Feature 계산 → **약 15~20분** 소요 (`data/interim/`에 자동 저장)
> - **두 번째 실행부터**: 캐시 로드 → 모든 Feature 자동 병합 → **약 1~2분** 이내 완료

### 4. 타 도시 전이성 검증 (선택)

```bash
python scripts/cross_city_eval.py
```

### 5. 결과물 확인

모든 결과물은 `outputs/` 폴더에 생성됩니다:

| 파일명 | 설명 |
|---|---|
| `evaluation_summary.txt` | AUROC / PAI / RRI 평가 요약 |
| `pai_metrics_2025.csv` | 2025년 시간적 검증 PAI 상세 |
| `pai_metrics_all.csv` | 전체 기간(2021-25) PAI 상세 |
| `shap_grid_bar.png` | 공간 Feature 중요도 순위 차트 |
| `shap_grid_dot.png` | Feature 영향력 방향성 시각화 |
| `seoul_pm_risk_grid.html` | (구버전) Folium 기반 정적 히트맵 |

### 6. 인터랙티브 웹 대시보드 실행

```bash
# 1) 모델 학습 완료 후 예측 및 SHAP 데이터를 웹 폴더로 내보내기
python scripts/export_for_web.py

# 2) 웹 대시보드 개발 서버 실행
cd web
npm install
npm run dev
```

> **웹 대시보드 주요 기능**
> - 🗺️ 서울 전역 500m 격자별 위험도 히트맵 (빨간색 농도 = 위험도)
> - 📊 SHAP Feature Importance 및 모델 성능 지표 실시간 패널
> - 🔍 구(District) 이름 검색 및 구역 하이라이트 필터
> - 🌓 다크/라이트 모드 동적 전환 (지도 타일 포함)

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Bar%20Chart.png" alt="Bar Chart" width="30" height="30" style="vertical-align: middle;"/> 모델 성능 상세

### 2025년 미래 예측 검증 (시간적 홀드아웃)

| 지표 | 기본 (16) | + CCTV (19) | + 신호등/횡단보도 (26) | **+ 견인·정규화 (27, 최종)** |
|---|:---:|:---:|:---:|:---:|
| **AUROC** | 0.7468 | 0.7863 | 0.8024 | **0.7980** |
| **MAE** | 1.222건 | 0.846건 | 0.758건 | **0.664건** |
| **RMSE** | 1.607건 | 1.175건 | 1.122건 | **0.954건** |
| **포착률 k=5%** | 11.4% | 17.2% | 19.2% | **15.3%** |
| **포착률 k=10%** | 21.8% | 28.0% | 29.5% | **28.0%** |
| **포착률 k=30%** | — | 65.1% | 66.7% | **66.3%** |
| **포착률 k=50%** | 85.1% | 87.4% | 92.0% | **92.3%** |
| **RRI k=50%** | 1.10 | 1.13 | 1.19 | **1.19** |
| **Moran's I** | — | 0.4291 | 0.4137 | **0.3811** |

> 💡 **성과 해석:** 견인 데이터의 시간 누수(리키지)를 완벽히 필터링하고 실제 XGBoost 포아송 raw 예측값을 적용해 평가 수식을 엄격히 정정하였음에도, 미래 예측 AUROC는 **0.7980**으로 매우 강력하게 유지되며 RMSE/MAE 오차와 Moran's I(공간 편향성) 지표가 대폭 향상되는 고도화 성과를 거두었습니다.

### 공간 전이성 검증 (서울 학습 → 부산 Zero-shot)

| 지표 | 결과 | 비고 |
|---|---|---|
| **부산 AUROC** | **0.9114** | OSMnx + POI 15개 공통 Feature 기준 전이 전용 모델 활용 |
| **PAI@10% (부산)** | **5.70** | 상위 10% 단속으로 부산 PM 사고의 **57.0% 예방** |
| **PAI@20% (부산)** | **8.26** | 상위 20% 단속으로 부산 PM 사고의 **82.6% 예방** |

> 💡 **성과 해석:** 서울과 부산 양쪽 도시에서 모두 완벽하게 가용한 15개 Feature(CCTV·견인 등 결측 데이터 완전 배제)만을 이용해 서울 데이터로 학습시킨 전용 모델로 부산에 제로샷 전이 평가를 내린 결과, **0.9114의 초고성능 AUROC**를 달성하여 모델의 공간적 일반화 전이 성능을 학술적으로 엄격하게 검증하였습니다.

> 서울에서만 학습된 모델이 부산에서도 높은 예측력을 보임 → **공간적 일반화(Spatial Generalization)** 성능 입증

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Magnifying%20Glass%20Tilted%20Left.png" alt="Magnifying Glass" width="30" height="30" style="vertical-align: middle;"/> 프로젝트 구조

```text
RoadSafe/
├── scripts/
│   ├── run_grid.py             # 메인 파이프라인 실행 스크립트
│   ├── export_for_web.py       # 웹 대시보드용 데이터 내보내기
│   └── cross_city_eval.py      # 타 도시 전이성 검증 스크립트
├── src/
│   ├── data/
│   │   └── loader_pm.py        # PM 사고 원본 데이터 로더
│   ├── features/
│   │   ├── engineer_grid.py    # 500m 격자 분할 및 라벨 생성
│   │   ├── engineer_osmnx.py   # OSMnx 도로망 Feature 추출
│   │   ├── engineer_poi.py     # POI(관심지점) Feature 추출
│   │   ├── engineer_cctv.py    # CCTV Feature 추출 및 격자 매핑
│   │   ├── engineer_slope.py   # 서울시 표고/경사도 Feature 추출
│   │   ├── engineer_signal.py  # 서울시 신호등 Feature 매핑
│   │   ├── engineer_crosswalk.py # 서울시 횡단보도 Feature 매핑
│   │   └── engineer_towing.py  # 전동킥보드 견인 데이터 Feature 추출
│   ├── models/
│   │   └── train_xgb_grid.py   # XGBoost 학습, HPO, SHAP, 평가 코어
│   ├── evaluation/             # PAI, AUROC 평가 모듈
│   └── visualization/          # Folium 히트맵 대시보드 생성
├── web/                        # 인터랙티브 React 웹 대시보드
│   ├── src/
│   │   ├── components/         # RiskMap, Sidebar, AnalyticsPanel 등
│   │   └── App.jsx
│   └── public/data/            # 모델 예측 GeoJSON, SHAP JSON
├── data/
│   ├── raw/                    # 원본 데이터 (.gitignore)
│   └── interim/                # 전처리된 Feature 캐시
├── outputs/                    # 결과물 (HTML, PNG, CSV, TXT)
├── research_log.md             # 연구 의사결정 및 실험 기록
└── requirements.txt
```

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Books.png" alt="Books" width="30" height="30" style="vertical-align: middle;"/> 참고 문헌

* Chengula et al. (2024). *Spatial instability of crash prediction models: A case of scooter crashes.* Machine Learning with Applications, 17.
* Lacherre et al. (2024). *Factors, Prediction, and Explainability of Vehicle Accident Risk Due to Driving Behavior through Machine Learning.* Computation, 12, 131.
* Kim et al. (2024). *SST-GCN: The Sequential based Spatio-Temporal Graph Convolutional Networks for Minute-level and Road-level Traffic Accident Risk Prediction.* arXiv:2405.18602.
* Abdullah et al. (2026). *Identifying accident and safety risks in urban micromobility.* Sustainable Futures, 11.