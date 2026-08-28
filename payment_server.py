import os
import json
import hmac
import hashlib
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from supabase import create_client
import razorpay


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_PLAN_ID = os.getenv("RAZORPAY_PLAN_ID")

RAZORPAY_WEBHOOK_SECRET = os.getenv(
    "RAZORPAY_WEBHOOK_SECRET"
)


# ============================================================
# VALIDATE CONFIGURATION
# ============================================================

required = {
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_SERVICE_KEY": SUPABASE_SERVICE_KEY,
    "RAZORPAY_KEY_ID": RAZORPAY_KEY_ID,
    "RAZORPAY_KEY_SECRET": RAZORPAY_KEY_SECRET,
    "RAZORPAY_PLAN_ID": RAZORPAY_PLAN_ID,
    "RAZORPAY_WEBHOOK_SECRET": RAZORPAY_WEBHOOK_SECRET,
}

missing = [
    name
    for name, value in required.items()
    if not value
]

if missing:
    raise RuntimeError(
        "Missing environment variables: "
        + ", ".join(missing)
    )


# ============================================================
# CLIENTS
# ============================================================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)

razorpay_client = razorpay.Client(
    auth=(
        RAZORPAY_KEY_ID,
        RAZORPAY_KEY_SECRET
    )
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="NSE Quant Trading Payment API",
    version="1.0.0"
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "nse-quant-payment-api"
    }


# ============================================================
# CREATE RAZORPAY SUBSCRIPTION
# ============================================================

@app.post("/create-subscription")
async def create_subscription(request: Request):

    body = await request.json()

    user_id = body.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="user_id is required"
        )

    # --------------------------------------------------------
    # Verify that the Supabase user exists
    # --------------------------------------------------------

    try:

        user_response = (
            supabase
            .auth.admin
            .get_user_by_id(user_id)
        )

        if not user_response:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Unable to verify user: {exc}"
        )


    # --------------------------------------------------------
    # Check existing subscription
    # --------------------------------------------------------

    try:

        existing = (
            supabase
            .table("subscriptions")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if existing.data:

            current = existing.data[0]

            if current.get("status") in [
                "active",
                "authenticated",
                "pending"
            ]:

                return {
                    "success": True,
                    "existing": True,
                    "subscription_id":
                        current.get(
                            "razorpay_subscription_id"
                        ),
                    "status":
                        current.get("status")
                }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Subscription lookup failed: {exc}"
        )


    # --------------------------------------------------------
    # Create Razorpay subscription
    # --------------------------------------------------------

    try:

        subscription = (
            razorpay_client
            .subscription
            .create(
                {
                    "plan_id": RAZORPAY_PLAN_ID,
                    "total_count": 12,
                    "quantity": 1,
                    "customer_notify": 1
                }
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=f"Razorpay error: {exc}"
        )


    subscription_id = subscription["id"]


    # --------------------------------------------------------
    # Store subscription in Supabase
    # --------------------------------------------------------

    try:

        record = {
            "user_id": user_id,
            "status": subscription.get(
                "status",
                "created"
            ),
            "plan_name": "NSE Quant Trading Monthly",
            "amount": 100,
            "razorpay_subscription_id":
                subscription_id
        }

        (
            supabase
            .table("subscriptions")
            .insert(record)
            .execute()
        )

    except Exception as exc:

        # ----------------------------------------------------
        # If DB insertion fails, don't silently continue.
        # ----------------------------------------------------

        raise HTTPException(
            status_code=500,
            detail=(
                "Subscription was created in Razorpay "
                "but could not be stored in Supabase: "
                f"{exc}"
            )
        )


    return {
        "success": True,
        "subscription_id": subscription_id,
        "plan_id": RAZORPAY_PLAN_ID,
        "status": subscription.get(
            "status",
            "created"
        ),
        "amount": 100,
        "currency": "INR"
    }


# ============================================================
# RAZORPAY WEBHOOK
# ============================================================

@app.post("/razorpay-webhook")
async def razorpay_webhook(request: Request):

    payload = await request.body()

    received_signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    if not received_signature:

        raise HTTPException(
            status_code=400,
            detail="Missing Razorpay signature"
        )


    # --------------------------------------------------------
    # Verify webhook signature
    # --------------------------------------------------------

    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()


    if not hmac.compare_digest(
        expected_signature,
        received_signature
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid webhook signature"
        )


    try:

        event = json.loads(
            payload.decode("utf-8")
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload"
        )


    event_name = event.get(
        "event",
        ""
    )


    # ========================================================
    # SUBSCRIPTION AUTHENTICATED
    # ========================================================

    if event_name == "subscription.authenticated":

        await process_subscription_event(
            event,
            "authenticated"
        )


    # ========================================================
    # SUBSCRIPTION ACTIVATED
    # ========================================================

    elif event_name == "subscription.activated":

        await process_subscription_event(
            event,
            "active"
        )


    # ========================================================
    # SUBSCRIPTION CHARGED
    # ========================================================

    elif event_name == "subscription.charged":

        await process_subscription_event(
            event,
            "active"
        )


    # ========================================================
    # SUBSCRIPTION CANCELLED
    # ========================================================

    elif event_name == "subscription.cancelled":

        await process_subscription_event(
            event,
            "cancelled"
        )


    # ========================================================
    # SUBSCRIPTION COMPLETED
    # ========================================================

    elif event_name == "subscription.completed":

        await process_subscription_event(
            event,
            "completed"
        )


    # ========================================================
    # PAYMENT FAILED
    # ========================================================

    elif event_name == "subscription.pending":

        await process_subscription_event(
            event,
            "pending"
        )


    return {
        "received": True,
        "event": event_name
    }


# ============================================================
# PROCESS SUBSCRIPTION EVENT
# ============================================================

async def process_subscription_event(
    event,
    new_status
):

    payload = event.get(
        "payload",
        {}
    )

    subscription_entity = (
        payload
        .get("subscription", {})
        .get("entity", {})
    )

    subscription_id = (
        subscription_entity
        .get("id")
    )

    if not subscription_id:
        return


    # --------------------------------------------------------
    # Find our user
    # --------------------------------------------------------

    result = (
        supabase
        .table("subscriptions")
        .select("*")
        .eq(
            "razorpay_subscription_id",
            subscription_id
        )
        .limit(1)
        .execute()
    )

    if not result.data:
        return


    existing = result.data[0]

    update_data = {
        "status": new_status,
        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat()
    }


    # --------------------------------------------------------
    # Extract payment information
    # --------------------------------------------------------

    payment_entity = (
        payload
        .get("payment", {})
        .get("entity", {})
    )

    payment_id = payment_entity.get(
        "id"
    )

    if payment_id:

        update_data[
            "razorpay_payment_id"
        ] = payment_id


    # --------------------------------------------------------
    # Start date
    # --------------------------------------------------------

    start_at = subscription_entity.get(
        "start_at"
    )

    if start_at:

        try:

            update_data["start_date"] = (
                datetime.fromtimestamp(
                    int(start_at),
                    tz=timezone.utc
                ).isoformat()
            )

        except Exception:
            pass


    # --------------------------------------------------------
    # End date
    # --------------------------------------------------------

    end_at = subscription_entity.get(
        "end_at"
    )

    if end_at:

        try:

            update_data["end_date"] = (
                datetime.fromtimestamp(
                    int(end_at),
                    tz=timezone.utc
                ).isoformat()
            )

        except Exception:
            pass


    # --------------------------------------------------------
    # Update Supabase
    # --------------------------------------------------------

    (
        supabase
        .table("subscriptions")
        .update(update_data)
        .eq(
            "id",
            existing["id"]
        )
        .execute()
    )