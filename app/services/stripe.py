import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.config import settings
from app.models.user import User
from app.models.billing import StripeCustomer, Subscription
from app.crud.subscription import subscription as crud_subscription
from app.crud.stripe_customer import stripe_customer as crud_stripe_customer
from app.schemas.billing import StripeCustomerCreate

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    def __init__(self):
        pass

    async def _make_request(self, stripe_api_call, *args, **kwargs):
        try:
            result = stripe_api_call(*args, **kwargs)
            return result
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Stripe error: {e.user_message}")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

    async def create_customer(self, db: Session, user: User) -> StripeCustomer:
        customer = await self._make_request(
            stripe.Customer.create,
            email=user.email,
            name=user.full_name or user.email,
            metadata={"user_id": str(user.id)}
        )
        customer_in = StripeCustomerCreate(user_id=user.id, stripe_customer_id=customer.id)
        return crud_stripe_customer.create(db, obj_in=customer_in)

    async def get_customer(self, stripe_customer_id: str) -> stripe.Customer:
        return await self._make_request(stripe.Customer.retrieve, stripe_customer_id)

    async def create_setup_intent(self, stripe_customer_id: str) -> stripe.SetupIntent:
        return await self._make_request(
            stripe.SetupIntent.create,
            customer=stripe_customer_id,
            usage="off_session",
        )

    async def attach_payment_method(self, stripe_customer_id: str, payment_method_id: str) -> stripe.PaymentMethod:
        return await self._make_request(
            stripe.PaymentMethod.attach,
            payment_method_id,
            customer=stripe_customer_id,
        )

    async def get_payment_methods(self, stripe_customer_id: str) -> List[stripe.PaymentMethod]:
        payment_methods = await self._make_request(
            stripe.PaymentMethod.list,
            customer=stripe_customer_id,
            type="card"
        )
        return payment_methods.data

    async def create_subscription(self, db: Session, user: User, price_ids: List[str], payment_method_id: Optional[str] = None) -> Subscription:
        if not user.stripe_customer:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stripe customer not found for this user.")

        items = [{"price": price_id} for price_id in price_ids]
        subscription = await self._make_request(
            stripe.Subscription.create,
            customer=user.stripe_customer.stripe_customer_id,
            items=items,
            default_payment_method=payment_method_id,
            expand=["latest_invoice.payment_intent"]
        )

        db_subscription = Subscription(
            user_id=user.id,
            stripe_customer_id=user.stripe_customer.stripe_customer_id,
            stripe_subscription_id=subscription.id,
            stripe_price_id=",".join(price_ids),
            status=subscription.status,
            current_period_start=datetime.fromtimestamp(subscription.current_period_start),
            current_period_end=datetime.fromtimestamp(subscription.current_period_end),
            cancel_at_period_end=subscription.cancel_at_period_end,
        )
        return crud_subscription.create(db, obj_in=db_subscription)

    async def get_subscription(self, db: Session, subscription_id: str) -> Optional[Subscription]:
        return crud_subscription.get_by_stripe_subscription_id(db, stripe_subscription_id=subscription_id)

    async def get_subscriptions(self, db: Session, user: User) -> List[Subscription]:
        if not user.stripe_customer:
            return []
        return crud_subscription.get_multi_by_user(db, user_id=user.id)

    async def cancel_subscription(self, db: Session, subscription_id: str) -> Subscription:
        db_subscription = await self.get_subscription(db, subscription_id)
        if not db_subscription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")

        stripe_subscription = await self._make_request(stripe.Subscription.cancel, subscription_id)

        update_data = {
            "status": stripe_subscription.status,
            "cancel_at_period_end": stripe_subscription.cancel_at_period_end
        }
        return crud_subscription.update(db, db_obj=db_subscription, obj_in=update_data)

    async def get_invoices(self, stripe_customer_id: str) -> List[stripe.Invoice]:
        return await self._make_request(stripe.Invoice.list, customer=stripe_customer_id)

    async def create_invoice(self, stripe_customer_id: str, amount: float, currency: str, description: Optional[str] = None) -> stripe.Invoice:
        unit_amount_cents = int(amount * 100)
        await self._make_request(
            stripe.InvoiceItem.create,
            customer=stripe_customer_id,
            amount=unit_amount_cents,
            currency=currency,
            description=description
        )
        return await self._make_request(
            stripe.Invoice.create,
            customer=stripe_customer_id,
            collection_method='send_invoice',
            days_until_due=7,
            auto_advance=False
        )

    async def create_product(self, name: str, description: Optional[str] = None) -> stripe.Product:
        return await self._make_request(stripe.Product.create, name=name, description=description, type="service")

    async def get_product(self, product_id: str) -> stripe.Product:
        return await self._make_request(stripe.Product.retrieve, product_id)

    async def update_product(self, product_id: str, name: Optional[str] = None, description: Optional[str] = None, active: Optional[bool] = None) -> stripe.Product:
        return await self._make_request(stripe.Product.modify, product_id, name=name, description=description, active=active)

    async def delete_product(self, product_id: str) -> stripe.Product:
        return await self._make_request(stripe.Product.delete, product_id)

    async def create_price(self, product_id: str, unit_amount: int, currency: str = "usd", recurring_interval: str = "month") -> stripe.Price:
        return await self._make_request(
            stripe.Price.create,
            product=product_id,
            unit_amount=unit_amount,
            currency=currency,
            recurring={"interval": recurring_interval}
        )

    async def get_price(self, price_id: str) -> stripe.Price:
        return await self._make_request(stripe.Price.retrieve, price_id)

    async def update_price(self, price_id: str, active: Optional[bool] = None) -> stripe.Price:
        return await self._make_request(stripe.Price.modify, price_id, active=active)

    async def get_all_products(self) -> List[stripe.Product]:
        products = await self._make_request(stripe.Product.list)
        return products.data

    async def get_all_prices(self) -> List[stripe.Price]:
        prices = await self._make_request(stripe.Price.list)
        return prices.data

stripe_service = StripeService()