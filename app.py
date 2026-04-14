from flask import Flask, render_template, request, redirect, url_for, jsonify,send_file
import random
import math
import os

from db.connection import get_conn
from datetime import datetime
from services import RiskService
from db import init_db, get_conn
from sar_report import get_sar_records, generate_sar_pdf_bytes
import sqlite3

init_db()

# ─── App Setup ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

init_db()
risk_service = RiskService()


# ─── ML Model (Ensemble Simulation) ───────────────────────────────────────────
def compute_risk_score(income, expenses, missed_payments, credit_utilization):
    """
    Simulates an ensemble of XGBoost + Random Forest + Logistic Regression.
    Returns score 0-100 (higher = riskier).
    """
    income = max(income, 1)
    expense_ratio = min(expenses / income, 1.5)

    # Logistic Regression component
    lr_score = (
        0.30 * expense_ratio +
        0.35 * (missed_payments / 6) +
        0.35 * (credit_utilization / 100)
    )

    # Random Forest component
    rf_score = math.sqrt(
        0.25 * (expense_ratio ** 2) +
        0.40 * ((missed_payments / 6) ** 2) +
        0.35 * ((credit_utilization / 100) ** 2)
    )

    # XGBoost component
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


# ─── Helper: Enrich customer ──────────────────────────────────────────────────
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


# ─── Helper: Safe type conversion ─────────────────────────────────────────────
def safe_float(val, default=0.0):
    try:
        val = str(val).replace(",", "").strip()
        return float(val) if val != "" else default
    except:
        return default


def safe_int(val, default=0):
    try:
        val = str(val).strip()
        return int(val) if val != "" else default
    except:
        return default


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()

    customers_db = [dict(row) for row in rows]
    stats = {
        "total": len(customers_db),
        "high": sum(1 for c in customers_db if c["risk_category"] == "High Risk"),
        "medium": sum(1 for c in customers_db if c["risk_category"] == "Medium Risk"),
        "low": sum(1 for c in customers_db if c["risk_category"] == "Low Risk"),
    }
    return render_template("dashboard.html", customers=customers_db, stats=stats)


@app.route("/add_customer", methods=["GET", "POST"])
def add_customer():
    if request.method == "POST":
        try:
            raw_data = {
                "name": request.form["name"],
                "income": safe_float(request.form.get("income")),
                "expenses": safe_float(request.form.get("expenses")),
                "missed_payments": safe_int(request.form.get("missed_payments")),
                "credit_utilization": safe_float(request.form.get("credit_utilization")),
                "loan_amount": safe_float(request.form.get("loan_amount")),
                "loan_type": request.form.get("loan_type", "Personal Loan"),
                "email": request.form.get("email", "N/A"),
                "phone": request.form.get("phone", "N/A"),
                "added_on": datetime.now().strftime("%Y-%m-%d")
            }

            result = risk_service.evaluate(raw_data)
            score = result["risk_score"]
            category = get_risk_category(score)
            color = get_risk_color(score)
            explanation, intervention, message = generate_llm_explanation(raw_data, score, category)

            enriched = {
                **raw_data,
                "risk_score": score,
                "risk_category": category,
                "risk_color": color,
                "explanation": explanation,
                "intervention": intervention,
                "message": message,
                "ml_breakdown": result
            }

            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO customers (
                    name, income, expenses, missed_payments,
                    credit_utilization, loan_amount, loan_type,
                    email, phone, added_on, risk_score, risk_category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                enriched["name"], enriched["income"], enriched["expenses"],
                enriched["missed_payments"], enriched["credit_utilization"],
                enriched["loan_amount"], enriched["loan_type"],
                enriched["email"], enriched["phone"], enriched["added_on"],
                enriched["risk_score"], enriched["risk_category"]
            ))
            conn.commit()
            customer_id = cur.lastrowid
            conn.close()

            return redirect(url_for("customer_detail", customer_id=customer_id))

        except Exception as e:
            return render_template("add_customer.html", error=str(e))

    return render_template("add_customer.html")


@app.route("/customer/<int:customer_id>")
def customer_detail(customer_id):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    row = cur.fetchone()
    conn.close()

    if row is None:
        return "Customer not found", 404

    customer = dict(row)

    service = RiskService()
    result = service.evaluate(customer)

    customer["risk_score"] = result["risk_score"]
    customer["shap"] = result.get("shap", {})  # 'shap' is not returned by the engine; default to empty dict

    explanation, intervention, message = generate_llm_explanation(
        customer, customer["risk_score"], customer["risk_category"]
    )
    customer["explanation"] = explanation
    customer["intervention"] = intervention
    customer["message"] = message

    return render_template("customer_detail.html", customer=customer)


@app.route("/admin")
def admin_panel():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY id DESC")
    customers = cur.fetchall()
    conn.close()
    return render_template("admin.html", customers=customers)


@app.route("/api/stats")
def api_stats():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT risk_score, risk_category, name FROM customers")
    rows = cur.fetchall()
    conn.close()
    return jsonify({
        "total": len(rows),
        "high": sum(1 for r in rows if r["risk_category"] == "High Risk"),
        "medium": sum(1 for r in rows if r["risk_category"] == "Medium Risk"),
        "low": sum(1 for r in rows if r["risk_category"] == "Low Risk"),
        "scores": [r["risk_score"] for r in rows],
        "names": [r["name"] for r in rows],
    })


@app.route("/sar")
def sar_page():
    records = get_sar_records()
 
    high_n   = sum(1 for r in records if r["risk_level"] == "HIGH")
    medium_n = sum(1 for r in records if r["risk_level"] == "MEDIUM")
    low_n    = sum(1 for r in records if r["risk_level"] == "LOW")
 
    stats = {
        "total":  len(records),
        "high":   high_n,
        "medium": medium_n,
        "low":    low_n,
    }
 
    return render_template(
        "sar.html",
        records=records,
        stats=stats,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


@app.route("/api/sar")
def api_sar():
    try:
        cid = request.args.get("customer_id", type=int)
        records = get_sar_records(customer_id=cid)
        return jsonify({
            "report_type": "Suspicious Activity Report (SAR)",
            "generated_at": datetime.now().isoformat(),
            "total_records": len(records),
            "records": records,
        })
    except Exception as e:
        return jsonify({"error": str(e), "records": []}), 500

@app.route("/api/sar/pdf")
def sar_pdf_download():
    """Stream a freshly-generated SAR PDF to the browser as a download."""
    cid = request.args.get("customer_id", type=int)
    buf = generate_sar_pdf_bytes(customer_id=cid)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_cid{cid}" if cid else "_all"
    filename = f"SAR_Report{suffix}_{ts}.pdf"
 
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
 


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)