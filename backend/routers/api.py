"""Operational HTTP API; presentation belongs in templates."""
import threading
import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from backend.pipeline import run_pipeline
from backend.services.dashboard import event_detail, overview

router = APIRouter()
_scan_lock = threading.Lock()
_last_scan_result = {"ok": False, "error": "No scan run yet"}

@router.get("/health")
def health() -> dict[str, str]: return {"status": "ok", "mode": "production"}

@router.post("/scan")
def scan_now():
    if not _scan_lock.acquire(blocking=False): return JSONResponse({"status": "already_running"}, status_code=409)
    try: return run_pipeline()
    finally: _scan_lock.release()

@router.get("/scan/stream")
def scan_stream():
    """SSE endpoint for real-time scan progress updates."""
    def generate():
        global _last_scan_result
        
        if not _scan_lock.acquire(blocking=False):
            yield f"data: {json.dumps({'status': 'already_running'})}\n\n"
            return
        
        try:
            yield f"data: {json.dumps({'status': 'starting', 'progress': 0, 'message': 'Initializing scan...'})}\n\n"
            
            def progress_callback(progress, stage, message):
                nonlocal generate
                yield f"data: {json.dumps({'status': 'running', 'progress': progress, 'stage': stage, 'message': message})}\n\n"
            
            result = run_pipeline(progress_callback=progress_callback)
            _last_scan_result = result
            yield f"data: {json.dumps(result)}\n\n"
        finally:
            _scan_lock.release()
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@router.get("/scan/status")
def scan_status():
    """Get last scan result for error recovery."""
    return _last_scan_result

@router.get("/overview")
def overview_data(): return overview()

@router.get("/events/{event_id}")
def event_data(event_id: str):
    detail = event_detail(event_id)
    return detail if detail else JSONResponse({"detail": "Event not found"}, status_code=404)
