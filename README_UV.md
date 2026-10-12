# Instruccciones

Con `uv`, crea el proyecto, agrega las dependencias y ejecuta la app con `uv run`. `uv run` crea/usa automáticamente el entorno virtual, resuelve e instala dependencias y genera `uv.lock`.[[docs.astral](https://docs.astral.sh/uv/guides/integration/fastapi/)]

## 1. Crear el proyecto

```
mkdir async-task-api
cd async-task-api

uv init --no-package --python 3.12
```

Copia el código anterior en un archivo llamado `main.py`.

## 2. Agregar dependencias

```
uv add "fastapi[standard]" redis
```

El extra `standard` de FastAPI incluye `uvicorn` y utilidades habituales de desarrollo, como recarga automática.[[docs.astral](https://docs.astral.sh/uv/guides/integration/fastapi/)][[pydevtools](https://pydevtools.com/handbook/tutorial/set-up-a-fastapi-project-with-uv/)]

Tu `pyproject.toml` debería quedar aproximadamente así:

```
[project]
name = "async-task-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.115.0",
    "redis>=5.0.0",
]
```

## 3. Levantar Redis

Con Docker:

```
docker run --rm -d \
--name redis-task-api \
-p 6379:6379 \
redis:7-alpine
```

O, si ya tenés Redis instalado localmente:

```
redis-server
```

## 4. Ejecutar la API

Desde la carpeta del proyecto:

```
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

También podés usar el comando recomendado por FastAPI:

```
uv run fastapi dev
```

`uv run fastapi dev` ejecuta la aplicación en modo desarrollo con recargaautomática.[[docs.astral](https://docs.astral.sh/uv/guides/integration/fastapi/)][[fastapi.tiangolo](https://fastapi.tiangolo.com/tutorial/first-steps/)]

## 5. Probarlo

Abrí la documentación interactiva:

```
http://localhost:8000/docs
```

O desde terminal:

```
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"query": "Analizar este texto"}'
```

Respuesta esperada:

```
{
"job_id": "a1b2c3...",
"status": "pending"
}
```

Consultá el estado:

```
curl http://localhost:8000/status/<job_id>
```

Después de unos 3 segundos debería devolver:

```
{
"job_id": "a1b2c3...",
"status": "completed",
"result": "Resultado procesado para: Analizar este texto",
"error": null
}
```

## Comandos útiles

```
# Ejecutar sin recarga automática
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# Ejecutar con más workers
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Sincronizar dependencias desde pyproject.toml / uv.lock
uv sync

# Agregar una dependencia futura
uv add <paquete>
```

Para despliegue, `uvicorn` admite `--workers`; en tu ejemplo actual el worker corre dentro del mismo proceso de uvicorn, así que con varios workers tendrías varios consumidores de la cola. Eso es válido, pero para producción es más limpio separar API y worker en procesos/contenedores distintos.[[uvicorn](https://uvicorn.dev/settings/)][[uvicorn](https://uvicorn.dev/deployment/)]

 
