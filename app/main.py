from fastapi import FastAPI
from app.api.routes import router as graph_router
from app.core.registry import registry
# Import examples to ensure tools are registered
import app.examples.code_review 

app = FastAPI(title="Minimal Workflow Engine", version="1.0.0")

app.include_router(graph_router, prefix="/graph", tags=["Graph"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Workflow Engine. Use /docs for API documentation."}

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    from app.api.routes import get_storage
    storage = get_storage()
    # Check if it has init_db method (Duck typing or specific check)
    if hasattr(storage, "init_db"):
        await storage.init_db()

@app.get("/tools")
def list_tools():
    """List available tools in the registry."""
    return registry.list_tools()
