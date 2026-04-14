import numpy as np
from .schema import FeatureVector


class FeatureEngine:

    @staticmethod
    def _safe_div(a, b):
        return float(a) / float(b) if b not in [0, None] else 0.0

    @staticmethod
    def debt_to_income(income, expenses, loan_amount):
        emi_proxy = loan_amount * 0.02  # standardized assumption
        return FeatureEngine._safe_div(expenses + emi_proxy, income)

    @staticmethod
    def utilization_risk(utilization):
        # continuous risk scaling (not bucketed)
        return min(max(utilization / 100.0, 0.0), 1.0)

    @staticmethod
    def payment_risk(missed_payments):
        # exponential penalty for delinquency behavior
        return min((missed_payments ** 1.5) / 10.0, 1.0)

    @staticmethod
    def expense_pressure(income, expenses):
        return FeatureEngine._safe_div(expenses, income)

    @staticmethod
    def financial_stress(dti, util_risk, pay_risk, expense_pressure):
        # weighted nonlinear composite risk index
        return float(
            (0.30 * dti) +
            (0.30 * util_risk) +
            (0.25 * pay_risk) +
            (0.15 * expense_pressure)
        )

    @staticmethod
    def build(data) -> FeatureVector:

        income = float(data["income"])
        expenses = float(data["expenses"])
        loan_amount = float(data.get("loan_amount", 0))
        utilization = float(data["credit_utilization"])
        missed = float(data["missed_payments"])

        dti = FeatureEngine.debt_to_income(income, expenses, loan_amount)
        util_risk = FeatureEngine.utilization_risk(utilization)
        pay_risk = FeatureEngine.payment_risk(missed)
        exp_pressure = FeatureEngine.expense_pressure(income, expenses)

        stress = FeatureEngine.financial_stress(
            dti, util_risk, pay_risk, exp_pressure
        )

        return FeatureVector(
            dti=dti,
            utilization_risk=util_risk,
            payment_risk=pay_risk,
            expense_pressure=exp_pressure,
            financial_stress_index=stress
        )