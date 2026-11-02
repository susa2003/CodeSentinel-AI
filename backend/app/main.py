import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.db.database import engine, Base
import app.models.entities  # Ensure models are loaded for table registration
from app.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("codesentinel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing CodeSentinel AI database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down CodeSentinel AI backend.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-Style AI Code Review, Bug Detection and Software Quality Analysis Platform",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Safe Exception Handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {str(exc)}", exc_info=settings.DEBUG)
    # Safe error response without raw internal trace in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred while processing the request. Details logged safely.",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "The submitted payload failed validation constraints.",
            "details": exc.errors()
        }
    )


@app.get("/health", tags=["system"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/", tags=["system"])
def root_info():
    return {
        "platform": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "documentation": "/docs",
        "api_v1": settings.API_V1_STR
    }


# Include V1 API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
