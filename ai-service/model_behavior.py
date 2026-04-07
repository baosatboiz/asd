from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Tuple

import joblib
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


SEGMENT_NAMES = ["Khám phá", "Tiết kiệm", "Cao cấp", "Trung thành"]
FEATURE_NAMES = ["clicks", "add_to_cart", "total_spend", "session_duration"]


@dataclass(frozen=True)
class BehaviorInput:
    clicks: float
    add_to_cart: float
    total_spend: float
    session_duration: float

    def as_vector(self) -> list[float]:
        return [self.clicks, self.add_to_cart, self.total_spend, self.session_duration]


class BehaviorModel:
    """MLP classifier that segments customers into four behavior groups."""

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state
        self.pipeline = self._train_pipeline()

    def _train_pipeline(self) -> Pipeline:
        features, labels = self._build_synthetic_dataset()
        pipeline = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "mlp",
                    MLPClassifier(
                        hidden_layer_sizes=(32, 16),
                        activation="relu",
                        solver="adam",
                        alpha=0.0005,
                        batch_size=32,
                        learning_rate_init=0.001,
                        max_iter=1500,
                        random_state=self.random_state,
                        early_stopping=False,
                    ),
                ),
            ]
        )
        pipeline.fit(features, labels)
        return pipeline

    def _build_synthetic_dataset(self) -> Tuple[np.ndarray, np.ndarray]:
        rng = np.random.default_rng(self.random_state)

        centroids = {
            "Khám phá": np.array([18.0, 1.0, 35.0, 780.0]),
            "Tiết kiệm": np.array([26.0, 5.0, 70.0, 1120.0]),
            "Cao cấp": np.array([10.0, 2.0, 780.0, 520.0]),
            "Trung thành": np.array([28.0, 6.0, 290.0, 1380.0]),
        }
        spreads = {
            "Khám phá": np.array([5.0, 1.0, 20.0, 180.0]),
            "Tiết kiệm": np.array([6.0, 1.5, 30.0, 220.0]),
            "Cao cấp": np.array([4.0, 1.0, 140.0, 140.0]),
            "Trung thành": np.array([5.0, 1.5, 90.0, 260.0]),
        }

        samples: list[list[float]] = []
        labels: list[str] = []

        for segment_name in SEGMENT_NAMES:
            centroid = centroids[segment_name]
            spread = spreads[segment_name]
            for _ in range(220):
                row = rng.normal(loc=centroid, scale=spread)
                row = np.maximum(row, 0.0)
                row[0] = np.round(row[0], 2)
                row[1] = np.round(row[1], 2)
                row[2] = np.round(row[2], 2)
                row[3] = np.round(row[3], 2)
                samples.append(row.tolist())
                labels.append(segment_name)

        return np.asarray(samples, dtype=float), np.asarray(labels, dtype=object)

    def predict(self, behavior: BehaviorInput | Dict[str, Any] | Iterable[float]) -> Dict[str, Any]:
        vector = self._normalize_input(behavior)
        probabilities = self.pipeline.predict_proba([vector])[0]
        predicted_index = int(np.argmax(probabilities))
        predicted_segment = str(self.pipeline.classes_[predicted_index])

        return {
            "segment": predicted_segment,
            "confidence": round(float(probabilities[predicted_index]), 4),
            "probabilities": {
                str(label): round(float(score), 4)
                for label, score in zip(self.pipeline.classes_, probabilities)
            },
            "features": {
                name: round(float(value), 2)
                for name, value in zip(FEATURE_NAMES, vector)
            },
        }

    def save(self, path: str) -> None:
        joblib.dump(self.pipeline, path)

    @classmethod
    def load(cls, path: str) -> "BehaviorModel":
        instance = cls.__new__(cls)
        instance.random_state = 42
        instance.pipeline = joblib.load(path)
        return instance

    def _normalize_input(self, behavior: BehaviorInput | Dict[str, Any] | Iterable[float]) -> list[float]:
        if isinstance(behavior, BehaviorInput):
            return behavior.as_vector()

        if isinstance(behavior, dict):
            return [float(behavior[name]) for name in FEATURE_NAMES]

        vector = list(behavior)
        if len(vector) != len(FEATURE_NAMES):
            raise ValueError(f"Expected {len(FEATURE_NAMES)} features: {FEATURE_NAMES}")
        return [float(value) for value in vector]


def segment_hint(segment_name: str | None) -> str:
    hints = {
        "Khám phá": (
            "Khách đang ở giai đoạn khám phá. Hãy giới thiệu danh mục mới, best-seller, "
            "và những lựa chọn dễ bắt đầu để tăng tỷ lệ chuyển đổi."
        ),
        "Tiết kiệm": (
            "Khách nhạy cảm về giá. Hãy ưu tiên mã giảm giá, sản phẩm giá tốt, combo tiết kiệm, "
            "và nêu rõ ưu đãi để tối ưu quyết định mua."
        ),
        "Cao cấp": (
            "Khách có xu hướng chi tiêu cao. Hãy nhấn mạnh chất lượng, trải nghiệm premium, "
            "sản phẩm cao cấp và giá trị khác biệt."
        ),
        "Trung thành": (
            "Khách trung thành và có giá trị dài hạn. Hãy gợi ý ưu đãi dành cho thành viên, "
            "chăm sóc cá nhân hóa, và sản phẩm bổ sung phù hợp lịch sử mua sắm."
        ),
    }
    return hints.get(segment_name or "", "Chưa có đủ dữ liệu hành vi để cá nhân hóa sâu.")