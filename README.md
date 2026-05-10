# <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/Kick%20Scooter.png" alt="Kick Scooter" width="45" height="45" style="vertical-align: middle;"/> SAFERIDE: 데이터 기반 개인형 이동장치(PM) 안전 및 정책 플랫폼

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0.3-red?style=for-the-badge&logo=xgboost)
![Optuna](https://img.shields.io/badge/Optuna-3.6.1-blue?style=for-the-badge)
![SHAP](https://img.shields.io/badge/SHAP-Explainable%20AI-brightgreen?style=for-the-badge)
![Folium](https://img.shields.io/badge/Folium-Geospatial-orange?style=for-the-badge)

**SAFERIDE**는 단순한 AI 예측 모델을 넘어, **데이터로 교통 안전을 바꾸는 정책형 플랫폼**입니다. 
경찰청 TAAS 데이터, 기상 데이터, 행정 구역 데이터를 종합하여 전동킥보드 등 개인형 이동장치(PM)의 사고 위험도를 예측하고, 지자체와 기업이 활용할 수 있는 정량적 정책 근거를 제공합니다.

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/Rocket.png" alt="Rocket" width="30" height="30" style="vertical-align: middle;"/> 주요 기능 (Key Features)

### <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/World%20Map.png" alt="World Map" width="25" height="25" style="vertical-align: middle;"/> 1. 위험 Hotspot 지도 & 대시보드
* 서울시 구(區) 단위 / 500m 격자 단위의 PM 사고 위험도를 색상 히트맵으로 시각화합니다.
* 클릭 시 해당 구역의 **사고 심각도(고위험 비율) 및 핵심 위험 요인**을 즉시 확인할 수 있습니다.

### <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Light%20Bulb.png" alt="Light Bulb" width="25" height="25" style="vertical-align: middle;"/> 2. 설명 가능한 AI (XAI)를 통한 정책 근거 제시
* **SHAP (SHapley Additive exPlanations)** 기술을 적용하여, 모델이 블랙박스로 남지 않도록 합니다.
* 야간 주행, 신호 위반, 교차로 등 어떤 환경적 요인이 사고를 치명적으로 만드는지 정량화하여 지자체 정책 수립의 근거로 제공합니다.

### <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Bell.png" alt="Bell" width="25" height="25" style="vertical-align: middle;"/> 3. 실시간 Geofencing 및 알림 연계 (설계안)
* 고위험 구역 진입 시 "현재 사고 위험 높음 - 감속 권고" 알림 제공.
* PM 공유 플랫폼 기업에 REST API 형태로 위험도 데이터를 제공하여 **자동 속도 제한(Geofencing)**을 지원합니다.

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Hammer%20and%20Wrench.png" alt="Hammer and Wrench" width="30" height="30" style="vertical-align: middle;"/> 시스템 아키텍처 및 모델 고도화 전략

본 프로젝트는 점진적인 모델 고도화 전략을 채택합니다.

* **Phase 1: XGBoost Baseline 모델 (완료)**
  * PM 사고 데이터 기반 심각도(사망/중상 vs 경상) 분류 예측.
  * `scale_pos_weight` 적용 및 `Optuna` 기반 Bayesian Optimization (TPE) 탐색.
  * SHAP 기반 Feature Importance 도출.
* **Phase 2: LSTM 시계열 모델 (예정)**
  * 500m 단위 격자(Grid) 생성 및 1시간 단위 6시간 슬라이딩 윈도우 데이터 구축.
* **Phase 3: SST-GCN 시공간 융합 모델 (예정)**
  * 도로 네트워크(Node, Edge) 기반 Graph Convolutional Network와 LSTM 결합.

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Laptop.png" alt="Laptop" width="30" height="30" style="vertical-align: middle;"/> 실행 방법 (Phase 1 기준)

### 1. 환경 설정

Anaconda를 사용한 가상환경 세팅을 권장합니다.

```bash
# 가상환경 생성 및 활성화
conda create -n roadsafe python=3.11 -y
conda activate roadsafe

# 공간 데이터 분석용 패키지 우선 설치 (충돌 방지)
conda install -c conda-forge geopandas osmnx pyproj shapely -y

# 의존성 패키지 설치
pip install -r requirements.txt
pip install folium python-docx openpyxl "numpy<2.0.0"
```

### 2. 데이터 준비

* 프로젝트 최상단 폴더에 `사고분석-지역별.xlsx` 파일을 배치합니다. 
* *(해당 데이터는 Github에 올라가지 않도록 `.gitignore` 처리되어 있습니다.)*

### 3. 파이프라인 실행

```bash
# 전체 파이프라인 자동 실행 (데이터로드 -> 특성 공학 -> 학습 -> 시각화)
python3 scripts/run_phase1.py
```

### 4. 결과물 확인

실행이 완료되면 `outputs/` 디렉토리에 다음 파일들이 생성됩니다:
* `seoul_pm_risk_map.html`: 서울 구별 사고 다발 구역 및 심각도 히트맵 (브라우저에서 실행)
* `shap_summary_bar.png`: Feature 중요도 막대 그래프
* `shap_summary_dot.png`: Feature 값 변화에 따른 심각도 영향 산점도

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Open%20File%20Folder.png" alt="Folder" width="30" height="30" style="vertical-align: middle;"/> 폴더 구조

```text
RoadSafe/
├── scripts/
│   ├── setup_project.py     # 프로젝트 기본 디렉토리 셋업
│   └── run_phase1.py        # Phase 1 전체 파이프라인 실행 스크립트
├── src/
│   ├── data/
│   │   ├── loader.py        # Phase 2용 다중 소스 병합 로더
│   │   └── loader_phase1.py # Phase 1용 엑셀 데이터 로더
│   ├── features/
│   │   ├── engineer.py      # 시간/기상 변수 엔지니어링
│   │   ├── engineer_phase1.py # Phase 1용 One-hot 인코딩
│   │   └── grid.py          # Phase 2용 500m 격자 생성
│   ├── models/
│   │   ├── train_xgb.py     # XGBoost 학습 원본
│   │   ├── train_xgb_phase1.py # Phase 1 XGBoost + SHAP 분석
│   │   └── lstm_model.py    # Phase 2용 LSTM 모델
│   └── visualization/
│       └── visualize_phase1.py # 구 단위 위험도 히트맵 (Folium)
├── tests/                   # 단위 테스트 코드
├── outputs/                 # 시각화 및 모델 결과물 (Git Ignore)
└── requirements.txt
```

---

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Books.png" alt="Books" width="30" height="30" style="vertical-align: middle;"/> 참고 문헌
* Chengula et al. (2024). Spatial instability of crash prediction models: A case of scooter crashes.
* Lacherre et al. (2024). Factors, Prediction, and Explainability of Vehicle Accident Risk Due to Driving Behavior through Machine Learning.
* Kim et al. (2024). SST-GCN: The Sequential based Spatio-Temporal Graph Convolutional Networks.