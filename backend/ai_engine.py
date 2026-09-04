import os
import google.generativeai as genai
from pydantic import BaseModel
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

# Configure the Gemini SDK
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class DiagnosisClass(str, Enum):
    NETWORK_DROP = "NETWORK_DROP"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    SUSPECTED_FRAUD = "SUSPECTED_FRAUD"
    INVALID_CARD_DETAILS = "INVALID_CARD_DETAILS"
    REQUIRES_HUMAN = "REQUIRES_HUMAN"

# Define the exact JSON shape the LLM must return
class PaymentDiagnosis(BaseModel):
    diagnosis_class: DiagnosisClass
    confidence_score: float
    reasoning: str  # We keep this for the audit logs on the frontend

def diagnose_failure(error_code: str, error_description: str, metadata: dict) -> PaymentDiagnosis:
    """
    Takes raw payment failure signals and returns a deterministic diagnosis classification.
    """
    # We use gemini-1.5-flash because it is fast enough for real-time webhook processing
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert payment systems diagnostician. Analyze this failed Razorpay transaction.
    
    Error Code: {error_code}
    Error Description: {error_description}
    Additional Metadata: {metadata}
    
    Classify the root cause of this failure. If the error implies a temporary bank timeout 
    or network drop, it is a NETWORK_DROP. If the bank rejected it for funds, INSUFFICIENT_FUNDS. 
    If it looks like a risk hold, SUSPECTED_FRAUD. If you are unsure, default to REQUIRES_HUMAN.
    """

    try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=PaymentDiagnosis,
                    temperature=0.1
                )
            )
            
        
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            import json
            result = json.loads(raw_text)
            return PaymentDiagnosis(**result)
            
    except Exception as e:
        print(f"AI Layer Failure: {e}")
        # The Ultimate Guardrail: If the AI fails or hallucinates, safely degrade to a human queue
        return PaymentDiagnosis(
            diagnosis_class=DiagnosisClass.REQUIRES_HUMAN,
            confidence_score=0.0,
            reasoning="System exception or hallucination caught in AI layer."
        )
