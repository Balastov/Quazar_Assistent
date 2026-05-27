import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "apps" / "api"))

from config import get_settings
from routers import audit, auth, chats, confluence, documents, llm, oidc, projects

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Quazar Assistent API",
    description="Corporate AI assistant with RAG, multi-LLM, and Confluence integration",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(oidc.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(chats.router)
app.include_router(confluence.router)
app.include_router(llm.router)
app.include_router(audit.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "quazar-api"}


@app.get("/")
async def root():
    return {"message": "Quazar Assistent API", "docs": "/docs"}
