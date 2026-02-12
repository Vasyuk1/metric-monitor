from prometheus_client import Gauge, Counter, Histogram, REGISTRY
from typing import Dict

class MetricsRegistry:
    def __init__(self):
        self._gauges: Dict[str, Gauge] = {}
        self._counters: Dict[str, Counter] = {}
        self._histograms: Dict[str, Histogram] = {}
    
    def gauge(self, name: str, description: str, labels: list = None) -> Gauge:
        if name not in self._gauges:
            self._gauges[name] = Gauge(name, description, labels or [])
        return self._gauges[name]
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        gauge = self.gauge(name, "auto-generated", labels=list(labels.keys()) if labels else None)
        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)

registry = MetricsRegistry()