from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import auth, maintenance, vehicles

app = FastAPI(title="Vehicle Maintenance Index", description="A simple place to track your vehicles and their maintenance.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(maintenance.router)


@app.get("/health")
def health():
    return {"status": "ok"}
