import sys
import os

# Add the root directory to sys.path so we can import backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.pipeline import run_pipeline

if __name__ == "__main__":
    print("Starting Custos Autonomous Pipeline...")
    result = run_pipeline()
    if result.get("ok"):
        print("\nPipeline complete. Refresh the dashboard at http://127.0.0.1:8000")
    else:
        print(f"\nPipeline failed at {result.get('failed_at')}: {result.get('error')}")
        sys.exit(1)
