from feature_engineering import FeatureEngine

from ml_engine.models.lr import LogisticRegressionModel
from ml_engine.models.rf import RandomForestModel
from ml_engine.models.gb import GradientBoostingModel
from ml_engine.models.lgbm import LightGBMModel
from ml_engine.models.gru import GRUModel


class EnsembleRiskEngine:

    def __init__(self):

        # initialize independent models (production style)
        self.lr = LogisticRegressionModel()
        self.rf = RandomForestModel()
        self.gb = GradientBoostingModel()
        self.lgbm = LightGBMModel()
        self.gru = GRUModel()

        # ensemble weights (PPT-aligned)
        self.weights = {
            "lr": 0.10,
            "rf": 0.20,
            "gb": 0.20,
            "lgbm": 0.30,
            "gru": 0.20
        }

    def predict(self, raw_data):

        # 1. Feature extraction
        features = FeatureEngine.build(raw_data)

        # 2. Individual model predictions
        lr_score = self.lr.predict_proba(features)
        rf_score = self.rf.predict_proba(features)
        gb_score = self.gb.predict_proba(features)
        lgbm_score = self.lgbm.predict_proba(features)
        gru_score = self.gru.predict_proba(features)

        # 3. Weighted fusion
        final_score = (
            self.weights["lr"] * lr_score +
            self.weights["rf"] * rf_score +
            self.weights["gb"] * gb_score +
            self.weights["lgbm"] * lgbm_score +
            self.weights["gru"] * gru_score
        )

        return {
            "risk_score": round(final_score * 100, 2),
            "lr": round(lr_score, 4),
            "rf": round(rf_score, 4),
            "gb": round(gb_score, 4),
            "lgbm": round(lgbm_score, 4),
            "gru": round(gru_score, 4)
        }