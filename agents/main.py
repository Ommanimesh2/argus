"""
ARGUS Agents — entrypoint. Runs FastAPI server (audit start, stream, report).
Usage (from repo root): python -m agents.main
"""
from .config import HOST, PORT, LOG_LEVEL
from .server import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level=LOG_LEVEL,
        workers=1,
    )
