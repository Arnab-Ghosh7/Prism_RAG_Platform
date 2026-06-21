import numpy as np
from typing import List, Dict
from collections import defaultdict

class FailurePatternMiner:
    def __init__(self):
        self.failures: List[Dict] = []
        self.domain_stats: Dict[str, Dict] = {}
        self.failure_cooccurrence: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record(self, domain: str, topic: str, confidence: float, actual_accuracy: float, failure_type: str = None):
        if domain not in self.domain_stats:
            self.domain_stats[domain] = {"total": 0, "failures": 0}
        self.domain_stats[domain]["total"] += 1

        if actual_accuracy < 0.5:
            self.domain_stats[domain]["failures"] += 1
            ft = failure_type or "LOW_ACCURACY"
            self.failures.append({
                "domain": domain, "topic": topic, "confidence": confidence,
                "accuracy": actual_accuracy, "failure_type": ft
            })

    def get_patterns(self) -> List[Dict]:
        patterns = []
        for domain, stats in self.domain_stats.items():
            if stats["total"] >= 2:
                rate = stats["failures"] / stats["total"]
                if rate > 0.3:
                    patterns.append({
                        "type": "DOMAIN_WEAKNESS", "domain": domain,
                        "failure_rate": round(rate, 3),
                        "severity": "CRITICAL" if rate > 0.6 else "HIGH"
                    })
        if self.failures:
            overconf = [f for f in self.failures if f["confidence"] > 0.7]
            if len(overconf) > 1:
                patterns.append({
                    "type": "SYSTEMATIC_OVERCONFIDENCE", "count": len(overconf),
                    "avg_confidence": round(np.mean([f["confidence"] for f in overconf]), 3),
                    "avg_accuracy": round(np.mean([f["accuracy"] for f in overconf]), 3),
                    "severity": "CRITICAL"
                })
        return patterns

    def get_vulnerability_report(self) -> Dict:
        total = sum(s["total"] for s in self.domain_stats.values())
        total_f = sum(s["failures"] for s in self.domain_stats.values())
        return {
            "total_interactions": total, "total_failures": total_f,
            "overall_failure_rate": round(total_f / max(1, total), 3),
            "domain_vulnerabilities": {
                d: round(s["failures"] / max(1, s["total"]), 3)
                for d, s in self.domain_stats.items()
            },
            "patterns": self.get_patterns()
        }
