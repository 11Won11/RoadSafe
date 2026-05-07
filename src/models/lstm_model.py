"""
6시간 슬라이딩 윈도우 기반 LSTM 위험 예측 모델
PyTorch 구현 — 격자별 시계열 패턴 학습
"""
import numpy as np
import torch
import torch.nn as nn


class RiskLSTM(nn.Module):
    """LSTM 기반 PM 사고 위험 이진 분류 모델"""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.lstm = nn.LSTM(
            input_dim, hidden_dim, num_layers,
            batch_first=True, dropout=dropout
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, input_dim)
        out, _ = self.lstm(x)
        return self.head(out[:, -1]).squeeze(-1)  # 마지막 타임스텝 예측


def make_sequences(
    df,
    feat_cols: list,
    target_col: str,
    seq_len: int = 6,
):
    """격자별 6h 슬라이딩 윈도우 → (X, y) numpy 배열 반환"""
    X_list, y_list = [], []
    for _, grp in df.sort_values("datetime").groupby("grid_id"):
        feats  = grp[feat_cols].values
        labels = grp[target_col].values
        for i in range(len(grp) - seq_len):
            X_list.append(feats[i : i + seq_len])
            y_list.append(labels[i + seq_len])
    return (
        np.array(X_list, dtype=np.float32),
        np.array(y_list, dtype=np.float32),
    )


def train_epoch(model, loader, optimizer, loss_fn, device) -> float:
    """한 에폭 학습, 평균 loss 반환"""
    model.train()
    total_loss = 0.0
    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        optimizer.zero_grad()
        loss = loss_fn(model(X_batch), y_batch)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(loader)
