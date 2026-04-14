import numpy as np

class LogisticRegressionModel:

    def predict_proba(self, f):
        # linear logit + sigmoid (calibrated baseline model)
        logit = (
            2.0 * f.dti +
            1.5 * f.utilization_risk +
            1.8 * f.payment_risk +
            1.2 * f.expense_pressure
        )

        return 1 / (1 + np.exp(-logit))