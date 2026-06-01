from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_db
from backend.models.subscription import Subscription
from backend.models.user import User
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/billing", tags=["billing"])
ACTIVE_STATUSES = {"active", "trialing"}


def _stripe_ready() -> bool:
    return bool(settings.STRIPE_API_KEY and settings.STRIPE_PRICE_ID)


def _sync_subscription_from_stripe(db: Session, subscription: Any, customer_email: str | None = None) -> None:
    customer_id = subscription.get("customer")
    user = None
    if customer_id:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user and customer_email:
        user = db.query(User).filter(User.email == customer_email).first()
    if not user:
        return

    user.stripe_customer_id = customer_id or user.stripe_customer_id
    user.stripe_subscription_id = subscription.get("id") or user.stripe_subscription_id
    user.subscription_status = subscription.get("status") or "inactive"

    period_end = subscription.get("current_period_end")
    current_period_end = (
        datetime.fromtimestamp(period_end, tz=timezone.utc) if isinstance(period_end, int) else None
    )
    price_id = None
    items = subscription.get("items", {}).get("data", []) if isinstance(subscription.get("items"), dict) else []
    if items:
        price_id = items[0].get("price", {}).get("id")

    existing = None
    if user.stripe_subscription_id:
        existing = db.query(Subscription).filter(Subscription.stripe_subscription_id == user.stripe_subscription_id).first()
    if not existing:
        existing = Subscription(user_id=user.id, stripe_subscription_id=user.stripe_subscription_id)
        db.add(existing)
    existing.stripe_customer_id = user.stripe_customer_id
    existing.status = user.subscription_status
    existing.price_id = price_id
    existing.current_period_end = current_period_end


@router.get("/subscription")
def subscription_status(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "subscription_status": current_user.subscription_status,
        "active": current_user.subscription_status in ACTIVE_STATUSES,
        "stripe_configured": _stripe_ready(),
    }


@router.post("/create-checkout-session")
def create_checkout_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not _stripe_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured. Set STRIPE_API_KEY and STRIPE_PRICE_ID.",
        )
    stripe.api_key = settings.STRIPE_API_KEY
    checkout_params = {
        "mode": "subscription",
        "line_items": [{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
        "success_url": f"{settings.APP_BASE_URL}/best-bets?checkout=success",
        "cancel_url": f"{settings.APP_BASE_URL}/pricing?checkout=cancelled",
        "metadata": {"user_id": str(current_user.id), "email": current_user.email},
    }
    if current_user.stripe_customer_id:
        checkout_params["customer"] = current_user.stripe_customer_id
    else:
        checkout_params["customer_email"] = current_user.email
    session = stripe.checkout.Session.create(**checkout_params)
    if session.customer and not current_user.stripe_customer_id:
        current_user.stripe_customer_id = session.customer
        db.commit()
    return {"checkout_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    if not settings.STRIPE_WEBHOOK_SECRET or not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stripe webhook is not configured")

    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook payload") from exc

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        subscription_id = data_object.get("subscription")
        customer_id = data_object.get("customer")
        user_id = data_object.get("metadata", {}).get("user_id")
        user = db.query(User).filter(User.id == int(user_id)).first() if user_id else None
        if user:
            user.stripe_customer_id = customer_id
            user.stripe_subscription_id = subscription_id
        if subscription_id:
            stripe.api_key = settings.STRIPE_API_KEY
            subscription = stripe.Subscription.retrieve(subscription_id)
            _sync_subscription_from_stripe(db, subscription, data_object.get("customer_email"))
    elif event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
        _sync_subscription_from_stripe(db, data_object)

    db.commit()
    return {"received": True}
