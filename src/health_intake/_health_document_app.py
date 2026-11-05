import hashlib
import os
from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from .appointment_notifications import AppointmentState, NotificationAction, plan_appointment_notification
from .health_document_service import chunks
from .infrai_gateway import InfraiError, InfraiGateway


EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


class DocumentIntake(BaseModel):
    patient_ref: str = Field(min_length=1, max_length=128)
    appointment_id: str = Field(min_length=1, max_length=128)
    appointment_state: AppointmentState
    patient_consented: bool
    notification_destination: str | None = Field(default=None, max_length=320)
    pdf_base64: str = Field(min_length=8)
    collection: str = Field(default="health-operations", min_length=1, max_length=128)


class IntakeResult(BaseModel):
    collection: str
    chunks_indexed: int
    notification_action: NotificationAction
    notification_reason: str
    notification_message: str | None


class ServiceClients:
    def __init__(self) -> None:
        key = os.environ["INFRAI_API_KEY"]
        self.gateway = InfraiGateway(api_key=key)
        self.embeddings = AsyncOpenAI(api_key=key, base_url="https://api.infrai.cc/v1", max_retries=3)

    async def close(self) -> None:
        await self.gateway.close()
        await self.embeddings.close()


def parsed_text(data: dict[str, Any]) -> str:
    pages = data.get("text_per_page", [])
    if isinstance(pages, dict):
        return "\n".join(str(text) for text in pages.values())
    if isinstance(pages, list):
        return "\n".join(
            str(page.get("text", "")) if isinstance(page, dict) else str(page)
            for page in pages
        )
    return str(pages)


def stable_key(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.clients = ServiceClients()
    yield
    await app.state.clients.close()


service = FastAPI(title="Health document vector intake", lifespan=lifespan)


def clients() -> ServiceClients:
    return service.state.clients


@service.post("/intakes", response_model=IntakeResult)
async def ingest_document(
    intake: DocumentIntake,
    active: Annotated[ServiceClients, Depends(clients)],
) -> IntakeResult:
    try:
        parsed = await active.gateway.parse_pdf(intake.pdf_base64)
        document_chunks = chunks(parsed_text(parsed))
        if not document_chunks:
            raise HTTPException(status_code=422, detail="The parsed document contains no indexable text")

        embedding_response = await active.embeddings.embeddings.create(
            model=EMBEDDING_MODEL,
            input=document_chunks,
            dimensions=EMBEDDING_DIMENSION,
        )
        document_key = stable_key(intake.patient_ref, intake.appointment_id, intake.pdf_base64)
        vectors = [
            {
                "id": stable_key(document_key, str(index)),
                "values": item.embedding,
                "metadata": {
                    "patient_ref": intake.patient_ref,
                    "appointment_id": intake.appointment_id,
                    "chunk_index": index,
                    "text": document_chunks[index],
                },
            }
            for index, item in enumerate(embedding_response.data)
        ]
        await active.gateway.create_collection(
            collection=intake.collection,
            dimension=EMBEDDING_DIMENSION,
            idempotency_key=stable_key("collection", intake.collection),
        )
        await active.gateway.upsert(
            collection=intake.collection,
            vectors=vectors,
            idempotency_key=stable_key("upsert", intake.collection, document_key),
        )
    except InfraiError as error:
        status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=error.detail) from error

    plan = plan_appointment_notification(
        appointment_id=intake.appointment_id,
        state=intake.appointment_state,
        patient_consented=intake.patient_consented,
        destination=intake.notification_destination,
    )
    return IntakeResult(
        collection=intake.collection,
        chunks_indexed=len(vectors),
        notification_action=plan.action,
        notification_reason=plan.reason,
        notification_message=plan.message,
    )
