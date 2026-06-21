import numpy as np
from typing import Dict, List

class CalibrationTracker:
    def __init__(self, n_buckets: int = 10):
        self.n_buckets = n_buckets
        self.buckets: Dict[float, List[float]] = {
            round(i / n_buckets, 2): []
            for i in range(1, n_buckets + 1)
        }
        self.history: List[Dict] = []

    def _bucket_key(self, confidence: float) -> float:
        b = round(max(0.01, min(1.0, confidence)) * self.n_buckets) / self.n_buckets
        return max(self.buckets.keys()) if b > max(self.buckets.keys()) else b

    def record(self, confidence: float, actual_accuracy: float):
        key = self._bucket_key(confidence)
        self.buckets[key].append(actual_accuracy)
        self.history.append({"confidence": confidence, "accuracy": actual_accuracy})

    def get_calibration_curve(self) -> Dict[float, float]:
        return {
            bucket: float(np.mean(accs))
            for bucket, accs in self.buckets.items()
            if accs
        }

    def expected_calibration_error(self) -> float:
        curve = self.get_calibration_curve()
        if not curve: return 1.0
        total = sum(len(self.buckets[b]) for b in curve)
        if total == 0: return 1.0
        ece = 0.0
        for bucket, acc in curve.items():
            n_b = len(self.buckets[bucket])
            ece += (n_b / total) * abs(bucket - acc)
        return ece

    def predict_accuracy(self, confidence: float) -> float:
        curve = self.get_calibration_curve()
        if not curve: return confidence
        nearest = min(curve.keys(), key=lambda b: abs(b - confidence))
        return curve[nearest]

    def second_order_confidence(self, confidence: float) -> float:
        key = self._bucket_key(confidence)
        n = len(self.buckets[key])
        prior = 10
        return n / (n + prior)

    def get_overconfidence_regions(self) -> List[Dict]:
        curve = self.get_calibration_curve()
        overconfident = []
        for bucket, acc in curve.items():
            if bucket - acc > 0.15:
                overconfident.append({
                    "confidence_bucket": bucket,
                    "actual_accuracy": acc,
                    "gap": bucket - acc,
                    "sample_size": len(self.buckets[bucket])
                })
        return overconfident
