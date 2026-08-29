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
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")


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
    version="1.1.0"
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
# AUTHENTICATE SUPABASE USER
# ============================================================

def get_authenticated_user(request: Request):

    authorization = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is required"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header"
        )

    access_token = authorization.replace(
        "Bearer ",
        "",
        1
    ).strip()

    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Access token is missing"
        )

    try:

        user_response = supabase.auth.get_user(
            access_token
        )

        user = getattr(
            user_response,
            "user",
            None
        )

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired access token"
            )

        return user

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {exc}"
        )


# ============================================================
# CREATE RAZORPAY SUBSCRIPTION
# ============================================================

@app.post("/create-subscription")
async def create_subscription(request: Request):

    # --------------------------------------------------------
    # IMPORTANT:
    # We DO NOT accept user_id from the request body.
    #
    # The user_id comes from the verified Supabase JWT.
    # --------------------------------------------------------

    user = get_authenticated_user(request)

    user_id = user.id


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

            current_status = current.get("status")

            if current_status in [
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
                    "status": current_status,
                    "amount": 100,
                    "currency": "INR"
                }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Subscription lookup failed: "
                f"{exc}"
            )
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
    # Save subscription to Supabase
    # --------------------------------------------------------

    record = {
        "user_id": user_id,
        "status": subscription.get(
            "status",
            "created"
        ),
        "plan_name": "NSE Quant Trading Monthly",
        "amount": 100,
        "razorpay_subscription_id":
            subscription_id,
        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat()
    }


    try:

        # Because user_id has a unique index,
        # upsert safely handles an existing inactive row.

        (
            supabase
            .table("subscriptions")
            .upsert(
                record,
                on_conflict="user_id"
            )
            .execute()
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Razorpay subscription was created "
                "but Supabase could not store it: "
                f"{exc}"
            )
        )


    return {
        "success": True,
        "existing": False,
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
    # Verify Razorpay webhook signature
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


    # --------------------------------------------------------
    # Subscription events
    # --------------------------------------------------------

    if event_name == "subscription.authenticated":

        await process_subscription_event(
            event,
            "authenticated"
        )

    elif event_name == "subscription.activated":

        await process_subscription_event(
            event,
            "active"
        )

    elif event_name == "subscription.charged":

        await process_subscription_event(
            event,
            "active"
        )

    elif event_name == "subscription.cancelled":

        await process_subscription_event(
            event,
            "cancelled"
        )

    elif event_name == "subscription.completed":

        await process_subscription_event(
            event,
            "completed"
        )

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


    # --------------------------------------------------------
    # Subscription entity
    # --------------------------------------------------------

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
    # Find subscription in our database
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


    # --------------------------------------------------------
    # Update status
    # --------------------------------------------------------

    update_data = {
        "status": new_status,
        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat()
    }


    # --------------------------------------------------------
    # Payment entity
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
    # Subscription start date
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
    # Subscription end date
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