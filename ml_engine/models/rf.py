import numpy as np

class RandomForestModel:

    def predict_proba(self, f):
        # rule-based tree ensemble approximation
        score = (
            0.4 * (f.dti ** 2) +
            0.3 * f.utilization_risk +
            0.2 * f.payment_risk +
            0.1 * np.sqrt(f.expense_pressure)
        )

        return min(score, 1.0)