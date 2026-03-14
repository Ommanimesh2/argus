"""
ARGUS Agents — entrypoint. Runs FastAPI server (audit start, stream, report).
Usage (from repo root): python -m agents.main
"""
from .config import HOST, PORT, UVICORN_LOG_LEVEL
from .server import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level=UVICORN_LOG_LEVEL,
        workers=1,
    )
