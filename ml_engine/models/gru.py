
class GRUModel:

    def predict_proba(self, f):
        # sequence behavior approximation (no real DL needed)

        memory_risk = (
            0.5 * f.payment_risk +
            0.3 * f.utilization_risk +
            0.2 * f.dti
        )

        # slight nonlinear amplification (behavior drift effect)
        return min(memory_risk ** 1.1, 1.0)