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
from app.crud.user import user as crud_user
from app.schemas.billing import BillingReportSchema, StripeCustomerCreate, BillingHistoryInvoiceSchema, TransactionTimeseriesReport, TimeseriesDataPoint
from app.schemas.user import User as UserSchema
from app.crud.school import school as crud_school
from collections import defaultdict
from enum import Enum

stripe.api_key = settings.STRIPE_SECRET_KEY

class TimePeriod(str, Enum):
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"

class StripeService:
    def __init__(self):
        pass

    async def _make_request(self, stripe_api_call, *args, **kwargs):
        try:
            result = stripe_api_call(*args, **kwargs)
            return result
        except stripe.StripeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Stripe error: {e.user_message}")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

    async def _get_or_create_customer(self, db: Session, user_schema: UserSchema) -> StripeCustomer:
        user_model = crud_user.get(db, id=user_schema.id)
        if not user_model:
            raise HTTPException(status_code=404, detail="User not found in database.")

        if user_model.stripe_customer:
            return user_model.stripe_customer

        customer = await self._make_request(
            stripe.Customer.create,
            email=user_model.email,
            name=user_model.full_name or user_model.email,
            metadata={"user_id": str(user_model.id)}
        )
        customer_in = StripeCustomerCreate(user_id=user_model.id, stripe_customer_id=customer.id)
        new_db_customer = crud_stripe_customer.create(db, obj_in=customer_in)

        db.refresh(user_model)

        return new_db_customer

    async def create_customer(self, db: Session, user: UserSchema) -> StripeCustomer:
        user_model = crud_user.get(db, id=user.id)
        if not user_model:
            raise HTTPException(status_code=404, detail="User not found in database.")
        if user_model.stripe_customer:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stripe customer already exists for this user.")
        return await self._get_or_create_customer(db, user)

    async def get_customer(self, stripe_customer_id: str) -> stripe.Customer:
        return await self._make_request(stripe.Customer.retrieve, stripe_customer_id)

    async def create_setup_intent(self, db: Session, user: UserSchema) -> stripe.SetupIntent:
        customer = await self._get_or_create_customer(db, user)
        return await self._make_request(
            stripe.SetupIntent.create,
            customer=customer.stripe_customer_id,
            usage="off_session",
        )

    async def attach_payment_method(self, db: Session, user: UserSchema, payment_method_id: str) -> stripe.PaymentMethod:
        customer = await self._get_or_create_customer(db, user)
        return await self._make_request(
            stripe.PaymentMethod.attach,
            payment_method_id,
            customer=customer.stripe_customer_id,
        )

    async def get_payment_methods(self, db: Session, user: UserSchema) -> List[stripe.PaymentMethod]:
        customer = await self._get_or_create_customer(db, user)
        payment_methods = await self._make_request(
            stripe.PaymentMethod.list,
            customer=customer.stripe_customer_id,
            type="card"
        )
        return payment_methods.data

    async def create_subscription(self, db: Session, user: UserSchema, price_ids: List[str], payment_method_id: Optional[str] = None) -> Subscription:
        customer = await self._get_or_create_customer(db, user)
        user_model = crud_user.get(db, id=user.id)

        items = [{"price": price_id} for price_id in price_ids]
        subscription = await self._make_request(
            stripe.Subscription.create,
            customer=customer.stripe_customer_id,
            items=items,
            default_payment_method=payment_method_id,
            expand=["latest_invoice.payment_intent"]
        )

        db_subscription = Subscription(
            user_id=user_model.id,
            stripe_customer_id=customer.stripe_customer_id,
            stripe_subscription_id=subscription.id,
            stripe_price_id=",".join(price_ids),
            status=subscription.status,
            current_period_start=datetime.fromtimestamp(subscription.current_period_start),
            current_period_end=datetime.fromtimestamp(subscription.current_period_end),
            cancel_at_period_end=subscription.cancel_at_period_end,
        )
        return crud_subscription.create(db, obj_in=db_subscription)

    async def create_checkout_session(self, db: Session, user: UserSchema, price_ids: List[str], success_url: str, cancel_url: str) -> stripe.checkout.Session:
        customer = await self._get_or_create_customer(db, user)
        line_items = [{"price": price_id, "quantity": 1} for price_id in price_ids]

        checkout_session = await self._make_request(
            stripe.checkout.Session.create,
            customer=customer.stripe_customer_id,
            line_items=line_items,
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return checkout_session

    async def get_subscription(self, db: Session, subscription_id: str) -> Optional[Subscription]:
        return crud_subscription.get_by_stripe_subscription_id(db, stripe_subscription_id=subscription_id)

    async def get_subscriptions(self, db: Session, user: UserSchema) -> List[Subscription]:
        user_model = crud_user.get(db, id=user.id)
        if not user_model or not user_model.stripe_customer:
            return []
        return crud_subscription.get_multi_by_user(db, user_id=user_model.id)

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

    async def get_invoices(self, db: Session, user: UserSchema) -> List[BillingHistoryInvoiceSchema]:
        user_model = crud_user.get(db, id=user.id)
        if not user_model or not user_model.stripe_customer:
            return []

        invoices = await self._make_request(stripe.Invoice.list, customer=user_model.stripe_customer.stripe_customer_id, expand=["data.charge"])

        history = []
        for invoice in invoices.data:
            payment_method_details = "N/A"
            if invoice.charge and invoice.charge.payment_method_details and invoice.charge.payment_method_details.card:
                card = invoice.charge.payment_method_details.card
                payment_method_details = f"{card.brand.capitalize()} **** {card.last4}"

            history.append(
                BillingHistoryInvoiceSchema(
                    invoice_no=invoice.number or invoice.id,
                    school_name=user_model.full_name,
                    school_email=user_model.email,
                    amount=invoice.amount_paid / 100,
                    date=datetime.fromtimestamp(invoice.created),
                    payment_method=payment_method_details,
                    status=invoice.status
                )
            )
        return history

    async def get_billing_report(self, db: Session) -> BillingReportSchema:

        total_revenue = 0.0
        charges = await self._make_request(stripe.Charge.list, limit=100)
        while True:
            for charge in charges.data:
                if charge.paid and charge.status == 'succeeded':
                    total_revenue += charge.amount / 100.0
            if not charges.has_more:
                break
            charges = await self._make_request(stripe.Charge.list, starting_after=charges.data[-1].id, limit=100)

        total_active_subscriptions = crud_subscription.get_active_count(db)
        number_of_schools = crud_school.get_all_schools_count(db)

        return BillingReportSchema(
            total_revenue=total_revenue,
            total_active_subscriptions=total_active_subscriptions,
            number_of_schools=number_of_schools
        )

    async def get_transaction_timeseries(self, db: Session, period: TimePeriod, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> TransactionTimeseriesReport:
        timeseries_data = defaultdict(lambda: {"revenue": 0.0, "transactions": 0})

        filters = {"limit": 100}
        if start_date or end_date:
            filters["created"] = {}
            if start_date:
                filters["created"]["gte"] = int(start_date.timestamp())
            if end_date:
                filters["created"]["lte"] = int(end_date.timestamp())

        charges = await self._make_request(stripe.Charge.list, **filters)

        while True:
            for charge in charges.data:
                if charge.paid and charge.status == 'succeeded':
                    charge_date = datetime.fromtimestamp(charge.created)

                    if period == TimePeriod.YEAR:
                        period_key = str(charge_date.year)
                    elif period == TimePeriod.MONTH:
                        period_key = charge_date.strftime("%Y-%m")
                    elif period == TimePeriod.WEEK:
                        iso = charge_date.isocalendar()
                        period_key = f"{iso[0]}-W{iso[1]:02d}"

                    timeseries_data[period_key]["revenue"] += charge.amount / 100.0
                    timeseries_data[period_key]["transactions"] += 1

            if not charges.has_more:
                break

            filters_pagination = dict(filters)
            filters_pagination["starting_after"] = charges.data[-1].id
            charges = await self._make_request(stripe.Charge.list, **filters_pagination)

        sorted_data = sorted(timeseries_data.items())

        report_data = [
            TimeseriesDataPoint(
                period=key,
                revenue=values["revenue"],
                transactions=values["transactions"]
            )
            for key, values in sorted_data
        ]

        return TransactionTimeseriesReport(data=report_data)

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