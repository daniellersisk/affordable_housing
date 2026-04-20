from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Housing Units API")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
