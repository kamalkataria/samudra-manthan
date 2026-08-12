from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

app = FastAPI(title="Samudra Manthan API", version="1.0.0")

# --- Security & Authorization Gate ---
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
MASTER_SECRET_HEADER = APIKeyHeader(name="X-Master-Secret", auto_error=False)

# Replace with your actual secure internal master secret or load from environment variables
MASTER_SECRET = "samudra_master_secret_internal_app_123"

def verify_paid_api_key(api_key: str) -> bool:
    # Placeholder for third-party paid key validation (e.g., check against a DB)
    active_paid_keys = ["sm_live_thirdparty_demo_key"]
    return api_key in active_paid_keys

async def verify_api_access(
    x_api_key: Optional[str] = Security(API_KEY_HEADER),
    x_master_secret: Optional[str] = Security(MASTER_SECRET_HEADER)
):
    if x_master_secret == MASTER_SECRET:
        return {"tier": "owner"}
    if x_api_key and verify_paid_api_key(x_api_key):
        return {"tier": "paid_developer"}
    
    raise HTTPException(
        status_code=402, 
        detail="Payment Required. A valid API key or master secret is required."
    )

# --- Pydantic Request Models ---
class GmailPayload(BaseModel):
    token_info: Dict[str, Any]
    client_secrets_info: Optional[Dict[str, Any]] = None

class ScanRequest(BaseModel):
    auth: GmailPayload

# --- API Endpoints ---
@app.get("/")
def health_check():
    return {"status": "online", "service": "Samudra Manthan API"}

@app.post("/api/scan")
def trigger_scan(payload: ScanRequest, access: dict = Security(verify_api_access)):
    """
    Endpoint to trigger a mailbox scan using client-provided credentials in-memory.
    """
    try:
        # We will hook this up to your core scanning logic next!
        return {
            "status": "success", 
            "message": "Scan initiated with in-memory credentials.",
            "tier_used": access["tier"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
