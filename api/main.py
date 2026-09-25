import os
import sys

# Ensure project root is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import ai, kpis, transactions, anomalies, customers, metadata

app = FastAPI(
    title="FinSight AI Analytics API",
    description="REST API for FinSight AI providing analytical views on transaction data",
    version="1.0.0"
)

# Allow CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(kpis.router)
app.include_router(transactions.router)
app.include_router(anomalies.router)
app.include_router(customers.router)
app.include_router(metadata.router)
app.include_router(ai.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "FinSight AI API is running"}
