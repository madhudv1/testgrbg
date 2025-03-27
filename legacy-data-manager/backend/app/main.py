from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.endpoints import drive, chat
from .core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Document and Data Management Platform",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware with more permissive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"]  # Exposes all headers
)

# Include routers
app.include_router(drive.router, prefix=f"{settings.API_V1_STR}/drive", tags=["drive"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])

@app.get("/")
async def root():
    return {"message": "Welcome to Legacy Data Manager API"} 