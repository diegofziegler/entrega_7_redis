import asyncio
import logging
from enum import StrEnum
from typing import TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from redis import asyncio as aioredis
from redis.exceptions import RedisError

from main import REDIS_URL, QUEUE_NAME, STATUS_PREFIX, TaskStatus, TaskState, RedisTaskRepository

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class GraphState(TypedDict):
    query: str
    result: str


async def sample_node(state: GraphState) -> GraphState:
    """Nodo de ejemplo que simula procesamiento dentro de LangGraph."""
    await asyncio.sleep(2.0)
    return {"result": f"Resultado procesado por LangGraph para: {state['query']}"}


def build_task_graph():
    """Construye y compila el grafo de LangGraph."""
    workflow = StateGraph(GraphState)
    workflow.add_node("process_node", sample_node)
    workflow.set_entry_point("process_node")
    workflow.add_edge("process_node", END)
    return workflow.compile()


async def process_task(graph: StateGraph, task: TaskState) -> str:
    """Invoca el grafo de LangGraph de manera asíncrona usando ainvoke."""
    initial_state: GraphState = {"query": task.query, "result": ""}
    output_state = await graph.ainvoke(initial_state)
    return output_state["result"]


async def task_worker(repository: RedisTaskRepository, graph: StateGraph) -> None:
    logger.info("Worker independiente iniciado...")

    while True:
        try:
            job_id = await repository.next_job_id()
            if job_id is None:
                continue

            task = await repository.get_task(job_id)
            if task is None:
                logger.warning("Job %s no encontrado; se descarta", job_id)
                continue

            task.status = TaskStatus.PROCESSING
            await repository.update_task(task)

            try:
                result = await process_task(graph, task)
                task.status = TaskStatus.COMPLETED
                task.result = result
            except Exception as exc:
                logger.exception("Error procesando job %s", job_id)
                task.status = TaskStatus.ERROR
                task.error = str(exc)

            await repository.update_task(task)

        except asyncio.CancelledError:
            logger.info("Worker detenido.")
            raise
        except RedisError:
            logger.exception("Error de Redis en el worker")
            await asyncio.sleep(1)

async def heartbeat_loop(redis_client: aioredis.Redis, worker_id: str, interval: int = 10, ttl: int = 25) -> None:
    """Envía un latido periódico a Redis para indicar que el worker está activo."""
    heartbeat_key = f"worker:heartbeat:{worker_id}"
    logger.info("Heartbeat iniciado para el worker %s", worker_id)
    
    try:
        while True:
            # Actualiza la clave con un TTL; si el worker muere, la clave expira sola
            await redis_client.set(heartbeat_key, "alive", ex=ttl)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        # Limpieza al apagar el worker ordenadamente
        await redis_client.delete(heartbeat_key)
        logger.info("Heartbeat detenido para el worker %s", worker_id)
        raise

async def main() -> None:
    worker_id = uuid.uuid4().hex[:8]
    redis_client = aioredis.from_url(
        REDIS_URL, 
        decode_responses=True,
        socket_timeout=None,
    )
    repository = RedisTaskRepository(redis_client)
    graph = build_task_graph()

    # Lanzamos el worker y el heartbeat en paralelo
    worker_task = asyncio.create_task(task_worker(repository, graph))
    hb_task = asyncio.create_task(heartbeat_loop(redis_client, worker_id))

    try:
        await asyncio.gather(worker_task, hb_task)
    except asyncio.CancelledError:
        pass
    finally:
        await redis_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker detenido manualmente.")
        