from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

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
    StripePriceCreate,
    StripePriceUpdate,
    StripePriceSchema,
    BillingHistoryInvoiceSchema
)
from app.core.constants import RoleEnum
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
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    if not context.user.stripe_customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stripe customer not found for this user.")
    
    customer = await stripe_service.get_customer(context.user.stripe_customer.stripe_customer_id)
    return APIResponse(message="Stripe customer retrieved successfully", data=customer)

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
    invoices = await stripe_service.get_invoices(user=context.user)
    return APIResponse(message="Invoices retrieved successfully", data=invoices)

@router.post("/admin/products", response_model=APIResponse[StripeProductSchema], status_code=status.HTTP_201_CREATED, dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def create_stripe_product(
    product_in: StripeProductCreate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    product = await stripe_service.create_product(product_in.name, product_in.description)
    return APIResponse(message="Stripe product created successfully", data=product)

@router.get("/admin/products", response_model=APIResponse[List[StripeProductSchema]], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def get_all_stripe_products(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    products = await stripe_service.get_all_products()
    return APIResponse(message="Stripe products retrieved successfully", data=products)

@router.get("/admin/products/{product_id}", response_model=APIResponse[StripeProductSchema], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
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
    product = await stripe_service.update_product(product_id, product_in.name, product_in.description, product_in.active)
    return APIResponse(message="Stripe product updated successfully", data=product)

@router.delete("/admin/products/{product_id}", response_model=APIResponse[StripeProductSchema], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def delete_stripe_product(
    product_id: str,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    product = await stripe_service.delete_product(product_id)
    return APIResponse(message="Stripe product deleted successfully", data=product)

@router.post("/admin/prices", response_model=APIResponse[StripePriceSchema], status_code=status.HTTP_201_CREATED, dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def create_stripe_price(
    price_in: StripePriceCreate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    price = await stripe_service.create_price(price_in.stripe_product_id, price_in.unit_amount, price_in.currency, price_in.recurring_interval)
    return APIResponse(message="Stripe price created successfully", data=price)

@router.get("/admin/prices", response_model=APIResponse[List[StripePriceSchema]], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def get_all_stripe_prices(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    prices = await stripe_service.get_all_prices()
    return APIResponse(message="Stripe prices retrieved successfully", data=prices)

@router.get("/admin/prices/{price_id}", response_model=APIResponse[StripePriceSchema], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
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
    price = await stripe_service.update_price(price_id, price_in.active)
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
    school_customer = crud_stripe_customer.get_by_user_id(db, user_id=invoice_in.school_id)
    if not school_customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stripe customer not found for this school.")

    invoice = await stripe_service.create_invoice(
        stripe_customer_id=school_customer.stripe_customer_id,
        amount=invoice_in.amount,
        currency=invoice_in.currency,
        description=invoice_in.description
    )
    return APIResponse(message="Invoice created successfully", data=invoice)
