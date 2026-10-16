# Imagen del backend de RepuSense.
#
#   docker build -t repusense-backend ./backend
#   docker run --rm -p 8000:8000 --env-file backend/.env repusense-backend
#
# Para el desarrollo local NO hace falta: usá `pnpm dev:backend`.
# Esta imagen es para llevar el backend a otro entorno.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# uv aparte de la app: si solo cambia el codigo, la capa de dependencias
# queda cacheada y la imagen tarda milisegundos en reconstruirse.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Capa de dependencias: solo se invalida si cambia pyproject.toml o uv.lock
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

EXPOSE 8000

# --no-sync: las dependencias ya estan en la imagen, no hay que resolverlas
# de nuevo en cada arranque.
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
