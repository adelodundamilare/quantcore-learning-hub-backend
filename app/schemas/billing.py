from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class StripeCustomerBase(BaseModel):
    pass

class StripeCustomerCreate(StripeCustomerBase):
    pass

class StripeCustomerSchema(StripeCustomerBase):
    id: int
    user_id: int
    stripe_customer_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class SubscriptionBase(BaseModel):
    stripe_price_id: str

class SubscriptionCreate(SubscriptionBase):
    payment_method_id: Optional[str] = None

class SubscriptionSchema(SubscriptionBase):
    id: int
    user_id: int
    stripe_customer_id: str
    stripe_subscription_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PaymentMethodAdd(BaseModel):
    payment_method_id: str

class PaymentMethodSchema(BaseModel):
    id: str
    card_brand: str
    card_last4: str
    exp_month: int
    exp_year: int
    is_default: bool = False

class InvoiceSchema(BaseModel):
    id: str
    amount_due: float
    currency: str
    status: str
    invoice_pdf: Optional[str] = None
    created_at: datetime

class StripeProductBase(BaseModel):
    name: str
    description: Optional[str] = None

class StripeProductCreate(StripeProductBase):
    pass

class StripeProductUpdate(StripeProductBase):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None

class StripeProductSchema(StripeProductBase):
    id: int
    stripe_product_id: str
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class StripePriceBase(BaseModel):
    stripe_product_id: str
    unit_amount: int
    currency: str = "usd"
    recurring_interval: str = "month"

class StripePriceCreate(StripePriceBase):
    pass

class StripePriceUpdate(BaseModel):
    active: Optional[bool] = None

class StripePriceSchema(StripePriceBase):
    id: int
    stripe_price_id: str
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
