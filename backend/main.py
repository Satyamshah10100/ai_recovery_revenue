import os
import json
from fastapi import FastAPI, BackgroundTasks, Header, Request
from supabase import create_client, Client
from dotenv import load_dotenv

# Import our bounded AI engine
from ai_engine import diagnose_failure, DiagnosisClass

load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Razorpay AI Recovery Layer")


def process_failed_payment(event_id: str, payload: dict):
    # For testing, we use the mock transaction ID we inserted into Supabase earlier.
    test_tx_id = "550e8400-e29b-41d4-a716-446655440000" 
    
    # Safely extract error details from the complex Razorpay payload
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    error_code = entity.get("error_code", "UNKNOWN")
    error_desc = entity.get("error_description", "No description provided")
    
    # --- GUARDRAIL 1: INGESTION IDEMPOTENCY ---
    try:
        event_response = supabase.table("failed_events").insert({
            "webhook_event_id": event_id,
            "transaction_id": test_tx_id,
            "error_code": error_code,
            "raw_payload": payload,
            "processing_status": "PROCESSING"
        }).execute()
        
        failed_event_db_id = event_response.data[0]['id']
        print(f"📥 New Webhook Stored: {event_id}")
        
    except Exception as e:
        # Supabase/PostgreSQL throws error 23505 on unique constraint violations
        if "23505" in str(e) or "duplicate key" in str(e):
            print(f" [Idempotency Lock] Duplicate webhook {event_id} rejected.")
            return
        print(f"Database error: {e}")
        return

    # --- GUARDRAIL 2: BOUNDED AI DIAGNOSIS ---
    print(f" Running AI Diagnosis on {error_code}...")
    diagnosis = diagnose_failure(error_code, error_desc, payload)
    print(f"   -> AI Result: {diagnosis.diagnosis_class.value} (Confidence: {diagnosis.confidence_score})")
    
    # --- GUARDRAIL 3: DETERMINISTIC POLICY ENGINE ---
    action = "MANUAL_REVIEW" # Safe default
    
    if diagnosis.diagnosis_class == DiagnosisClass.NETWORK_DROP and diagnosis.confidence_score > 0.80:
        action = "SMART_RETRY"
    elif diagnosis.diagnosis_class == DiagnosisClass.INSUFFICIENT_FUNDS:
        action = "SEND_PAYMENT_LINK"
        
    print(f" Deterministic Policy Decision: {action}")
        
    # --- GUARDRAIL 4: THE DOUBLE-CHARGE SAFETY LOCK ---
    try:
        supabase.table("recovery_attempts").insert({
            "transaction_id": test_tx_id,
            "failed_event_id": failed_event_db_id,
            "ai_diagnosis_class": diagnosis.diagnosis_class.value,
            "ai_confidence": float(diagnosis.confidence_score),
            "action_taken": action,
            "execution_status": "EXECUTED" if action != "MANUAL_REVIEW" else "PENDING_REVIEW"
        }).execute()
        
        print(f" Successfully locked and executed action: {action} for transaction {test_tx_id}\n")

        
    except Exception as e:
        if "23505" in str(e) or "duplicate key" in str(e):
            print(f"🛑 [Double-Charge Lock] Action {action} already taken for {test_tx_id}. Aborting execution.\n")
        else:
            print(f"Failed to acquire lock: {e}")

# ENDPOINTS 
@app.get("/")
def health_check():
    return {"status": "healthy"}

@app.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    try:
        body = await request.json()
        event_type = body.get("event")
        
        if event_type == "payment.failed":
            event_id = request.headers.get("x-razorpay-event-id", str(body.get("created_at", "test_id")))
            
            # Push heavy processing to the background
            background_tasks.add_task(process_failed_payment, event_id, body)
            
        return {"status": "ok"}
        
    except Exception as e:
        return {"status": "error", "message": "Failed to parse webhook"}
