"""
Universal AI Governance (UAIG) - 21 CFR Part 11 Audit Ledger
Cryptographically chained, append-only SQLite persistence engine.
"""
import sqlite3
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uaig_core.models import AuditRecordSchema, SystemContext, LLMToolPayload, VerificationDecision

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

class CFR21AuditLedger:
    def __init__(self, db_path: str = "uaig_audit_ledger.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=FULL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_records (
                    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_utc TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    is_authorized INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    diagnostic_message TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    record_hash TEXT NOT NULL UNIQUE
                );
            """)
            # Enforce immutability via SQLite triggers
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_audit_update
                BEFORE UPDATE ON audit_records
                BEGIN
                    SELECT RAISE(FAIL, '21 CFR Part 11 Violation: Updates are strictly prohibited on audit trail.');
                END;
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
                BEFORE DELETE ON audit_records
                BEGIN
                    SELECT RAISE(FAIL, '21 CFR Part 11 Violation: Deletions are strictly prohibited on audit trail.');
                END;
            """)
            conn.commit()

    def get_latest_hash(self) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT record_hash FROM audit_records ORDER BY record_id DESC LIMIT 1;")
            row = cursor.fetchone()
            return row[0] if row else GENESIS_HASH

    def commit_record(
        self,
        context: SystemContext,
        payload: LLMToolPayload,
        decision: VerificationDecision
    ) -> str:
        previous_hash = self.get_latest_hash()
        timestamp_utc = datetime.now(timezone.utc).isoformat()
        payload_serialized = json.dumps(payload.model_dump(), sort_keys=True)

        # Cryptographic Hash Chain Computation
        hasher = hashlib.sha256()
        hasher.update(previous_hash.encode("utf-8"))
        hasher.update(timestamp_utc.encode("utf-8"))
        hasher.update(context.session_id.encode("utf-8"))
        hasher.update(context.user_id.encode("utf-8"))
        hasher.update(payload.action_name.encode("utf-8"))
        hasher.update(decision.status.encode("utf-8"))
        hasher.update(payload_serialized.encode("utf-8"))
        hasher.update(decision.diagnostic_message.encode("utf-8"))
        record_hash = hasher.hexdigest()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO audit_records (
                    timestamp_utc, session_id, user_id, action_name,
                    status, is_authorized, payload_json, diagnostic_message,
                    previous_hash, record_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                timestamp_utc,
                context.session_id,
                context.user_id,
                payload.action_name,
                decision.status,
                1 if decision.is_authorized else 0,
                payload_serialized,
                decision.diagnostic_message,
                previous_hash,
                record_hash
            ))
            conn.commit()

        return record_hash

    def verify_ledger_integrity(self) -> Tuple[bool, int, str]:
        """
        Traverses the complete audit ledger from genesis to head and verifies
        that every SHA-256 record hash matches its forward computation.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT record_id, timestamp_utc, session_id, user_id, action_name,
                       status, payload_json, diagnostic_message, previous_hash, record_hash
                FROM audit_records ORDER BY record_id ASC;
            """)
            rows = cursor.fetchall()

        if not rows:
            return True, 0, "Audit ledger is empty. Integrity verified."

        expected_prev = GENESIS_HASH
        for row in rows:
            rec_id, ts, sess_id, uid, act, st, payload_json, diag, prev_h, rec_h = row
            
            if prev_h != expected_prev:
                return False, rec_id, f"Integrity Failure at Record {rec_id}: prev_hash {prev_h} != expected {expected_prev}"

            hasher = hashlib.sha256()
            hasher.update(prev_h.encode("utf-8"))
            hasher.update(ts.encode("utf-8"))
            hasher.update(sess_id.encode("utf-8"))
            hasher.update(uid.encode("utf-8"))
            hasher.update(act.encode("utf-8"))
            hasher.update(st.encode("utf-8"))
            hasher.update(payload_json.encode("utf-8"))
            hasher.update(diag.encode("utf-8"))
            computed_h = hasher.hexdigest()

            if computed_h != rec_h:
                return False, rec_id, f"Cryptographic Mismatch at Record {rec_id}: computed {computed_h} != stored {rec_h}"

            expected_prev = rec_h

        return True, len(rows), f"All {len(rows)} audit records verified. Cryptographic chain intact."

    def list_records(self, limit: int = 50) -> List[AuditRecordSchema]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT record_id, timestamp_utc, session_id, user_id, action_name,
                       status, is_authorized, payload_json, diagnostic_message,
                       previous_hash, record_hash
                FROM audit_records ORDER BY record_id DESC LIMIT ?;
            """, (limit,))
            rows = cursor.fetchall()

        return [
            AuditRecordSchema(
                record_id=r[0],
                timestamp_utc=r[1],
                session_id=r[2],
                user_id=r[3],
                action_name=r[4],
                status=r[5],
                is_authorized=bool(r[6]),
                payload_json=r[7],
                diagnostic_message=r[8],
                previous_hash=r[9],
                record_hash=r[10]
            ) for r in rows
        ]
