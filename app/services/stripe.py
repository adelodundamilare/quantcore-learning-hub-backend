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
from app.crud.role import role as crud_role
from app.core.constants import RoleEnum
from app.schemas.billing import BillingReportSchema, InvoiceCreate, StripeCustomerCreate, BillingHistoryInvoiceSchema, TransactionTimeseriesReport, TimeseriesDataPoint, SubscriptionDetailSchema, SchoolInvoiceSchema, InvoicePaymentIntentSchema, InvoiceCheckoutSessionCreate, CheckoutSession
from app.schemas.user import User as UserSchema, UserContext
from app.crud.school import school as crud_school
from app.services.email import EmailService
from app.services.notification import notification_service
from app.crud.stripe_product import stripe_product as crud_stripe_product
from app.crud.stripe_price import stripe_price as crud_stripe_price
from app.crud.invoice import invoice as crud_invoice
from app.models.billing import Invoice
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

    async def _get_or_create_customer_from_school_id(self, db: Session, school_id: int) -> StripeCustomer:
        school = crud_school.get(db, id=school_id)
        if not school:
            raise HTTPException(status_code=404, detail="School not found in database.")

        school_admin_role = crud_role.get_by_name(db, name=RoleEnum.SCHOOL_ADMIN)
        if not school_admin_role:
            raise HTTPException(status_code=500, detail="School admin role not found.")

        school_admins = crud_user.get_users_by_school_and_role(db, school_id=school.id, role_id=school_admin_role.id)
        if not school_admins:
            raise HTTPException(status_code=404, detail="No school admin found for this school.")

        user_model = school_admins[0]

        if user_model.stripe_customer:
            return user_model.stripe_customer

        customer = await self._make_request(
            stripe.Customer.create,
            email=user_model.email,
            name=user_model.full_name or user_model.email,
            metadata={"user_id": str(user_model.id), "school_id": str(school.id)}
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

    async def get_subscriptions(self, db: Session, user: UserSchema, status: str = 'all') -> List[SubscriptionDetailSchema]:
        user_model = crud_user.get(db, id=user.id)
        if not user_model or not user_model.stripe_customer:
            return []

        try:
            stripe_subscriptions = await self._make_request(
                stripe.Subscription.list,
                customer=user_model.stripe_customer.stripe_customer_id,
                status=status,
                expand=["data.latest_invoice", "data.default_payment_method", "data.items.data.price"]
            )

            product_ids = set()
            if stripe_subscriptions and stripe_subscriptions.data:
                for stripe_sub in stripe_subscriptions.data:
                    if stripe_sub.get('items') and stripe_sub['items'].get('data'):
                        for item in stripe_sub['items']['data']:
                            if item.get('price') and item['price'].get('product'):
                                product_ids.add(item['price']['product'])

            product_map = {}
            if product_ids:
                products = await self._make_request(stripe.Product.list, ids=list(product_ids))
                product_map = {p.id: p.name for p in products.data}

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Could not retrieve subscriptions for customer {user_model.stripe_customer.stripe_customer_id}: {e}", exc_info=True)
            return []

        subscription_details = []
        for stripe_sub in stripe_subscriptions.data:
            try:
                plan_name = "N/A"
                price = 0.0

                if stripe_sub.get('items') and stripe_sub['items'].get('data'):
                    first_item = stripe_sub['items']['data'][0]
                    if first_item.get('price') and first_item['price'].get('product'):
                        plan_name = product_map.get(first_item['price']['product'], "N/A")
                    if first_item.get('price') and first_item['price'].get('unit_amount') is not None:
                        price = first_item['price']['unit_amount'] / 100

                payment_method = "N/A"
                if stripe_sub.get('default_payment_method') and isinstance(stripe_sub['default_payment_method'], stripe.PaymentMethod):
                    pm = stripe_sub['default_payment_method']
                    if pm.type == 'card' and pm.card:
                        payment_method = f"{pm.card.brand.capitalize()} **** {pm.card.last4}"

                invoice_no = "N/A"
                if stripe_sub.get('latest_invoice') and isinstance(stripe_sub['latest_invoice'], stripe.Invoice):
                    invoice_no = stripe_sub['latest_invoice'].number or stripe_sub['latest_invoice'].id

                start_date = datetime.fromtimestamp(first_item['current_period_start'])
                end_date = datetime.fromtimestamp(first_item['current_period_end'])

                subscription_details.append(
                    SubscriptionDetailSchema(
                        start_date=start_date,
                        end_date=end_date,
                        plan_name=plan_name,
                        price=price,
                        payment_method=payment_method,
                        subscription_id=stripe_sub.id,
                        invoice_no=invoice_no,
                        status=stripe_sub.status,
                        cancel_at_period_end=stripe_sub.cancel_at_period_end
                    )
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error processing subscription {stripe_sub.id}: {e}", exc_info=True)

        return subscription_details

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

    async def update_subscription_auto_renewal(self, db: Session, subscription_id: str, auto_renew: bool, context: UserContext) -> Subscription:
        db_subscription = await self.get_subscription(db, subscription_id)

        if not db_subscription or db_subscription.user_id != context.user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")

        if db_subscription.status != 'active':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Auto-renewal can only be updated for active subscriptions.")

        stripe_subscription = await self._make_request(
            stripe.Subscription.modify,
            subscription_id,
            cancel_at_period_end=auto_renew
        )

        update_data = {
            "status": stripe_subscription.status,
            "cancel_at_period_end": stripe_subscription.cancel_at_period_end
        }
        return crud_subscription.update(db, db_obj=db_subscription, obj_in=update_data)

    async def create_customer_portal_session(self, db: Session, context: UserContext) -> stripe.billing_portal.Session:
        customer = await self._get_or_create_customer(db, context.user)
        portal_session = await self._make_request(
            stripe.billing_portal.Session.create,
            customer=customer.stripe_customer_id,
            return_url=settings.STRIPE_PORTAL_RETURN_URL
        )
        return portal_session

    async def get_invoices(self, db: Session, context: UserContext) -> List[BillingHistoryInvoiceSchema]:
        user_model = context.user

        invoice_params = {
            "limit": 100,
            "expand": ["data.charge", "data.default_payment_method"]
        }

        if not context.role or context.role.name != RoleEnum.SUPER_ADMIN:
            if not user_model.stripe_customer:
                return []
            invoice_params['customer'] = user_model.stripe_customer.stripe_customer_id

        invoices_response = await self._make_request(stripe.Invoice.list, **invoice_params)

        history = []
        for invoice in invoices_response.data:
            payment_method_details = "N/A"

            charge = getattr(invoice, 'charge', None)
            if charge:
                if isinstance(charge, str):
                    try:
                        charge_obj = await self._make_request(stripe.Charge.retrieve, charge)
                        if hasattr(charge_obj, 'payment_method_details') and charge_obj.payment_method_details:
                            pmd = charge_obj.payment_method_details
                            if hasattr(pmd, 'card') and pmd.card:
                                card = pmd.card
                                payment_method_details = f"{card.brand.capitalize()} **** {card.last4}"
                    except:
                        pass
                else:
                    if hasattr(charge, 'payment_method_details') and charge.payment_method_details:
                        pmd = charge.payment_method_details
                        if hasattr(pmd, 'card') and pmd.card:
                            card = pmd.card
                            payment_method_details = f"{card.brand.capitalize()} **** {card.last4}"

            if payment_method_details == "N/A":
                default_pm = getattr(invoice, 'default_payment_method', None)
                if default_pm:
                    if isinstance(default_pm, str):
                        try:
                            pm_obj = await self._make_request(stripe.PaymentMethod.retrieve, default_pm)
                            if hasattr(pm_obj, 'card') and pm_obj.card:
                                payment_method_details = f"{pm_obj.card.brand.capitalize()} **** {pm_obj.card.last4}"
                        except:
                            pass
                    else:
                        if hasattr(default_pm, 'card') and default_pm.card:
                            payment_method_details = f"{default_pm.card.brand.capitalize()} **** {default_pm.card.last4}"

            customer_name = "N/A"
            customer_email = "N/A"

            customer = getattr(invoice, 'customer', None)
            if customer:
                if isinstance(customer, str):
                    try:
                        customer_obj = await self._make_request(stripe.Customer.retrieve, customer)
                        customer_name = getattr(customer_obj, 'name', None) or "N/A"
                        customer_email = getattr(customer_obj, 'email', None) or "N/A"
                    except:
                        pass
                else:
                    customer_name = getattr(customer, 'name', None) or "N/A"
                    customer_email = getattr(customer, 'email', None) or "N/A"

            history.append(
                BillingHistoryInvoiceSchema(
                    invoice_no=invoice.number or invoice.id,
                    school_name=customer_name,
                    school_email=customer_email,
                    amount=invoice.amount_paid / 100,
                    date=datetime.fromtimestamp(invoice.created),
                    payment_method=payment_method_details,
                    status=invoice.status
                )
            )
        return history

    async def get_total_revenue(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> float:
        total_revenue = 0.0
        charge_params = {"limit": 100}
        if start_date:
            charge_params["created"] = {"gte": int(start_date.timestamp())}
        if end_date:
            if "created" not in charge_params:
                charge_params["created"] = {}
            charge_params["created"]["lte"] = int(end_date.timestamp())

        charges = await self._make_request(stripe.Charge.list, **charge_params)

        while True:
            for charge in charges.data:
                if charge.paid and charge.status == 'succeeded':
                    total_revenue += charge.amount / 100.0
            if not charges.has_more:
                break
            charge_params["starting_after"] = charges.data[-1].id
            charges = await self._make_request(stripe.Charge.list, **charge_params)
        return total_revenue

    async def get_billing_report(self, db: Session) -> BillingReportSchema:
        total_revenue = await self.get_total_revenue()
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

    async def create_invoice(self, db: Session, invoice_in: InvoiceCreate) -> stripe.Invoice:
        school_customer = await self._get_or_create_customer_from_school_id(db, school_id=invoice_in.school_id)

        unit_amount_cents = int(invoice_in.amount * 100)

        invoice = await self._make_request(
            stripe.Invoice.create,
            customer=school_customer.stripe_customer_id,
            collection_method='send_invoice',
            days_until_due=7
        )

        await self._make_request(
            stripe.InvoiceItem.create,
            customer=school_customer.stripe_customer_id,
            invoice=invoice.id,
            amount=unit_amount_cents,
            currency=invoice_in.currency,
            description=invoice_in.description
        )

        finalized_invoice = await self._make_request(
            stripe.Invoice.finalize_invoice,
            invoice.id
        )

        due_date = datetime.fromtimestamp(finalized_invoice.due_date) if finalized_invoice.due_date else None

        db_invoice = Invoice(
            school_id=invoice_in.school_id,
            stripe_invoice_id=finalized_invoice.id,
            amount=invoice_in.amount,
            currency=invoice_in.currency,
            status=finalized_invoice.status,
            description=invoice_in.description,
            due_date=due_date
        )
        crud_invoice.create(db, obj_in=db_invoice)

        return finalized_invoice

    async def create_product(self, name: str, description: Optional[str] = None, unit_amount: int = None, currency: str = "usd", recurring_interval: str = "month", metadata: Optional[Dict[str, str]] = None) -> stripe.Product:
        product_data = {"name": name}
        if description:
            product_data["description"] = description
        if metadata:
            product_data["metadata"] = metadata

        if unit_amount is not None:
            product_data["default_price_data"] = {
                "currency": currency,
                "unit_amount": unit_amount,
                "recurring": {"interval": recurring_interval}
            }

        return await self._make_request(stripe.Product.create, **product_data)

    async def get_all_products(self) -> List[Dict[str, Any]]:
        products = await self._make_request(stripe.Product.list, limit=100)
        prices = await self._make_request(stripe.Price.list, limit=100)

        price_map = {}
        for price in prices.data:
            if price.active and price.product not in price_map:
                price_map[price.product] = price

        result = []
        for product in products.data:
            if not product.active:
                continue

            price = price_map.get(product.id)

            result.append({
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "metadata": product.metadata,
                "price": {
                    "id": price.id if price else None,
                    "amount": price.unit_amount / 100 if price else None,
                    "currency": price.currency if price else None,
                    "interval": price.recurring.interval if price and price.recurring else None
                } if price else None
            })

        return result

    async def get_product(self, product_id: str) -> stripe.Product:
        return await self._make_request(stripe.Product.retrieve, product_id)

    async def update_product(self, product_id: str, name: Optional[str] = None, description: Optional[str] = None, active: Optional[bool] = None, metadata: Optional[Dict[str, str]] = None) -> stripe.Product:
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if active is not None:
            update_data["active"] = active
        if metadata is not None:
            update_data["metadata"] = metadata
        return await self._make_request(stripe.Product.modify, product_id, **update_data)

    async def delete_product(self, product_id: str) -> stripe.Product:
        return await self._make_request(stripe.Product.delete, product_id)

    async def get_price(self, price_id: str) -> stripe.Price:
        return await self._make_request(stripe.Price.retrieve, price_id)

    async def update_price(self, price_id: str, active: Optional[bool] = None, metadata: Optional[Dict[str, str]] = None) -> stripe.Price:
        update_data = {}
        if active is not None:
            update_data["active"] = active
        if metadata is not None:
            update_data["metadata"] = metadata
        return await self._make_request(stripe.Price.modify, price_id, expand=["product"], **update_data)

    async def get_all_prices(self) -> List[Dict[str, Any]]:
        prices = await self._make_request(stripe.Price.list, active=True, expand=["data.product"])

        result = []
        for price in prices.data:
            product = price.product

            result.append({
                "id": price.id,
                "amount": price.unit_amount,
                "currency": price.currency,
                "interval": price.recurring.interval if price.recurring else None,
                "product_id": product.id if hasattr(product, 'id') else product,
                "product_name": product.name if hasattr(product, 'name') else None,
                "product_metadata": product.metadata if hasattr(product, 'metadata') else {}
            })

        return result

    async def update_invoice_status(self, invoice_id: str, status: str) -> stripe.Invoice:
        return await self._make_request(stripe.Invoice.modify, invoice_id, status=status)

    async def delete_invoice(self, db: Session, stripe_invoice_id: str) -> stripe.Invoice:
        """Soft delete an invoice by voiding it in Stripe and marking as deleted in DB."""
        db_invoice = crud_invoice.get_by_stripe_invoice_id(db, stripe_invoice_id=stripe_invoice_id)
        if not db_invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")

        try:
            if db_invoice.status == 'draft':
                stripe_invoice = await self._make_request(stripe.Invoice.delete, db_invoice.stripe_invoice_id)
            else:
                stripe_invoice = await self._make_request(stripe.Invoice.void_invoice, db_invoice.stripe_invoice_id)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to void/delete invoice in Stripe: {str(e)}")

        crud_invoice.soft_delete(db, invoice=db_invoice)

        return stripe_invoice

    async def get_school_invoices(self, db: Session, context: UserContext) -> List[SchoolInvoiceSchema]:
        if not context.school:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must be assigned to a school.")

        from app.utils.permission import permission_helper
        if not permission_helper.is_school_admin(context):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only school admins can view school invoices.")

        invoices = crud_invoice.get_multi_by_school(db, school_id=context.school.id)

        enriched_invoices = []
        for invoice in invoices:
            try:
                stripe_invoice = await self._make_request(stripe.Invoice.retrieve, invoice.stripe_invoice_id)
                invoice_pdf_url = getattr(stripe_invoice, 'invoice_pdf', None)
            except Exception as e:
                invoice_pdf_url = None

            invoice_data = {
                "id": invoice.id,
                "school_id": invoice.school_id,
                "stripe_invoice_id": invoice.stripe_invoice_id,
                "amount": invoice.amount,
                "currency": invoice.currency,
                "status": invoice.status,
                "description": invoice.description,
                "due_date": invoice.due_date,
                "invoice_pdf": invoice_pdf_url,
                "created_at": invoice.created_at,
                "updated_at": invoice.updated_at
            }
            enriched_invoices.append(SchoolInvoiceSchema(**invoice_data))

        return enriched_invoices

    async def create_invoice_payment_intent(self, db: Session, invoice_id: int, context: UserContext) -> InvoicePaymentIntentSchema:
        if not context.school:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must be assigned to a school.")

        from app.utils.permission import permission_helper
        if not permission_helper.is_school_admin(context):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only school admins can pay invoices.")

        invoice = crud_invoice.get(db, id=invoice_id)
        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")

        if invoice.school_id != context.school.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invoice does not belong to your school.")

        if invoice.status not in ['open', 'draft']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invoice status '{invoice.status}' is not payable.")

        school_customer = await self._get_or_create_customer_from_school_id(db, school_id=invoice.school_id)

        amount_cents = int(invoice.amount * 100)
        payment_intent = await self._make_request(
            stripe.PaymentIntent.create,
            amount=amount_cents,
            currency=invoice.currency,
            customer=school_customer.stripe_customer_id,
            metadata={
                "invoice_id": str(invoice.id),
                "school_id": str(invoice.school_id),
                "stripe_invoice_id": invoice.stripe_invoice_id
            },
            description=f"Payment for invoice {invoice.stripe_invoice_id}"
        )

        return InvoicePaymentIntentSchema(
            client_secret=payment_intent.client_secret,
            invoice_id=invoice.id,
            amount=invoice.amount,
            currency=invoice.currency
        )

    async def create_invoice_checkout_session(self, db: Session, invoice_id: int, context: UserContext, success_url: str, cancel_url: str) -> CheckoutSession:
        if not context.school:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must be assigned to a school.")

        from app.utils.permission import permission_helper
        if not permission_helper.is_school_admin(context):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only school admins can pay invoices.")

        invoice = crud_invoice.get(db, id=invoice_id)
        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")

        if invoice.school_id != context.school.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invoice does not belong to your school.")

        if invoice.status not in ['open', 'draft']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invoice status '{invoice.status}' is not payable.")

        school_customer = await self._get_or_create_customer_from_school_id(db, school_id=invoice.school_id)

        amount_cents = int(invoice.amount * 100)

        checkout_session = await self._make_request(
            stripe.checkout.Session.create,
            customer=school_customer.stripe_customer_id,
            line_items=[{
                'price_data': {
                    'currency': invoice.currency,
                    'product_data': {
                        'name': f'Invoice Payment - {invoice.stripe_invoice_id}',
                        'description': invoice.description or f'Payment for invoice {invoice.stripe_invoice_id}',
                    },
                    'unit_amount': amount_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "invoice_id": str(invoice.id),
                "school_id": str(invoice.school_id),
                "stripe_invoice_id": invoice.stripe_invoice_id
            }
        )

        return CheckoutSession(id=checkout_session.id, url=checkout_session.url)

    async def handle_invoice_paid_event(self, db: Session, event: stripe.Event):
        invoice = event['data']['object']
        customer_id = invoice['customer']
        stripe_customer = crud_stripe_customer.get_by_stripe_customer_id(db, stripe_customer_id=customer_id)
        if stripe_customer:
            user = crud_user.get(db, id=stripe_customer.user_id)
            if user:
                EmailService.send_email(
                    to_email=user.email,
                    subject="Your payment was successful",
                    template_name="payment_success.html",
                    template_context={'user_name': user.full_name, 'invoice_id': invoice['id']}
                )
                notification_service.create_notification(
                    db,
                    user_id=user.id,
                    message=f"Your payment for invoice {invoice['id']} was successful.",
                    notification_type="payment_success"
                )

    async def handle_checkout_session_completed_event(self, db: Session, event: stripe.Event):
        session = event['data']['object']
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')

        if not customer_id or not subscription_id:
            print(f"Checkout session {session.id} missing customer or subscription ID.")
            return

        stripe_customer = crud_stripe_customer.get_by_stripe_customer_id(db, stripe_customer_id=customer_id)
        if not stripe_customer:
            print(f"Stripe customer {customer_id} not found in DB.")
            return

        user = crud_user.get(db, id=stripe_customer.user_id)
        if not user:
            print(f"User for stripe customer {customer_id} not found in DB.")
            return

        stripe_subscription = await self._make_request(stripe.Subscription.retrieve, subscription_id)

        db_subscription = crud_subscription.get_by_stripe_subscription_id(db, stripe_subscription_id=subscription_id)

        price_ids = [item['price']['id'] for item in stripe_subscription['items']['data']]

        if db_subscription:
            update_data = {
                "status": stripe_subscription.status,
                "stripe_price_id": ",".join(price_ids),
                "current_period_start": datetime.fromtimestamp(stripe_subscription.current_period_start),
                "current_period_end": datetime.fromtimestamp(stripe_subscription.current_period_end),
                "cancel_at_period_end": stripe_subscription.cancel_at_period_end,
            }
            crud_subscription.update(db, db_obj=db_subscription, obj_in=update_data)
        else:
            db_subscription = Subscription(
                user_id=user.id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                stripe_price_id=",".join(price_ids),
                status=stripe_subscription.status,
                current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
                cancel_at_period_end=stripe_subscription.cancel_at_period_end,
            )
            crud_subscription.create(db, obj_in=db_subscription)

        EmailService.send_email(
            to_email=user.email,
            subject="Welcome to QuantCore Learning Hub!",
            template_name="welcome-verify.html",
            template_context={'user_name': user.full_name}
        )
        notification_service.create_notification(
            db,
            user_id=user.id,
            message="Your subscription is now active! Welcome to QuantCore Learning Hub.",
            notification_type="subscription_activated"
        )

    async def handle_subscription_created_event(self, db: Session, event: stripe.Event):
        subscription = event['data']['object']
        customer_id = subscription['customer']
        stripe_customer = crud_stripe_customer.get_by_stripe_customer_id(db, stripe_customer_id=customer_id)
        if stripe_customer:
            user = crud_user.get(db, id=stripe_customer.user_id)
            if user:
                db_subscription = Subscription(
                    user_id=user.id,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=subscription['id'],
                    stripe_price_id=",".join([item['price']['id'] for item in subscription['items']['data']]),
                    status=subscription['status'],
                    current_period_start=datetime.fromtimestamp(subscription['current_period_start']),
                    current_period_end=datetime.fromtimestamp(subscription['current_period_end']),
                    cancel_at_period_end=subscription['cancel_at_period_end'],
                )
                crud_subscription.create(db, obj_in=db_subscription)

    async def handle_subscription_updated_event(self, db: Session, event: stripe.Event):
        subscription = event['data']['object']
        db_subscription = crud_subscription.get_by_stripe_subscription_id(db, stripe_subscription_id=subscription['id'])
        if db_subscription:
            price_ids = [item['price']['id'] for item in subscription['items']['data']]
            update_data = {
                "status": subscription['status'],
                "stripe_price_id": ",".join(price_ids),
                "current_period_start": datetime.fromtimestamp(subscription['current_period_start']),
                "current_period_end": datetime.fromtimestamp(subscription['current_period_end']),
                "cancel_at_period_end": subscription['cancel_at_period_end'],
            }
            crud_subscription.update(db, db_obj=db_subscription, obj_in=update_data)

    async def handle_subscription_deleted_event(self, db: Session, event: stripe.Event):
        subscription = event['data']['object']
        db_subscription = crud_subscription.get_by_stripe_subscription_id(db, stripe_subscription_id=subscription['id'])
        if db_subscription:
            update_data = {
                "status": "canceled"
            }
            crud_subscription.update(db, db_obj=db_subscription, obj_in=update_data)

    async def handle_product_created_event(self, db: Session, event: stripe.Event):
        product = event['data']['object']
        db_product = crud_stripe_product.get_by_stripe_product_id(db, stripe_product_id=product['id'])
        if db_product:
            crud_stripe_product.update(db, db_obj=db_product, obj_in={
                "name": product['name'],
                "description": product.get('description'),
                "active": product['active']
            })
        else:
            product_in = {
                "stripe_product_id": product['id'],
                "name": product['name'],
                "description": product.get('description'),
                "active": product['active']
            }
            crud_stripe_product.create(db, obj_in=product_in)

    async def handle_price_created_event(self, db: Session, event: stripe.Event):
        price = event['data']['object']
        db_price = crud_stripe_price.get_by_stripe_price_id(db, stripe_price_id=price['id'])
        if db_price:
            crud_stripe_price.update(db, db_obj=db_price, obj_in={
                "stripe_product_id": price['product'],
                "unit_amount": price['unit_amount'],
                "currency": price['currency'],
                "recurring_interval": price['recurring']['interval'] if price.get('recurring') else None,
                "active": price['active']
            })
        else:
            price_in = {
                "stripe_price_id": price['id'],
                "stripe_product_id": price['product'],
                "unit_amount": price['unit_amount'],
                "currency": price['currency'],
                "recurring_interval": price['recurring']['interval'] if price.get('recurring') else None,
                "active": price['active']
            }
            crud_stripe_price.create(db, obj_in=price_in)

    async def handle_customer_created_event(self, db: Session, event: stripe.Event):
        customer = event['data']['object']
        user_id = customer.get('metadata', {}).get('user_id')

        if not user_id:
            user = crud_user.get_by_email(db, email=customer['email'])
            if not user:
                print(f"User with email {customer['email']} not found.")
                return
            user_id = user.id
        else:
            user_id = int(user_id)

        db_stripe_customer = crud_stripe_customer.get_by_user_id(db, user_id=user_id)
        if db_stripe_customer:
            if db_stripe_customer.stripe_customer_id != customer['id']:
                crud_stripe_customer.update(db, db_obj=db_stripe_customer, obj_in={"stripe_customer_id": customer['id']})
            return

        customer_in = StripeCustomerCreate(user_id=user_id, stripe_customer_id=customer['id'])
        crud_stripe_customer.create(db, obj_in=customer_in)

stripe_service = StripeService()
