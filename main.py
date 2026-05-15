import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "artifacts", "crm-optimizer"))

from main import app  # noqa: F401  — re-export for uvicorn

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
