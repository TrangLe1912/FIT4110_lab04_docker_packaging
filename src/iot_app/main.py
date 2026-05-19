import os
import time
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from pydantic import BaseModel, Field


SERVICE_NAME = os.getenv("SERVICE_NAME", "iot-ingestion")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")


app = FastAPI(
    title="FIT4110 Lab 04 - IoT Ingestion Service",
    version="0.1.0",
    description="Minimal IoT Ingestion API used to verify Docker packaging with Postman/Newman.",
)


class SensorReadingIn(BaseModel):
    device_id: str = Field(..., min_length=1, examples=["ESP32_01"])
    temperature: float = Field(..., ge=-40, le=85, examples=[38.5])
    humidity: Optional[float] = Field(default=None, ge=0, le=100, examples=[65.0])
    motion: Optional[bool] = Field(default=None, examples=[False])
    timestamp: str = Field(..., examples=["2026-05-18T10:30:00Z"])


class SensorReadingOut(BaseModel):
    readingId: str
    status: str
    device_id: str
    acceptedAt: int


READINGS: List[Dict] = []


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "about:blank",
                "title": "Unauthorized",
                "status": 401,
                "detail": "Missing Authorization header",
            },
        )

    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "about:blank",
                "title": "Unauthorized",
                "status": 401,
                "detail": "Invalid bearer token",
            },
        )


@app.get("/health")
def health() -> Dict[str, str]:
    return {
        "status": "ok",
        "service": SERVICE_NAME,
    }


@app.post(
    "/readings",
    response_model=SensorReadingOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
)
def create_reading(payload: SensorReadingIn, response: Response) -> SensorReadingOut:
    if payload.temperature >= 70:
        response.headers["X-Warning"] = "high-temperature"

    reading_id = f"reading_{len(READINGS) + 1:03d}"
    accepted_at = int(time.time())

    item = {
        "readingId": reading_id,
        "status": "accepted",
        "device_id": payload.device_id,
        "acceptedAt": accepted_at,
        "payload": payload.model_dump(),
    }
    READINGS.append(item)

    return SensorReadingOut(
        readingId=reading_id,
        status="accepted",
        device_id=payload.device_id,
        acceptedAt=accepted_at,
    )


@app.get("/readings/latest", dependencies=[Depends(verify_bearer_token)])
def latest_reading() -> Dict:
    if not READINGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "about:blank",
                "title": "Not Found",
                "status": 404,
                "detail": "No readings have been submitted yet",
            },
        )

    return READINGS[-1]


@app.get("/readings/{reading_id}", dependencies=[Depends(verify_bearer_token)])
def get_reading(reading_id: str) -> Dict:
    for item in READINGS:
        if item["readingId"] == reading_id:
            return item

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "type": "about:blank",
            "title": "Not Found",
            "status": 404,
            "detail": f"Reading {reading_id} does not exist",
        },
    )
