# <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/Kick%20Scooter.png" alt="Kick Scooter" width="45" height="45" style="vertical-align: middle;"/> SAFERIDE — PM 사고 공간 위험도 예측 플랫폼

![Python](https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&logo=python)
![XGBoost](https://img.shields.io/badge/XGBoost-Grid_Model-red?style=for-the-badge)
![Metric](https://img.shields.io/badge/PAI@20%25-1.99-blueviolet?style=for-the-badge)
![Validation](https://img.shields.io/badge/Temporal_Holdout-2024_Future_Prediction-brightgreen?style=for-the-badge)
![OSMnx](https://img.shields.io/badge/OSMnx-Spatial_Feature-orange?style=for-the-badge)
![Folium](https://img.shields.io/badge/Folium-Grid_Heatmap-green?style=for-the-badge)

> **"사고가 나기 전에 위험한 공간을 먼저 바꿉니다."**
>
> SAFERIDE는 서울시 PM(개인형 이동장치) 사고 좌표 데이터와 도로망 공간 정보를 결합하여,
> **사고가 없었던 지점도 포함해** 서울 전역의 공간적 PM 사고 위험도를 500m 격자 단위로 예측하는 AI 플랫폼입니다.

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/Rocket.png" alt="Rocket" width="30" height="30" style="vertical-align: middle;"/> 핵심 기술 및 논문급 성과

| 항목 | 내용 |
|---|---|
| **모델 구조** | **격자 수준(Grid-level) XGBoost 예측 모델** (500m × 500m) |
| **시간적 검증** | 2021~2023 데이터 학습 → **2024년 미래 실제 사고 예측 검증** |
| **엄밀한 통제** | 산, 강 등 PM 주행이 불가능한 노출량 0(Zero-exposure) 구역 선제적 필터링 적용 (정확도 과대평가 방지) |
| **미래 예측력** | **AUROC 0.767** (2024년 검증 기준, 보수적 필터링 및 유동인구 POI 변수 추가 모델) |
| **실용성 지표(PAI)**| **PAI@10% = 2.46** (서울 상위 10% 위험 구역만 관리해도 전체 사고의 약 25% 사전 예방 가능) |
| **설명가능성** | SHAP 분석을 통해 "반경 500m 내 교차로 밀집도"가 핵심 위험 요인임을 정량적 증명 |

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Light%20Bulb.png" alt="Light Bulb" width="30" height="30" style="vertical-align: middle;"/> 주요 기능

### 🗺️ 1. 서울 전역 격자 위험도 히트맵
* 서울을 **500m × 500m 격자**로 나누어 도로망이 존재하는 2,400여 개 구역의 위험도를 예측합니다.
* 초록(안전) → 노랑 → 주황 → 빨강(위험)의 직관적 색상 스케일을 제공합니다.
* 특정 격자를 클릭하면 해당 구역의 누적 사고 건수와 예측 위험도 점수를 팝업으로 확인할 수 있습니다.

### 🧠 2. SHAP 기반 설명 가능한 AI (XAI)
* 모델이 특정 격자를 왜 위험하다고 판단했는지 **SHAP 값으로 정량화**합니다.
* Feature Importance Bar 차트와 방향성 Dot 차트를 자동 생성하여, 정책 제언이나 논문 작성 시 직접 활용할 수 있습니다.

### 🏗️ 3. PAI (Predictive Accuracy Index) 자동 평가 체계
* 공간 모델의 실용성을 평가하는 범죄/교통학 핵심 지표인 PAI를 자동 계산합니다.
* 모델 실행 시 시간적 홀드아웃(2024년 테스트) 결과를 PAI 표 형태로 터미널과 텍스트 파일에 출력합니다.

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Hammer%20and%20Wrench.png" alt="Hammer and Wrench" width="30" height="30" style="vertical-align: middle;"/> 파이프라인 아키텍처

```text
[STEP 1] PM 사고 CSV 로드 (2021~2024 서울 데이터)
        ↓
[STEP 2] 서울 전역 500m 격자 분할 및 OSMnx 공간 Feature 자동 추출 (캐싱)
        ↓
[STEP 3] 산/강 등 비도로(노출량 0) 구역 필터링 (과대평가 방지)
        ↓
[STEP 4] 2021-2023 사고 기준 XGBoost 학습 (Optuna 튜닝) + SHAP 분석
        ↓
[STEP 5] 2024 실제 사고 대비 PAI 계산 및 히트맵 대시보드(HTML) 생성
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

`data/raw/` 폴더에 아래 파일을 배치합니다.
*(해당 폴더는 `.gitignore` 처리되어 GitHub에 업로드되지 않습니다.)*

```text
data/raw/
└── 서울특별시_2021-2024.csv   # PM 사고 좌표 데이터
```

### 3. 전체 파이프라인 실행

```bash
python scripts/run_grid.py
```

> **⏱️ 소요 시간 안내**
> - 최초 실행: 서울 도로망 다운로드 + 격자 Feature 계산으로 **약 15~20분** 소요 (`data/interim/`에 자동 저장)
> - 두 번째 실행부터: 캐시를 로드하므로 **약 1~2분** 이내에 학습 및 평가 완료

### 4. 결과물 확인

모든 결과물은 `outputs/` 폴더에 생성됩니다:

| 파일명 | 설명 |
|---|---|
| `seoul_pm_risk_grid.html` | 격자 수준 공간 위험도 대시보드 (브라우저에서 열기) |
| `evaluation_summary.txt` | AUROC 및 PAI 평가 요약 결과 (논문 복붙용) |
| `pai_metrics_2024.csv` | 2024년 시간적 검증 PAI 상세 데이터 |
| `shap_grid_bar.png` | 공간 Feature 중요도 순위 차트 |
| `shap_grid_dot.png` | Feature 영향력 방향성 시각화 차트 |

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Bar%20Chart.png" alt="Bar Chart" width="30" height="30" style="vertical-align: middle;"/> 모델 성능 및 성과 요약

| 지표 | 결과 | 의미 (논문 디펜스 포인트) |
|---|---|---|
| **미래 예측 AUROC** | **0.767** | 랜덤 분할이 아닌 2024년 시간적 홀드아웃 검증. 유동인구(POI) 변수 결합을 통해 이전(0.737) 대비 예측력 크게 향상. |
| **전체 기간 AUROC** | **0.859** | 전체 기간 기준 강건한 분류 성능 (유동인구 변수 추가로 0.820 → 0.859 상승). |
| **PAI@10%** | **2.46** | 상위 10% 위험 격자 단속 시, 2024년 전체 PM 사고의 약 **25%** 사전 예방 가능 (무작위 단속 대비 2.46배 효율). |
| **PAI@20%** | **2.20** | 상위 20% 위험 격자 단속 시, 2024년 전체 PM 사고의 약 **44%** 사전 예방 가능. |

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Books.png" alt="Books" width="30" height="30" style="vertical-align: middle;"/> 참고 문헌

* Chengula et al. (2024). *Spatial instability of crash prediction models: A case of scooter crashes.* Machine Learning with Applications, 17.
* Lacherre et al. (2024). *Factors, Prediction, and Explainability of Vehicle Accident Risk Due to Driving Behavior through Machine Learning.* Computation, 12, 131.
* Kim et al. (2024). *SST-GCN: The Sequential based Spatio-Temporal Graph Convolutional Networks for Minute-level and Road-level Traffic Accident Risk Prediction.* arXiv:2405.18602.
* Abdullah et al. (2026). *Identifying accident and safety risks in urban micromobility.* Sustainable Futures, 11.