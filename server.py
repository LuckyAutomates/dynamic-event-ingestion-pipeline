import asyncio
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, StrictStr

from playwright_engine import save_quotes

logger = logging.getLogger(__name__)

app = FastAPI()


class QuoteRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: StrictStr
    author: StrictStr


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    quotes: list[QuoteRecord]


@app.post("/ingest")
async def ingest(payload: IngestRequest) -> dict[str, int]:
    records = [
        {
            "quote_text": quote.text,
            "author": quote.author,
            "page_number": None,
        }
        for quote in payload.quotes
    ]

    try:
        await asyncio.to_thread(save_quotes, records)
    except Exception as exc:
        logger.exception("Quote ingestion failed.")
        raise HTTPException(
            status_code=503,
            detail="Quote ingestion is temporarily unavailable.",
        ) from exc

    return {"inserted": len(records)}
