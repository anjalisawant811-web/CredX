# CredX – Pre-Delinquency Intervention Engine

> **Hackathon Project** · AI-powered early warning system for bank employees to identify at-risk customers before loan default occurs.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)
![XGBoost](https://img.shields.io/badge/ML-XGBoost%20%2B%20RF%20%2B%20LR-orange)
![LLM](https://img.shields.io/badge/LLM-LLaMA%203.2%20Simulated-purple)

---

## 🎯 Problem Statement

Banks currently intervene **only after a customer misses a payment** — by then recovery costs are 15–20% and customer relationships are damaged. CredX changes this by identifying delinquency risk **weeks before** it occurs.

---

## 🚀 Features

| Feature | Description |
|---|---|
| 📊 **Risk Dashboard** | View all customers with color-coded risk scores (🔴🟡🟢) |
| ➕ **Add Customer** | Onboard new customers with live risk preview |
| 🧠 **AI Explanation** | LLM-generated risk narrative per customer |
| 📋 **Intervention Plan** | Step-by-step recommended actions for bank employees |
| 📨 **Message Draft** | Auto-generated SMS/Email draft for customer outreach |
| 🔍 **Search & Filter** | Filter by risk level, search by name |

---

## 🏗️ Tech Stack

- **Backend:** Python · Flask
- **Frontend:** HTML · CSS · JavaScript · Bootstrap 5
- **ML Models:** XGBoost (primary) + Random Forest + Logistic Regression (ensemble)
- **LLM Layer:** LLaMA 3.2 3B (simulated via prompt engineering for demo)

---

## 📁 Project Structure

```
CredX/
│
├── app.py                    # Flask backend (routes + ML + LLM logic)
├── requirements.txt          # Python dependencies
├── README.md
│
├── templates/
│   ├── dashboard.html        # Main employee dashboard
│   ├── add_customer.html     # Customer onboarding form
│   └── customer_detail.html  # Per-customer risk detail view
│
├── static/
│   └── styles.css            # Dark fintech UI theme
│
└── data/
    └── sample_customers.csv  # Preloaded dataset (8 customers, varied risk)
```

---

## ⚡ How to Run

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/CredX.git
cd CredX
```

### 2. Create Virtual Environment (recommended)
```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the App
```bash
python app.py
```

### 5. Open in Browser
```
http://127.0.0.1:5000
```

---

## 🤖 ML Model Details

The risk score (0–100) is computed by an **ensemble of three models**:

| Model | Weight | Role |
|---|---|---|
| XGBoost | 40% | Primary predictor — captures non-linear patterns |
| Random Forest | 35% | Stability signal — reduces variance |
| Logistic Regression | 25% | Explainability — linear boundary |

**Input features:**
- Monthly Income
- Monthly Expenses (expense ratio)
- Missed Payments (last 6 months)
- Credit Utilization (%)

**Risk Categories:**
- 🔴 High Risk: Score ≥ 70
- 🟡 Medium Risk: Score 40–69
- 🟢 Low Risk: Score < 40

---

## 🧠 LLM Integration

For the hackathon demo, LLM outputs are **prompt-engineered simulations** of LLaMA 3.2 3B responses. The system generates:

1. **Risk Explanation** — Natural language description of why the customer is at risk
2. **Intervention Plan** — Ranked list of recommended bank actions
3. **Customer Message** — Ready-to-send SMS/Email draft

In production, these would be served by a local LLaMA 3.2 / Phi-4 Mini / Gemma 3 inference endpoint.

---

## 📊 Sample Output

```
Customer: Anjali Mehta
Risk Score: 87.3 / 100
Category: 🔴 High Risk

AI Explanation: Anjali Mehta presents a high delinquency risk. 
Primary drivers include 4 missed payments, credit utilization at 91%, 
and expenses consuming 96.7% of income...

Intervention: 
1. Schedule urgent call within 48 hours
2. Offer debt restructuring — extend tenure 12 months
3. Propose EMI holiday of 1–2 months
...
```

---

## 👥 Use Case: Bank Employee Workflow

1. **Employee logs in** → sees Dashboard with all monitored customers
2. **Sorts by High Risk** → identifies customers needing immediate action
3. **Clicks "View"** → sees full AI-generated risk profile
4. **Reads Intervention Plan** → decides next action
5. **Copies Message Draft** → sends personalized outreach to customer
6. **Adds new customer** → enters financial data → gets instant risk score

---

## 🔮 Future Scope

- Real-time transaction stream ingestion (Kafka)
- Actual LLaMA 3.2 local inference via Ollama
- Multi-employee role system (RM, Credit Officer, Branch Manager)
- Historical trend charts per customer
- WhatsApp Business API integration for message delivery
- Model retraining pipeline with feedback loop

---

## 📄 License

MIT License — Free for educational and hackathon use.

---

*Built for hackathon · CredX v1.0*
