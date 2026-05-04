"""
SAFERIDE 프로젝트 폴더 구조 초기화 스크립트
실행: python scripts/setup_project.py
"""
from pathlib import Path

DIRS = [
    "data/raw",
    "data/processed",
    "data/interim",
    "src/data",
    "src/features",
    "src/models",
    "src/evaluation",
    "src/visualization",
    "notebooks",
    "configs",
    "outputs/figures",
    "outputs/models",
]

if __name__ == "__main__":
    for d in DIRS:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"✓ {d}")

    # __init__.py 생성 (패키지화)
    for pkg in ["src", "src/data", "src/features", "src/models",
                "src/evaluation", "src/visualization"]:
        init = Path(pkg) / "__init__.py"
        init.touch(exist_ok=True)

    print("프로젝트 구조 생성 완료")
