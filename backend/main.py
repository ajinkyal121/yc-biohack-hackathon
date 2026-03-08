import asyncio
import uuid
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from models import PipelineEvent, ScientistInput
import json
import base64

app = FastAPI(title="YC Biohack Hackathon")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for pipeline run queues
run_queues: dict[str, asyncio.Queue] = {}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/run")
async def start_pipeline(
    text: str = Form(...),
    files: list[UploadFile] = File(None),
):
    run_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    run_queues[run_id] = queue

    # Process uploaded files
    file_data = []
    if files:
        for f in files:
            if f.filename:
                content = await f.read()
                media_type = f.content_type or "application/octet-stream"
                file_data.append({
                    "filename": f.filename,
                    "content_base64": base64.b64encode(content).decode(),
                    "media_type": media_type,
                })

    scientist_input = ScientistInput(text=text, files=file_data)

    # Import here to avoid circular imports
    from pipeline import run_pipeline

    asyncio.create_task(run_pipeline(scientist_input, queue, run_id))

    return {"run_id": run_id}


@app.get("/api/stream/{run_id}")
async def stream_events(run_id: str):
    queue = run_queues.get(run_id)
    if not queue:
        return {"error": "Run not found"}

    async def event_generator():
        while True:
            event: PipelineEvent = await queue.get()
            yield {"data": event.model_dump_json()}
            if event.status in ("done", "error") and event.step == "final":
                # Clean up
                run_queues.pop(run_id, None)
                break

    return EventSourceResponse(event_generator())
