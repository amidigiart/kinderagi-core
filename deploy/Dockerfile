FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn pydantic numpy cryptography \
    && pip install --no-cache-dir "ukbe-core @ git+https://github.com/amidigiart/ukbe-core@main"

COPY app.py safety_pipeline.py demo_brain.py resonance_motor.py ./
COPY static/ static/

ENV KINDERAGI_ENV=prod \
    OLLAMA_URL=http://ollama:11434 \
    KINDERAGI_MODEL=gemma3:4b

EXPOSE 8123
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8123"]
