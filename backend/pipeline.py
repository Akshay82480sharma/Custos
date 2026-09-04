"""Runs the full OS pipeline across all 4 capabilities."""
import subprocess
import sys
import os
from typing import Callable, Optional

SCRIPTS = [
    ("backend/ingestion.py", "Ingestion"),
    ("backend/sync_razorpay.py", "Sync Razorpay"),
    ("backend/capabilities/risk.py", "Risk Analysis"),
    ("backend/capabilities/growth.py", "Growth Analysis"),
    ("backend/capabilities/recovery_workflow.py", "Recovery Workflow"),
    ("backend/capabilities/finance.py", "Finance Analysis"),
]

def run_pipeline(progress_callback: Optional[Callable] = None):
    """Run the full pipeline with optional progress callback.
    
    Args:
        progress_callback: Optional callback function(progress: int, stage: str, message: str)
                         Called with progress percentage (0-100), stage name, and message.
    """
    root = os.path.dirname(os.path.dirname(__file__))
    total = len(SCRIPTS)
    
    for i, (script, stage_name) in enumerate(SCRIPTS):
        progress = int((i / total) * 100)
        if progress_callback:
            progress_callback(progress, stage_name, f"Running {stage_name}...")
        
        path = os.path.join(root, script)
        result = subprocess.run([sys.executable, path], cwd=root, capture_output=True, text=True)
        
        if result.returncode != 0:
            if progress_callback:
                progress_callback(progress, f"{stage_name} (Failed)", f"Error: {result.stderr[:200]}")
            return {"ok": False, "failed_at": script, "error": result.stderr}
    
    if progress_callback:
        progress_callback(100, "Complete", "All stages completed successfully")
    
    return {"ok": True}

if __name__ == "__main__":
    print(run_pipeline())
