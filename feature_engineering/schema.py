from dataclasses import dataclass

@dataclass(frozen=True)
class FeatureVector:
    dti: float
    utilization_risk: float
    payment_risk: float
    expense_pressure: float
    financial_stress_index: float