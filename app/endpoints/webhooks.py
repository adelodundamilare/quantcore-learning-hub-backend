from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
import stripe

from app.core.config import settings
from app.utils import deps
from app.services.stripe import stripe_service

router = APIRouter()

@router.post("/stripe-webhook")
async def stripe_webhook(request: Request, db: Session = Depends(deps.get_db)):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event['type'] == 'customer.created':
        customer = event['data']['object']
        print(f"Customer created: {customer['id']}")
    elif event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        print(f"Subscription created: {subscription['id']}")
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        print(f"Subscription updated: {subscription['id']}")
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        print(f"Subscription deleted: {subscription['id']}")
    elif event['type'] == 'invoice.paid':
        await stripe_service.handle_invoice_paid_event(db, event)
    else:
        print(f"Unhandled event type {event['type']}")

    return {"status": "success"}
