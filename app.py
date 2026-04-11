from flask import Flask, render_template, request, redirect, url_for, jsonify
import random
import math
import os
from datetime import datetime

# Explicitly set template and static folders relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

# ─── In-Memory Database ────────────────────────────────────────────────────────
customers = [
    {
        "id": 1,
        "name": "Priya Sharma",
        "income": 85000,
        "expenses": 72000,
        "missed_payments": 2,
        "credit_utilization": 78,
        "added_on": "2025-01-10",
        "email": "priya.sharma@email.com",
        "phone": "+91-9876543210",
        "loan_amount": 500000,
        "loan_type": "Personal Loan"
    },
    {
        "id": 2,
        "name": "Rahul Verma",
        "income": 120000,
        "expenses": 45000,
        "missed_payments": 0,
        "credit_utilization": 22,
        "added_on": "2025-01-15",
        "email": "rahul.verma@email.com",
        "phone": "+91-9123456789",
        "loan_amount": 800000,
        "loan_type": "Home Loan"
    },
    {
        "id": 3,
        "name": "Anjali Mehta",
        "income": 60000,
        "expenses": 58000,
        "missed_payments": 4,
        "credit_utilization": 91,
        "added_on": "2025-01-18",
        "email": "anjali.mehta@email.com",
        "phone": "+91-9988776655",
        "loan_amount": 300000,
        "loan_type": "Personal Loan"
    },
    {
        "id": 4,
        "name": "Vikram Singh",
        "income": 200000,
        "expenses": 80000,
        "missed_payments": 0,
        "credit_utilization": 15,
        "added_on": "2025-01-20",
        "email": "vikram.singh@email.com",
        "phone": "+91-9001234567",
        "loan_amount": 2000000,
        "loan_type": "Business Loan"
    },
    {
        "id": 5,
        "name": "Sneha Patel",
        "income": 55000,
        "expenses": 50000,
        "missed_payments": 1,
        "credit_utilization": 55,
        "added_on": "2025-02-01",
        "email": "sneha.patel@email.com",
        "phone": "+91-9765432101",
        "loan_amount": 250000,
        "loan_type": "Vehicle Loan"
    },
    {
        "id": 6,
        "name": "Arjun Nair",
        "income": 95000,
        "expenses": 88000,
        "missed_payments": 3,
        "credit_utilization": 85,
        "added_on": "2025-02-05",
        "email": "arjun.nair@email.com",
        "phone": "+91-9345678901",
        "loan_amount": 600000,
        "loan_type": "Personal Loan"
    },
    {
        "id": 7,
        "name": "Meena Krishnan",
        "income": 150000,
        "expenses": 60000,
        "missed_payments": 0,
        "credit_utilization": 10,
        "added_on": "2025-02-10",
        "email": "meena.k@email.com",
        "phone": "+91-9456789012",
        "loan_amount": 1500000,
        "loan_type": "Home Loan"
    },
    {
        "id": 8,
        "name": "Deepak Joshi",
        "income": 42000,
        "expenses": 41000,
        "missed_payments": 5,
        "credit_utilization": 95,
        "added_on": "2025-02-15",
        "email": "deepak.joshi@email.com",
        "phone": "+91-9567890123",
        "loan_amount": 150000,
        "loan_type": "Personal Loan"
    },
]

next_id = 9  # auto-increment

# ─── ML Model (Ensemble Simulation) ───────────────────────────────────────────
def compute_risk_score(income, expenses, missed_payments, credit_utilization):
    """
    Simulates an ensemble of XGBoost + Random Forest + Logistic Regression.
    Returns score 0-100 (higher = riskier).
    """
    income = max(income, 1)
    expense_ratio = min(expenses / income, 1.5)

    # Logistic Regression component (linear boundary)
    lr_score = (
        0.30 * expense_ratio +
        0.35 * (missed_payments / 6) +
        0.35 * (credit_utilization / 100)
    )

    # Random Forest component (non-linear interaction)
    rf_score = math.sqrt(
        0.25 * (expense_ratio ** 2) +
        0.40 * ((missed_payments / 6) ** 2) +
        0.35 * ((credit_utilization / 100) ** 2)
    )

    # XGBoost component (boosted signal with missed_payments emphasis)
    xgb_raw = (
        1.5 * (missed_payments / 6) +
        1.0 * (credit_utilization / 100) +
        0.5 * expense_ratio
    )
    xgb_score = min(xgb_raw / 3, 1.0)

    # Ensemble (weighted average)
    ensemble = 0.40 * xgb_score + 0.35 * rf_score + 0.25 * lr_score
    return round(min(ensemble * 100, 100), 1)

def get_risk_category(score):
    if score >= 70:
        return "High Risk"
    elif score >= 40:
        return "Medium Risk"
    else:
        return "Low Risk"

def get_risk_color(score):
    if score >= 70:
        return "danger"
    elif score >= 40:
        return "warning"
    else:
        return "success"

# ─── LLM Simulation Layer ──────────────────────────────────────────────────────
def generate_llm_explanation(customer, score, category):
    name = customer["name"]
    income = customer["income"]
    expenses = customer["expenses"]
    missed = customer["missed_payments"]
    util = customer["credit_utilization"]
    expense_ratio = round((expenses / income) * 100, 1)

    if category == "High Risk":
        explanation = (
            f"{name} presents a high delinquency risk (Score: {score}/100). "
            f"The primary drivers are {missed} missed payment(s) in recent cycles, "
            f"a critically elevated credit utilization of {util}%, "
            f"and an expense-to-income ratio of {expense_ratio}% — "
            f"leaving almost no financial buffer. The ensemble model (XGBoost dominant) "
            f"detects strong non-linear stress patterns consistent with pre-default behavior. "
            f"Immediate intervention is recommended to prevent loan default."
        )
        intervention = (
            f"1. Schedule an urgent call with {name} within 48 hours.\n"
            f"2. Offer a Debt Restructuring Plan — extend tenure by 12 months.\n"
            f"3. Propose an EMI holiday of 1–2 months to ease cash flow.\n"
            f"4. Flag account for daily monitoring by the credit risk team.\n"
            f"5. Initiate a financial counseling session referral."
        )
        message = (
            f"Dear {name},\n\n"
            f"We noticed some recent changes in your account activity and want to reach out proactively. "
            f"At [Bank Name], we are committed to supporting our valued customers.\n\n"
            f"We would like to discuss some flexible repayment options that may help ease your financial commitments. "
            f"Our team is available for a confidential consultation at your convenience.\n\n"
            f"Please contact your relationship manager or call our dedicated support line at 1800-XXX-XXXX.\n\n"
            f"Warm regards,\nCustomer Care Team\n[Bank Name]"
        )
    elif category == "Medium Risk":
        explanation = (
            f"{name} is at medium delinquency risk (Score: {score}/100). "
            f"Key indicators include {missed} missed payment(s), "
            f"credit utilization at {util}%, and expenses consuming {expense_ratio}% of income. "
            f"The Random Forest model identifies moderate stress signals with some volatility. "
            f"Preventive engagement now can significantly reduce escalation probability."
        )
        intervention = (
            f"1. Send a proactive financial wellness check SMS/email.\n"
            f"2. Offer optional EMI restructuring or top-up loan consolidation.\n"
            f"3. Enroll customer in auto-debit to prevent accidental missed payments.\n"
            f"4. Set bi-weekly monitoring alert for credit utilization changes.\n"
            f"5. Share budgeting tips via in-app notification."
        )
        message = (
            f"Dear {name},\n\n"
            f"Thank you for being a valued customer. We are reaching out as part of our "
            f"proactive customer wellness program.\n\n"
            f"We have some personalized offers that may help you manage your finances better, "
            f"including flexible EMI options and financial planning support.\n\n"
            f"To know more, please visit your nearest branch or call 1800-XXX-XXXX.\n\n"
            f"Best regards,\nRelationship Management Team\n[Bank Name]"
        )
    else:
        explanation = (
            f"{name} is classified as low delinquency risk (Score: {score}/100). "
            f"Financials are stable: {missed} missed payment(s), "
            f"credit utilization at {util}%, and a healthy expense-to-income ratio of {expense_ratio}%. "
            f"The Logistic Regression model confirms strong creditworthiness. "
            f"Routine monitoring is sufficient at this stage."
        )
        intervention = (
            f"1. No immediate intervention required.\n"
            f"2. Continue standard monthly monitoring cycle.\n"
            f"3. Consider offering loyalty rewards or credit limit upgrade.\n"
            f"4. Flag for cross-sell opportunities (insurance, investments).\n"
            f"5. Schedule routine annual review."
        )
        message = (
            f"Dear {name},\n\n"
            f"We appreciate your continued trust in [Bank Name]. "
            f"Your account is in excellent standing and we value your relationship with us.\n\n"
            f"As a token of appreciation, we would like to offer you exclusive benefits "
            f"and preferential rates on our premium products.\n\n"
            f"To explore these offers, contact your relationship manager or visit our website.\n\n"
            f"Sincerely,\nCustomer Experience Team\n[Bank Name]"
        )
    return explanation, intervention, message

# ─── Enrich customer with ML + LLM outputs ────────────────────────────────────
def enrich_customer(c):
    score = compute_risk_score(
        c["income"], c["expenses"], c["missed_payments"], c["credit_utilization"]
    )
    category = get_risk_category(score)
    color = get_risk_color(score)
    explanation, intervention, message = generate_llm_explanation(c, score, category)
    return {
        **c,
        "risk_score": score,
        "risk_category": category,
        "risk_color": color,
        "explanation": explanation,
        "intervention": intervention,
        "message": message,
    }

# Pre-enrich all preloaded customers
for i, c in enumerate(customers):
    customers[i] = enrich_customer(c)

# ─── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def dashboard():
    stats = {
        "total": len(customers),
        "high": sum(1 for c in customers if c["risk_category"] == "High Risk"),
        "medium": sum(1 for c in customers if c["risk_category"] == "Medium Risk"),
        "low": sum(1 for c in customers if c["risk_category"] == "Low Risk"),
    }
    return render_template("dashboard.html", customers=customers, stats=stats)

@app.route("/add_customer", methods=["GET", "POST"])
def add_customer():
    global next_id
    if request.method == "POST":
        try:
            new_c = {
                "id": next_id,
                "name": request.form["name"],
                "income": float(request.form["income"]),
                "expenses": float(request.form["expenses"]),
                "missed_payments": int(request.form["missed_payments"]),
                "credit_utilization": float(request.form["credit_utilization"]),
                "added_on": datetime.now().strftime("%Y-%m-%d"),
                "email": request.form.get("email", "N/A"),
                "phone": request.form.get("phone", "N/A"),
                "loan_amount": float(request.form.get("loan_amount", 0)),
                "loan_type": request.form.get("loan_type", "Personal Loan"),
            }
            enriched = enrich_customer(new_c)
            customers.append(enriched)
            next_id += 1
            return redirect(url_for("customer_detail", customer_id=enriched["id"]))
        except Exception as e:
            return render_template("add_customer.html", error=str(e))
    return render_template("add_customer.html")

@app.route("/customer/<int:customer_id>")
def customer_detail(customer_id):
    customer = next((c for c in customers if c["id"] == customer_id), None)
    if not customer:
        return redirect(url_for("dashboard"))
    return render_template("customer_detail.html", customer=customer)

@app.route("/api/stats")
def api_stats():
    return jsonify({
        "total": len(customers),
        "high": sum(1 for c in customers if c["risk_category"] == "High Risk"),
        "medium": sum(1 for c in customers if c["risk_category"] == "Medium Risk"),
        "low": sum(1 for c in customers if c["risk_category"] == "Low Risk"),
        "scores": [c["risk_score"] for c in customers],
        "names": [c["name"].split()[0] for c in customers],
    })

if __name__ == "__main__":
    app.run(debug=True)
