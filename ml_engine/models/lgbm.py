
class LightGBMModel:

    def predict_proba(self, f):
        # fast, balanced, production-like scorer
        return min((
            0.35 * f.dti +
            0.30 * f.utilization_risk +
            0.25 * f.payment_risk +
            0.10 * f.expense_pressure
        ), 1.0)