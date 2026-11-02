import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from backend.app.database.connection import get_db

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# --- Sessions & Messages ---

def create_session(session_id: Optional[str] = None, title: str = "New Environmental Consultation") -> str:
    sid = session_id or str(uuid.uuid4())
    now = _now_iso()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (sid, title, now, now)
        )
    return sid

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return None
        return dict(row)

def list_sessions() -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT s.id, s.title, s.created_at, s.updated_at, COUNT(m.id) as message_count
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

def update_session_title(session_id: str, title: str):
    now = _now_iso()
    with get_db() as conn:
        conn.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title, now, session_id))

def add_message(session_id: str, role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> str:
    mid = str(uuid.uuid4())
    now = _now_iso()
    tool_json = json.dumps(tool_calls) if tool_calls else None
    with get_db() as conn:
        # Check if session exists; if not, create it
        s = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not s:
            conn.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, content[:40] if content else "Session", now, now)
            )
        else:
            conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))

        conn.execute(
            "INSERT INTO messages (id, session_id, role, content, tool_calls_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (mid, session_id, role, content, tool_json, now)
        )
    return mid

def get_session_messages(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
            (session_id, limit)
        ).fetchall()
        messages = []
        for r in rows:
            d = dict(r)
            if d.get("tool_calls_json"):
                try:
                    d["tool_calls"] = json.loads(d["tool_calls_json"])
                except Exception:
                    d["tool_calls"] = []
            else:
                d["tool_calls"] = []
            messages.append(d)
        return messages

# --- Datasets ---

def save_dataset(dataset_dict: Dict[str, Any]) -> str:
    did = dataset_dict.get("id") or str(uuid.uuid4())
    now = _now_iso()
    meta_json = json.dumps(dataset_dict)
    with get_db() as conn:
        conn.execute("""
            INSERT INTO datasets (id, filename, stored_path, row_count, column_count, has_timestamps, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            did,
            dataset_dict["filename"],
            dataset_dict["stored_path"],
            dataset_dict["row_count"],
            dataset_dict["column_count"],
            1 if dataset_dict.get("has_timestamps") else 0,
            meta_json,
            now
        ))
    return did

def get_dataset(dataset_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        if not row:
            return None
        meta = json.loads(row["metadata_json"])
        return meta

def list_datasets() -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM datasets ORDER BY created_at DESC").fetchall()
        result = []
        for r in rows:
            try:
                meta = json.loads(r["metadata_json"])
                result.append(meta)
            except Exception:
                result.append(dict(r))
        return result

# --- Analysis Records ---

def save_analysis_record(record_type: str, title: str, input_summary: Dict[str, Any], result: Dict[str, Any], dataset_id: Optional[str] = None) -> str:
    rid = str(uuid.uuid4())
    now = _now_iso()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO analysis_records (id, record_type, title, input_summary_json, result_json, dataset_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            rid,
            record_type,
            title,
            json.dumps(input_summary),
            json.dumps(result),
            dataset_id,
            now
        ))
    return rid

def list_analysis_records(limit: int = 50, record_type: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db() as conn:
        if record_type:
            rows = conn.execute(
                "SELECT * FROM analysis_records WHERE record_type = ? ORDER BY created_at DESC LIMIT ?",
                (record_type, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM analysis_records ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        
        results = []
        for r in rows:
            item = dict(r)
            try:
                item["input_summary"] = json.loads(item["input_summary_json"])
            except Exception:
                item["input_summary"] = {}
            try:
                item["result"] = json.loads(item["result_json"])
            except Exception:
                item["result"] = {}
            results.append(item)
        return results

def get_analysis_record(record_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM analysis_records WHERE id = ?", (record_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        try:
            item["input_summary"] = json.loads(item["input_summary_json"])
        except Exception:
            item["input_summary"] = {}
        try:
            item["result"] = json.loads(item["result_json"])
        except Exception:
            item["result"] = {}
        return item

# --- Reports ---

def save_report(report_dict: Dict[str, Any]) -> str:
    rid = report_dict.get("report_id") or str(uuid.uuid4())
    now = _now_iso()
    findings_json = json.dumps(report_dict.get("summary_findings", []))
    with get_db() as conn:
        conn.execute("""
            INSERT INTO reports (id, filename, stored_path, report_type, size_bytes, title, findings_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rid,
            report_dict["filename"],
            report_dict["stored_path"],
            report_dict["file_type"],
            report_dict["size_bytes"],
            report_dict["title"],
            findings_json,
            now
        ))
    return rid

def list_reports(limit: int = 50) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        results = []
        for r in rows:
            item = dict(r)
            try:
                item["summary_findings"] = json.loads(item["findings_json"])
            except Exception:
                item["summary_findings"] = []
            results.append(item)
        return results

def get_report(report_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        try:
            item["summary_findings"] = json.loads(item["findings_json"])
        except Exception:
            item["summary_findings"] = []
        return item
