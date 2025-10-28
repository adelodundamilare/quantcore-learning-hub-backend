from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional

from app.schemas.response import APIResponse
from app.schemas.user import UserContext
from app.utils import deps
from app.services.stripe import stripe_service
from app.schemas.billing import (
    StripeCustomerSchema,
    SubscriptionCreate,
    SubscriptionSchema,
    PaymentMethodAdd,
    PaymentMethodSchema,
    InvoiceSchema,
    InvoiceCreate,
    StripeProductCreate,
    StripeProductUpdate,
    StripeProductSchema,
    StripePriceUpdate,
    StripePriceSchema,
    BillingHistoryInvoiceSchema,
    CheckoutSessionCreate,
    CheckoutSession,
    BillingReportSchema,
    TransactionTimeseriesReport
)
from app.core.constants import RoleEnum, TimePeriod
from app.models.billing import StripeCustomer
from app.crud.stripe_customer import stripe_customer as crud_stripe_customer

router = APIRouter()

@router.post("/customer", response_model=APIResponse[StripeCustomerSchema], status_code=status.HTTP_201_CREATED)
async def create_stripe_customer(
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    if context.user.stripe_customer:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stripe customer already exists for this user.")

    customer = await stripe_service.create_customer(db, context.user)
    return APIResponse(message="Stripe customer created successfully", data=customer)

@router.get("/customer", response_model=APIResponse[StripeCustomerSchema])
async def get_stripe_customer(
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    if not context.user.stripe_customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stripe customer not found for this user.")

    return APIResponse(message="Stripe customer retrieved successfully", data=context.user.stripe_customer)

@router.post("/setup-intent", response_model=APIResponse[dict])
async def create_setup_intent(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    if not context.user.stripe_customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stripe customer not found. Please create one first.")

    setup_intent = await stripe_service.create_setup_intent(context.user.stripe_customer.stripe_customer_id)
    return APIResponse(message="SetupIntent created successfully", data={"client_secret": setup_intent.client_secret})

@router.post("/payment-methods", response_model=APIResponse[PaymentMethodSchema], status_code=status.HTTP_201_CREATED)
async def add_payment_method(
    payment_method_in: PaymentMethodAdd,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    if not context.user.stripe_customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stripe customer not found. Please create one first.")

    payment_method = await stripe_service.attach_payment_method(
        context.user.stripe_customer.stripe_customer_id,
        payment_method_in.payment_method_id
    )
    return APIResponse(message="Payment method added successfully", data=payment_method)

@router.get("/payment-methods", response_model=APIResponse[List[PaymentMethodSchema]])
async def get_payment_methods(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    if not context.user.stripe_customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stripe customer not found for this user.")

    payment_methods = await stripe_service.get_payment_methods(context.user.stripe_customer.stripe_customer_id)
    return APIResponse(message="Payment methods retrieved successfully", data=payment_methods)

@router.post("/subscriptions", response_model=APIResponse[SubscriptionSchema], status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_in: SubscriptionCreate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    subscription = await stripe_service.create_subscription(
        db=db,
        user=context.user,
        price_ids=subscription_in.stripe_price_ids,
        payment_method_id=subscription_in.payment_method_id
    )
    return APIResponse(message="Subscription created successfully", data=subscription)

@router.get("/subscriptions", response_model=APIResponse[List[SubscriptionSchema]])
async def get_subscriptions(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    subscriptions = await stripe_service.get_subscriptions(db=db, user=context.user)
    return APIResponse(message="Subscriptions retrieved successfully", data=subscriptions)

@router.put("/subscriptions/{subscription_id}", response_model=APIResponse[SubscriptionSchema])
async def update_subscription(
    subscription_id: str,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Subscription update not yet implemented.")

@router.delete("/subscriptions/{subscription_id}", response_model=APIResponse[SubscriptionSchema])
async def cancel_subscription(
    subscription_id: str,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    subscription = await stripe_service.cancel_subscription(db=db, subscription_id=subscription_id)
    return APIResponse(message="Subscription cancelled successfully", data=subscription)

@router.get("/invoices", response_model=APIResponse[List[BillingHistoryInvoiceSchema]])
async def get_invoices(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    invoices = await stripe_service.get_invoices(db, user=context.user)
    return APIResponse(message="Invoices retrieved successfully", data=invoices)

@router.post("/create-checkout-session", response_model=APIResponse[CheckoutSession])
async def create_checkout_session(
    session_in: CheckoutSessionCreate,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    """
    Create a Stripe Checkout session for subscribing to a plan.
    """
    checkout_session = await stripe_service.create_checkout_session(
        db=db,
        user=context.user,
        price_ids=session_in.price_ids,
        success_url=session_in.success_url,
        cancel_url=session_in.cancel_url
    )
    return APIResponse(message="Checkout session created successfully", data=checkout_session)

@router.post("/admin/products", response_model=APIResponse[StripeProductSchema], status_code=status.HTTP_201_CREATED, dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def create_stripe_product(
    product_in: StripeProductCreate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    product = await stripe_service.create_product(product_in.name, product_in.description, product_in.unit_amount, product_in.currency, product_in.recurring_interval, product_in.metadata)
    return APIResponse(message="Stripe product created successfully", data=product)

@router.get("/admin/billing-report", response_model=APIResponse[BillingReportSchema], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def get_billing_report(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    """
    Retrieve a billing report for administrators, including total revenue, active subscriptions, and number of schools.
    """
    report = await stripe_service.get_billing_report(db)
    return APIResponse(message="Billing report retrieved successfully", data=report)

@router.get("/admin/transactions/timeseries", response_model=APIResponse[TransactionTimeseriesReport], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def get_transaction_timeseries(
    start_date: Optional[datetime] = Query(None, description="Start date for filtering transactions"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering transactions"),
    period: TimePeriod = Query(..., description="Time period for aggregation (year, month, or week)"),
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    """
    Retrieve timeseries transaction data for administrators, filterable by year, month, or week.
    """
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date"
        )

    if not start_date and not end_date:
        now = datetime.now()
        if period == TimePeriod.YEAR:
            start_date = datetime(now.year, 1, 1)
        elif period == TimePeriod.MONTH:
            start_date = datetime(now.year, 1, 1)
        elif period == TimePeriod.WEEK:
            start_date = now - timedelta(days=90)

    report = await stripe_service.get_transaction_timeseries(db, period,
        start_date=start_date,
        end_date=end_date)
    return APIResponse(message="Transaction timeseries report retrieved successfully", data=report)

@router.get("/products", response_model=APIResponse[List[Dict[str, Any]]])
async def get_all_stripe_products(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    products = await stripe_service.get_all_products()
    return APIResponse(message="Stripe products retrieved successfully", data=products)

@router.get("/products/{product_id}", response_model=APIResponse[StripeProductSchema])
async def get_stripe_product(
    product_id: str,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    product = await stripe_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return APIResponse(message="Stripe product retrieved successfully", data=product)

@router.put("/admin/products/{product_id}", response_model=APIResponse[StripeProductSchema], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def update_stripe_product(
    product_id: str,
    product_in: StripeProductUpdate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    product = await stripe_service.update_product(product_id, product_in.name, product_in.description, product_in.active, product_in.metadata)
    return APIResponse(message="Stripe product updated successfully", data=product)

@router.delete("/admin/products/{product_id}", response_model=APIResponse[StripeProductSchema], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def delete_stripe_product(
    product_id: str,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    product = await stripe_service.delete_product(product_id)
    return APIResponse(message="Stripe product deleted successfully", data=product)

@router.get("/prices", response_model=APIResponse[List[Dict[str, Any]]])
async def get_all_stripe_prices(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    prices = await stripe_service.get_all_prices()
    return APIResponse(message="Stripe prices retrieved successfully", data=prices)

@router.get("/prices/{price_id}", response_model=APIResponse[StripePriceSchema])
async def get_stripe_price(
    price_id: str,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    price = await stripe_service.get_price(price_id)
    if not price:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price not found.")
    return APIResponse(message="Stripe price retrieved successfully", data=price)

@router.put("/admin/prices/{price_id}", response_model=APIResponse[StripePriceSchema], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def update_stripe_price(
    price_id: str,
    price_in: StripePriceUpdate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    price = await stripe_service.update_price(price_id, price_in.active, price_in.metadata)
    return APIResponse(message="Stripe price updated successfully", data=price)

@router.delete("/admin/prices/{price_id}", response_model=APIResponse[StripePriceSchema], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def delete_stripe_price(
    price_id: str,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    price = await stripe_service.update_price(price_id, active=False)
    return APIResponse(message="Stripe price deactivated successfully", data=price)

@router.post("/admin/invoices", response_model=APIResponse[InvoiceSchema], status_code=status.HTTP_201_CREATED, dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def create_invoice_for_school(
    invoice_in: InvoiceCreate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    invoice = await stripe_service.create_invoice(
        db=db,
        invoice_in=invoice_in,
    )
    return APIResponse(message="Invoice created successfully", data=invoice)