import requests
import time
import uuid

# The URL of your local FastAPI server
WEBHOOK_URL = "http://127.0.0.1:8000/webhooks/razorpay"

# We generate a random event ID to simulate a fresh webhook
event_id = f"evt_test_{uuid.uuid4().hex[:8]}"

payload = {
    "event": "payment.failed",
    "created_at": int(time.time()),
    "payload": {
        "payment": {
            "entity": {
                "error_code": "GATEWAY_TIMEOUT",
                "error_description": "The issuer bank's network timed out during the transaction. Please try again."
            }
        }
    }
}

headers = {
    "x-razorpay-event-id": event_id,
    "Content-Type": "application/json"
}

print(" Firing First Webhook (Simulating Razorpay)...")
response_1 = requests.post(WEBHOOK_URL, json=payload, headers=headers)
print(f"Response: {response_1.status_code} - {response_1.json()}")

print("\n Waiting 5 seconds to let the AI process it...")
time.sleep(5)

print("\n Firing Duplicate Webhook (Simulating a Network Retry Glitch)...")
response_2 = requests.post(WEBHOOK_URL, json=payload, headers=headers)
print(f"Response: {response_2.status_code} - {response_2.json()}")

print("\n Check your Uvicorn server terminal to see the AI and Database in action!")
