import sqlite3

import os

def get_db():
    db_path = os.environ.get(
        "CUSTOS_DB_PATH",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "custos.db"),
    )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, source_id TEXT UNIQUE, type TEXT, amount INTEGER, status TEXT, customer_ref TEXT, raw_payload TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS classifications (event_id TEXT PRIMARY KEY, category TEXT, classified_at TEXT);
            CREATE TABLE IF NOT EXISTS llm_decisions (event_id TEXT PRIMARY KEY, diagnosis TEXT, recommended_action TEXT, confidence REAL, reasoning TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS policy_checks (event_id TEXT PRIMARY KEY, decision TEXT, reason TEXT, checked_at TEXT);
            CREATE TABLE IF NOT EXISTS actions (event_id TEXT PRIMARY KEY, action_type TEXT, executed_at TEXT, result TEXT);
            CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY, event_id TEXT, stage TEXT, detail TEXT, timestamp TEXT);
            
            CREATE TABLE IF NOT EXISTS risk_assessments (id TEXT PRIMARY KEY, event_id TEXT UNIQUE, risk_score REAL, is_safe BOOLEAN, verdict TEXT, signals TEXT, reasoning TEXT, assessed_at TEXT);
            CREATE TABLE IF NOT EXISTS growth_opportunities (id TEXT PRIMARY KEY, event_id TEXT UNIQUE, has_opportunity BOOLEAN, opportunities TEXT, best_offer TEXT, reasoning TEXT, identified_at TEXT);
            CREATE TABLE IF NOT EXISTS finance_reconciliations (id TEXT PRIMARY KEY, event_id TEXT UNIQUE, expected_settlement REAL, fee_deducted REAL, fee_rate TEXT, settlement_date TEXT, reconciliation_status TEXT, reasoning TEXT, reconciled_at TEXT);
            CREATE TABLE IF NOT EXISTS pipeline_summaries (id TEXT PRIMARY KEY, event_id TEXT UNIQUE, total_stages INTEGER, completed INTEGER, skipped INTEGER, total_ms INTEGER, verdict TEXT, verdict_summary TEXT, created_at TEXT);

            CREATE TABLE IF NOT EXISTS recovery_cases (
                id TEXT PRIMARY KEY,
                event_id TEXT UNIQUE NOT NULL,
                state TEXT NOT NULL,
                amount_at_risk INTEGER NOT NULL,
                verified_recovered_amount INTEGER NOT NULL DEFAULT 0,
                retry_count INTEGER NOT NULL DEFAULT 0,
                retry_limit INTEGER NOT NULL DEFAULT 3,
                recovery_probability REAL,
                expected_recovery_amount INTEGER NOT NULL DEFAULT 0,
                policy_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS action_runs (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                recovery_case_id TEXT,
                idempotency_key TEXT UNIQUE NOT NULL,
                action_type TEXT NOT NULL,
                authorization TEXT NOT NULL,
                execution_status TEXT NOT NULL,
                execution_detail TEXT,
                simulated INTEGER NOT NULL DEFAULT 1,
                executed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS verification_results (
                id TEXT PRIMARY KEY,
                recovery_case_id TEXT NOT NULL,
                action_run_id TEXT NOT NULL,
                provider_status TEXT NOT NULL,
                verified INTEGER NOT NULL,
                verified_amount INTEGER NOT NULL DEFAULT 0,
                verification_mode TEXT NOT NULL,
                checked_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settlements (
                id TEXT PRIMARY KEY,
                reference TEXT UNIQUE NOT NULL,
                gross_amount INTEGER NOT NULL,
                net_amount INTEGER NOT NULL,
                status TEXT NOT NULL,
                settled_at TEXT
            );
            CREATE TABLE IF NOT EXISTS merchant_memory (
                memory_id TEXT PRIMARY KEY,
                merchant_id TEXT NOT NULL,
                type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT
            );
            CREATE TABLE IF NOT EXISTS customer_memory (
                memory_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT
            );
            CREATE TABLE IF NOT EXISTS recovery_memory (
                memory_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                customer_id TEXT,
                action_type TEXT NOT NULL,
                outcome TEXT NOT NULL,
                amount INTEGER NOT NULL,
                time_to_recovery INTEGER,
                policy_version TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

        # SQLite migrations for databases created by the original prototype.
        columns = {row["name"] for row in db.execute("PRAGMA table_info(policy_checks)")}
        if "policy_version" not in columns:
            db.execute("ALTER TABLE policy_checks ADD COLUMN policy_version TEXT")
        if "authorization" not in columns:
            db.execute("ALTER TABLE policy_checks ADD COLUMN authorization TEXT")
        risk_columns = {row["name"] for row in db.execute("PRAGMA table_info(risk_assessments)")}
        if "risk_level" not in risk_columns:
            db.execute("ALTER TABLE risk_assessments ADD COLUMN risk_level TEXT")
        growth_columns = {row["name"] for row in db.execute("PRAGMA table_info(growth_opportunities)")}
        if "probability" not in growth_columns:
            db.execute("ALTER TABLE growth_opportunities ADD COLUMN probability REAL")
        if "potential_value" not in growth_columns:
            db.execute("ALTER TABLE growth_opportunities ADD COLUMN potential_value INTEGER")

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
