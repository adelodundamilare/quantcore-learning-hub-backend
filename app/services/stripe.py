import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from app.core.config import settings
from app.crud.user import user as user_crud
from app.models.user import User

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

    async def create_customer(self, user: User) -> stripe.Customer:
        customer = await self._make_request(
            stripe.Customer.create,
            email=user.email,
            name=user.full_name or user.email,
            metadata={
                "user_id": str(user.id)
            }
        )
        return customer

    async def get_customer(self, stripe_customer_id: str) -> stripe.Customer:
        customer = await self._make_request(stripe.Customer.retrieve, stripe_customer_id)
        return customer

    async def create_setup_intent(self, stripe_customer_id: str) -> stripe.SetupIntent:
        setup_intent = await self._make_request(
            stripe.SetupIntent.create,
            customer=stripe_customer_id,
            usage="off_session",
        )
        return setup_intent

    async def attach_payment_method(self, stripe_customer_id: str, payment_method_id: str) -> stripe.PaymentMethod:
        payment_method = await self._make_request(
            stripe.PaymentMethod.attach,
            payment_method_id,
            customer=stripe_customer_id,
        )
        return payment_method

    async def get_payment_methods(self, stripe_customer_id: str) -> List[stripe.PaymentMethod]:
        payment_methods = await self._make_request(
            stripe.PaymentMethod.list,
            customer=stripe_customer_id,
            type="card"
        )
        return payment_methods.data

    async def create_subscription(self, stripe_customer_id: str, price_id: str, payment_method_id: Optional[str] = None) -> stripe.Subscription:
        subscription = await self._make_request(
            stripe.Subscription.create,
            customer=stripe_customer_id,
            items=[{"price": price_id}],
            default_payment_method=payment_method_id,
            expand=["latest_invoice.payment_intent"]
        )
        return subscription

    async def get_subscription(self, subscription_id: str) -> stripe.Subscription:
        subscription = await self._make_request(stripe.Subscription.retrieve, subscription_id)
        return subscription

    async def cancel_subscription(self, subscription_id: str) -> stripe.Subscription:
        subscription = await self._make_request(stripe.Subscription.cancel, subscription_id)
        return subscription

    async def get_invoices(self, stripe_customer_id: str) -> List[stripe.Invoice]:
        invoices = await self._make_request(stripe.Invoice.list, customer=stripe_customer_id)
        return invoices.data

    async def create_product(self, name: str, description: Optional[str] = None) -> stripe.Product:
        product = await self._make_request(
            stripe.Product.create,
            name=name,
            description=description,
            type="service"
        )
        return product

    async def get_product(self, product_id: str) -> stripe.Product:
        product = await self._make_request(stripe.Product.retrieve, product_id)
        return product

    async def update_product(self, product_id: str, name: Optional[str] = None, description: Optional[str] = None) -> stripe.Product:
        product = await self._make_request(
            stripe.Product.modify,
            product_id,
            name=name,
            description=description
        )
        return product

    async def delete_product(self, product_id: str) -> stripe.Product:
        product = await self._make_request(stripe.Product.delete, product_id)
        return product

    async def create_price(self, product_id: str, unit_amount: int, currency: str = "usd", recurring_interval: str = "month") -> stripe.Price:
        price = await self._make_request(
            stripe.Price.create,
            product=product_id,
            unit_amount=unit_amount,
            currency=currency,
            recurring={"interval": recurring_interval}
        )
        return price

    async def get_price(self, price_id: str) -> stripe.Price:
        price = await self._make_request(stripe.Price.retrieve, price_id)
        return price

    async def update_price(self, price_id: str, active: Optional[bool] = None) -> stripe.Price:
        price = await self._make_request(
            stripe.Price.modify,
            price_id,
            active=active
        )
        return price

    async def get_all_products(self) -> List[stripe.Product]:
        products = await self._make_request(stripe.Product.list)
        return products.data

    async def get_all_prices(self) -> List[stripe.Price]:
        prices = await self._make_request(stripe.Price.list)
        return prices.data

stripe_service = StripeService()