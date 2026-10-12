# Ejercicioo 7, 2
La API solo acepta y consulta trabajos; el worker consume la cola con `BLPOP`, actualiza estados y maneja errores sin bloquear el event loop. `BLPOP` con `timeout=0` espera indefinidamente hasta que haya un elemento, evitando polling activo.[[redis.readthedocs](https://redis.readthedocs.io/en/stable/commands.html)][[redis](https://redis.io/blog/beyond-the-cache-with-python/)]

## Cómo cubre la consigna


| Criterio              | Implementación                                                                                                                |
|-----------------------|--------------------------------------------------------------------------------------------------------------------------------|
| Desacoplamiento       | `RedisTaskRepository` aísla Redis; los endpoints no conocen `RPUSH`, `BLPOP` ni el formato interno del estado.                |
| Estados y polling     | `TaskStatus` modela `pending`, `processing`, `completed` y `error`; `/status/{job_id}` consulta el estado persistido en Redis. |
| Worker y concurrencia | El worker consume con `BLPOP`, marca `processing`, ejecuta una corrutina y persiste `completed` o `error`.                     |
| Calidad y tipado      | Pydantic valida entrada y serializa estado; se usan `StrEnum`, uniones modernas `X                                             | None`, `asynccontextmanager` y `lifespan`. |


## Puntos importantes

- Usé `RPUSH` + `BLPOP` para implementar una cola FIFO: los trabajos se agregan al final y se consumen desde el frente.[[redis](https://redis.io/blog/beyond-the-cache-with-python/)]
- El estado se guarda como JSON en una clave `status:<job_id>` con TTL, de modo que los resultados no permanezcan indefinidamente en Redis.
- Reemplacé el arranque manual con `loop.create_task()` por el `lifespan` de FastAPI, que es el mecanismo recomendado para iniciar y detener recursos y tareas de fondo.[[fastapi.tiangolo](https://fastapi.tiangolo.com/advanced/events/)]
- En producción, conviene ejecutar el worker como un proceso independiente (`python worker.py` o un deployment separado), no dentro de uvicorn; así puedes escalar API y workers por separado. FastAPI documenta que las colas como Redis permiten ejecutar tareas en múltiples procesos o servidores.[[fastapi.tiangolo](https://fastapi.tiangolo.com/tutorial/background-tasks/)]

Guarda el archivo como `main.py` y ejecútalo con:

```
uvicorn main:app --host 0.0.0.0 --port 8000
```

Luego:

```
curl -X POST http://localhost:8000/process \      
-H "Content-Type: application/json" \      
-d '{"query": "Analizar este texto"}'      

curl http://localhost:8000/status/<job_id>
```

---

# Procesos separados

Ahora quedaron en procesos separados. El ejemplo corre de esta forma:

Levantar el API de esta forma:

```
uv run uvicorn main:app --reload --port 8000
```

Disparar el cliente de esta forma:

```
uv run python worker.py
```

## ¿Como testear?

1. levantar docker:

```
docker run --rm -d --name redis-task-api -p 6379:6379 redis:7-alpine
```

1. levantar api:

```
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload  
```

1. primera prueba

```
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/process" -ContentType "application/json" -Body '{"query": "Analizar este texto"}'
```

... esta es la respuesta:

```
job_id                           status  
------                           ------  
dc9c3a6d5f0e442299f007b093b11c6b pending
```

... tomar el `job_id` de la respuesta anterior:

```
Invoke-RestMethod -Uri "http://localhost:8000/status/dc9c3a6d5f0e442299f007b093b11c6b"
```

... y te va a responder con algo de esta forma:

```
job_id                           status    result                                        error  
------                           ------    ------                                        -----  
dc9c3a6d5f0e442299f007b093b11c6b completed Resultado procesado para: Analizar este texto
```

---


# ¿Por qué es efectivo este enfoque en producción?

*Escalabilidad horizontal:* Como cada worker genera su propio worker_id único al iniciar, si levantas 3 instancias de python worker.py, verás 3 latidos independientes en Redis.

*Autolimpieza por TTL:* Si un servidor donde corre el worker se apaga de golpe (corte de luz, OOM Killer), la clave en Redis expirará automáticamente tras los segundos configurados en ttl, evitando falsos positivos de "workers fantasma".

*Integración con Kubernetes / Load Balancers:* El endpoint /health/workers puede ser consumido por sondas de disponibilidad (liveness/readiness probes) o herramientas de monitoreo como Prometheus/Datadog.

 
---
