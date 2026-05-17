"""
SAFERIDE 모델 평가 실행 스크립트
PAI 곡선 + 2024년 시간적 검증
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.evaluate import run_evaluation

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    run_evaluation(output_dir="outputs")
