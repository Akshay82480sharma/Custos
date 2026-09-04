<div align="center">
  <h1>CUSTOS 🛡️</h1>
  <p><b>Autonomous Merchant Finance Agent</b></p>
  <p><i>Protect revenue. Recover what's lost. Find what's next.</i></p>
</div>

---

## 📖 Overview

Merchants lose revenue silently through failed payments, overdue invoices, and unaddressed disputes. **CUSTOS** is an autonomous agent that continuously watches a merchant's transaction stream, diagnoses revenue leakage as it happens, decides on a bounded recovery action, executes it, and logs every decision it made and why.

It acts as a guardian standing between "money is at risk" and "money is lost" — not just a dashboard that reports leakage after the fact, but an active, intelligent agent working in the background.

## 🚀 Key Features

- **Ingest & Detect:** Monitors payment gateways for failed charges, overdue invoices, and disputes.
- **AI Classification & Reasoning:** Uses a reasoning engine to analyze customer history, transaction context, and diagnose root causes with plain-language explanations.
- **Deterministic Policy Gate:** Ensures bounded autonomy. The AI only *recommends* actions; strict deterministic rules vet every recommendation before execution.
- **Automated Execution:** Executes approved actions (e.g., retrying a payment, sending a reminder) automatically.
- **Auditability & Explainability:** Every single decision from detection to outcome is written to an append-only audit log, ensuring the AI is never a black box.
- **Command Center:** A beautiful, responsive dashboard to review actions, recovered revenue, risk exposure, and growth opportunities.

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, SQLite
- **AI/Logic:** Gemini for reasoning + generation (Mocked in simulation for safe demo execution)
- **Frontend (Server-Side Rendered):** Instead of a decoupled SPA, the frontend is built directly into the backend using FastAPI's SSR capabilities. It uses Jinja2 Templates, HTML5, Vanilla JavaScript, and raw CSS. This keeps the architecture incredibly lightweight and allows launching both the API and UI from a single unified server.
- **Payments:** Designed around Razorpay webhooks

## 🏃‍♂️ How to Run Locally

You can run the entire pipeline and launch the dashboard with a single click on Windows!

### Prerequisites
Make sure you have Python 3.10+ installed.

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/custos-finance-agent.git
   cd custos-finance-agent
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Demo
Just double-click **`start_demo.bat`** (on Windows). 

**Or, run it manually via terminal:**
1. Process events through the autonomous pipeline:
   ```bash
   python run_pipeline.py
   ```
2. Start the dashboard server:
   ```bash
   python -m uvicorn backend.main:app --port 8000
   ```
3. Open your browser to http://127.0.0.1:8000

## 📂 Project Structure

- `backend/`: The core API, reasoning engine, policy gates, and services.
- `backend/templates/`: The HTML dashboard UI.
- `backend/static/`: CSS styling for the dashboard.
- `docs/`: Comprehensive specifications (PRD, System Architecture, Memory Architecture, etc.)
- `custos.db`: The SQLite database containing processed events.

## 🤝 Built For Hackathon

This project was built for the AI Revenue Recovery track. It demonstrates how autonomous agents can safely operate within strict financial policies to recover lost revenue.
