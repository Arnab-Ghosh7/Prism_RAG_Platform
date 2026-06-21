import numpy as np
from typing import Dict, List, Optional

class CognitiveMap:
    def __init__(self, confidence_threshold: float = 0.6, accuracy_threshold: float = 0.6):
        self.conf_thresh = confidence_threshold
        self.acc_thresh = accuracy_threshold
        self.map: Dict[str, Dict[str, Dict]] = {}

    def classify(self, confidence: float, accuracy: float) -> str:
        high_conf = confidence >= self.conf_thresh
        high_acc = accuracy >= self.acc_thresh
        if high_conf and high_acc: return "KNOWN_KNOWN"
        elif high_conf and not high_acc: return "UNKNOWN_KNOWN"
        elif not high_conf and high_acc: return "KNOWN_UNKNOWN"
        else: return "UNKNOWN_UNKNOWN"

    def update(self, domain: str, topic: str, confidence: float, accuracy: Optional[float] = None):
        if domain not in self.map: self.map[domain] = {}
        if topic not in self.map[domain]:
            self.map[domain][topic] = {"confidences": [], "accuracies": [], "quadrant": "UNTESTED"}
        
        entry = self.map[domain][topic]
        entry["confidences"].append(confidence)
        if accuracy is not None:
            entry["accuracies"].append(accuracy)
            avg_c = np.mean(entry["confidences"])
            avg_a = np.mean(entry["accuracies"])
            entry["quadrant"] = self.classify(avg_c, avg_a)

    def get_danger_zones(self) -> List[Dict]:
        dangers = []
        for domain, topics in self.map.items():
            for topic, state in topics.items():
                if state["quadrant"] == "UNKNOWN_KNOWN":
                    dangers.append({
                        "domain": domain, "topic": topic,
                        "avg_confidence": round(np.mean(state["confidences"]), 3),
                        "avg_accuracy": round(np.mean(state["accuracies"]), 3) if state["accuracies"] else None,
                        "severity": "CRITICAL"
                    })
        return dangers

    def get_summary(self) -> Dict:
        counts = {"KNOWN_KNOWN": 0, "KNOWN_UNKNOWN": 0, "UNKNOWN_KNOWN": 0, "UNKNOWN_UNKNOWN": 0, "UNTESTED": 0}
        for domain, topics in self.map.items():
            for topic, state in topics.items():
                q = state["quadrant"]
                if q in counts: counts[q] += 1
        return {
            "quadrant_distribution": counts,
            "total_domains": len(self.map),
            "total_topics": sum(len(t) for t in self.map.values()),
            "danger_zones": self.get_danger_zones(),
            "health_score": round(counts["KNOWN_KNOWN"] / max(1, sum(counts.values()) - counts["UNTESTED"]), 3)
        }
