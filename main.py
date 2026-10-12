#---------------------------------------------------------------------------------------------------
#
# La API solo acepta y consulta trabajos. El procesamiento se delega a workers externos.
#
#---------------------------------------------------------------------------------------------------
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum

from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field
from redis import asyncio as aioredis
from redis.exceptions import RedisError


REDIS_URL = "redis://localhost:6379"
QUEUE_NAME = "tasks_queue"
STATUS_PREFIX = "status:"
STATUS_TTL_SECONDS = 3600

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class TaskRequest(BaseModel):
    query: str = Field(min_length=1, examples=["Resume este texto"])


class TaskAcceptedResponse(BaseModel):
    job_id: str
    status: TaskStatus


class TaskStatusResponse(BaseModel):
    job_id: str
    status: TaskStatus
    result: str | None = None
    error: str | None = None


class TaskState(BaseModel):
    job_id: str
    status: TaskStatus
    query: str
    result: str | None = None
    error: str | None = None


class RedisTaskRepository:
    """Encapsula el acceso a Redis para la API y los workers."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def create_task(self, task: TaskState) -> None:
        async with self._redis.pipeline(transaction=True) as pipeline:
            pipeline.set(
                f"{STATUS_PREFIX}{task.job_id}",
                task.model_dump_json(),
                ex=STATUS_TTL_SECONDS,
            )
            pipeline.rpush(QUEUE_NAME, task.job_id)
            await pipeline.execute()

    async def get_task(self, job_id: str) -> TaskState | None:
        raw = await self._redis.get(f"{STATUS_PREFIX}{job_id}")
        return TaskState.model_validate_json(raw) if raw else None

    async def update_task(self, task: TaskState) -> None:
        await self._redis.set(
            f"{STATUS_PREFIX}{task.job_id}",
            task.model_dump_json(),
            ex=STATUS_TTL_SECONDS,
        )

    async def next_job_id(self) -> str | None:
        message = await self._redis.blpop(QUEUE_NAME, timeout=0)
        if message is None:
            return None

        _, job_id = message
        return job_id

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    redis_client = aioredis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_timeout=None,  # Evita timeouts en comandos bloqueantes como BLPOP
    )
    task_repository = RedisTaskRepository(redis_client)

    app.state.redis_client = redis_client
    app.state.task_repository = task_repository

    try:
        yield
    finally:
        await redis_client.aclose()


app = FastAPI(
    title="Async Task API",
    version="1.0.0",
    lifespan=lifespan,
)


def get_task_repository(request: Request) -> RedisTaskRepository:
    """Dependency Provider para inyectar RedisTaskRepository en los endpoints."""
    return request.app.state.task_repository


@app.post(
    "/process",
    response_model=TaskAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_task(
    request: TaskRequest,
    task_repository: RedisTaskRepository = Depends(get_task_repository),
) -> TaskAcceptedResponse:
    job_id = uuid.uuid4().hex
    task = TaskState(
        job_id=job_id,
        status=TaskStatus.PENDING,
        query=request.query,
    )

    try:
        await task_repository.create_task(task)
    except RedisError as exc:
        logger.exception("No se pudo encolar la tarea")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de tareas no está disponible.",
        ) from exc

    return TaskAcceptedResponse(job_id=job_id, status=task.status)


@app.get("/status/{job_id}", response_model=TaskStatusResponse)
async def get_status(
    job_id: str,
    task_repository: RedisTaskRepository = Depends(get_task_repository),
) -> TaskStatusResponse:
    try:
        task = await task_repository.get_task(job_id)
    except RedisError as exc:
        logger.exception("No se pudo consultar el estado del job")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de tareas no está disponible.",
        ) from exc

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job no encontrado o expirado.",
        )

    return TaskStatusResponse(
        job_id=task.job_id,
        status=task.status,
        result=task.result,
        error=task.error,
    )

@app.get("/health/workers", status_code=status.HTTP_200_OK)
async def check_workers_health(request: Request) -> dict[str, Any]:
    """Verifica si hay workers activos consultando sus heartbeats en Redis."""
    redis_client = request.app.state.redis_client
    
    try:
        # Buscamos todas las claves de latido activas
        cursor, keys = await redis_client.scan(match="worker:heartbeat:*", count=10)
        active_workers_count = len(keys)
        
        if active_workers_count == 0:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No hay workers activos en este momento.",
            )
            
        return {
            "status": "healthy",
            "active_workers": active_workers_count,
            "worker_ids": [key.split(":")[-1] for key in keys]
        }
    except RedisError as exc:
        logger.exception("Error al verificar la salud de los workers en Redis")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de Redis no disponible para verificación de salud.",
        ) from exc
        

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
    