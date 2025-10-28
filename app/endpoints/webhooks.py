from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
import stripe
from stripe import SignatureVerificationError

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
    except SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event['type'] == 'customer.created':
        customer = event['data']['object']
        print(f"Customer created: {customer['id']}")
    elif event['type'] == 'customer.subscription.created':
        await stripe_service.handle_subscription_created_event(db, event)
    elif event['type'] == 'customer.subscription.updated':
        await stripe_service.handle_subscription_updated_event(db, event)
    elif event['type'] == 'customer.subscription.deleted':
        await stripe_service.handle_subscription_deleted_event(db, event)
    elif event['type'] == 'invoice.paid':
        await stripe_service.handle_invoice_paid_event(db, event)
    else:
        print(f"Unhandled event type {event['type']}")

    return {"status": "success"}
