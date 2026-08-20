import os
import logging
import uuid
from typing import Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from python_llm import LLMProviderFactory, BaseLLMProvider, GenerateRequest, GenerateResponse, ChatMessage
from python_llm.config import load_llm_config

from src.models import ChatInitRequest, ChatMessageRequest

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("generation")

# Global state
llm_provider: BaseLLMProvider = None
chat_sessions: Dict[str, dict] = {}

class StatusResponse(BaseModel):
    service: str
    status: str
    provider: str = ""
    model: str = ""

@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_provider

    logger.info("Starting Generation Pipeline")

    llm_config = load_llm_config()
    llm_provider = LLMProviderFactory.create(
        llm_config.provider, llm_config.to_provider_config()
    )
    logger.info(f"Initialized LLM provider: {llm_config.provider}")

    yield

    logger.info("Shutting down Generation Pipeline")

app = FastAPI(
    title="Generation Pipeline",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status", response_model=StatusResponse)
async def status():
    return StatusResponse(
        service="generation-pipeline",
        status="ok" if llm_provider else "uninitialized",
        provider=llm_provider.provider_name if llm_provider else "",
        model=llm_provider.model if llm_provider else ""
    )

@app.get("/health")
async def health():
    return {
        "status": "healthy" if llm_provider else "unhealthy",
        "service": "generation-pipeline"
    }

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    if not llm_provider:
        raise HTTPException(status_code=503, detail="LLM provider not initialized")

    try:
        response = await llm_provider.generate(request)
        return response
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate/stream")
async def generate_stream(request: GenerateRequest):
    if not llm_provider:
        raise HTTPException(status_code=503, detail="LLM provider not initialized")

    async def stream_generator():
        try:
            async for chunk in llm_provider.generate_stream(request):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield f"data: [ERROR] {str(e)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream"
    )

@app.post("/chat/init")
async def chat_init(request: ChatInitRequest):
    chat_id = str(uuid.uuid4())

    chat_sessions[chat_id] = {
        "document_id": request.document_id,
        "document_title": request.document_title,
        "document_content": request.document_content,
        "history": []
    }

    system_message = f"You are a helpful assistant analyzing the document: {request.document_title or 'Unknown'}"
    if request.document_content:
        system_message += f"\n\nDocument content:\n{request.document_content[:2000]}"

    chat_sessions[chat_id]["history"].append(
        ChatMessage(role="system", content=system_message)
    )

    return {"chat_id": chat_id, "status": "initialized"}

@app.post("/chat/message")
async def chat_message(request: ChatMessageRequest):
    if not llm_provider:
        raise HTTPException(status_code=503, detail="LLM provider not initialized")

    if request.chat_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session = chat_sessions[request.chat_id]
    session["history"].append(ChatMessage(role="user", content=request.message))

    try:
        response = await llm_provider.chat(session["history"])
        session["history"].append(ChatMessage(role="assistant", content=response))

        return {
            "chat_id": request.chat_id,
            "message": response,
            "role": "assistant"
        }
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/message/stream")
async def chat_message_stream(request: ChatMessageRequest):
    if not llm_provider:
        raise HTTPException(status_code=503, detail="LLM provider not initialized")

    if request.chat_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session = chat_sessions[request.chat_id]
    session["history"].append(ChatMessage(role="user", content=request.message))

    async def stream_generator():
        try:
            full_response = ""
            async for chunk in llm_provider.generate_stream(
                GenerateRequest(
                    question=request.message,
                    context="\n".join([m.content for m in session["history"] if m.role == "system"])
                )
            ):
                full_response += chunk
                yield f"data: {chunk}\n\n"

            session["history"].append(ChatMessage(role="assistant", content=full_response))
        except Exception as e:
            logger.error(f"Chat stream error: {str(e)}")
            yield f"data: [ERROR] {str(e)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)
