from fastapi import FastAPI

app = FastAPI(title="CoachOS Media Service")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "media"}
