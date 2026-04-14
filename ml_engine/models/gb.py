
class GradientBoostingModel:

    def predict_proba(self, f):
        # sequential error correction simulation (boosting behavior)
        base = (
            1.5 * f.dti +
            2.0 * f.payment_risk +
            1.2 * f.utilization_risk
        )

        return min(base / 5.0, 1.0)