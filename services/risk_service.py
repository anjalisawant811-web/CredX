from ml_engine import EnsembleRiskEngine


class RiskService:

    def __init__(self):
        self.engine = EnsembleRiskEngine()

    def evaluate(self, raw_data: dict):
        return self.engine.predict(raw_data)