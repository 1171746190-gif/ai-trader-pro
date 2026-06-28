"""Research export API routes."""
from __future__ import annotations

import csv
import json
import logging
import os
from datetime import datetime, timezone
from io import StringIO
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse

from permissions import is_admin

logger = logging.getLogger(__name__)

# Sensitive key parts to filter from exports
SENSITIVE_KEY_PARTS = (
    "password", "secret", "token", "api_key", "private",
    "wallet", "seed", "mnemonic", "credential",
)


def _filter_sensitive(data: dict) -> dict:
    """Remove sensitive fields from data."""
    return {
        k: v for k, v in data.items()
        if not any(s in k.lower() for s in SENSITIVE_KEY_PARTS)
    }


def register_routes(app: FastAPI):
    """Register research export routes."""
    
    @app.get("/api/research/agents")
    async def export_agents(
        format: str = "csv",
        authorization: Optional[str] = Header(None),
    ):
        """Export agent data for research."""
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents LIMIT 10000")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Filter sensitive data
        filtered = [_filter_sensitive(row) for row in rows]
        
        if format == "json":
            return filtered
        
        # CSV format
        if not filtered:
            return PlainTextResponse("")
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=filtered[0].keys())
        writer.writeheader()
        writer.writerows(filtered)
        
        return PlainTextResponse(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=agents.csv"},
        )
    
    @app.get("/api/research/signals")
    async def export_signals(
        format: str = "csv",
        limit: int = Query(10000, le=50000),
        authorization: Optional[str] = Header(None),
    ):
        """Export signal data for research."""
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signals ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        filtered = [_filter_sensitive(row) for row in rows]
        
        if format == "json":
            return filtered
        
        if not filtered:
            return PlainTextResponse("")
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=filtered[0].keys())
        writer.writeheader()
        writer.writerows(filtered)
        
        return PlainTextResponse(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=signals.csv"},
        )
    
    @app.get("/api/research/events")
    async def export_events(
        format: str = "csv",
        experiment_key: Optional[str] = None,
        authorization: Optional[str] = Header(None),
    ):
        """Export experiment events."""
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if experiment_key:
            cursor.execute(
                "SELECT * FROM experiment_events WHERE experiment_key = ? ORDER BY created_at DESC LIMIT 10000",
                (experiment_key,)
            )
        else:
            cursor.execute("SELECT * FROM experiment_events ORDER BY created_at DESC LIMIT 10000")
        
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        filtered = [_filter_sensitive(row) for row in rows]
        
        if format == "json":
            return filtered
        
        if not filtered:
            return PlainTextResponse("")
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=filtered[0].keys())
        writer.writeheader()
        writer.writerows(filtered)
        
        return PlainTextResponse(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=events.csv"},
        )
    
    @app.get("/api/research/schema")
    async def get_schema():
        """Get database schema for research."""
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [{"name": row[1], "type": row[2]} for row in cursor.fetchall()]
            schema[table] = columns
        
        conn.close()
        return schema
