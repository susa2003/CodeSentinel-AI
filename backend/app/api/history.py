from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional

from backend.app.database.repository import (
    list_analysis_records, get_analysis_record
)

router = APIRouter(prefix="/history", tags=["History & Audit Trail"])

@router.get("")
def get_analysis_history(limit: int = 50, record_type: Optional[str] = None):
    """Retrieve chronologically ordered analysis and prediction audit records."""
    records = list_analysis_records(limit=limit, record_type=record_type)
    return records

@router.get("/{record_id}")
def get_record_details(record_id: str):
    """Retrieve full input and output payload for a specific analysis record."""
    rec = get_analysis_record(record_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Analysis record '{record_id}' not found.")
    return rec
