from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import datetime

class StripeCustomerBase(BaseModel):
    pass

class StripeCustomerCreate(StripeCustomerBase):
    user_id: int
    stripe_customer_id: str

class StripeCustomerSchema(StripeCustomerBase):
    id: int
    user_id: int
    stripe_customer_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class SubscriptionBase(BaseModel):
    stripe_price_ids: List[str]


class SubscriptionCreate(SubscriptionBase):
    payment_method_id: Optional[str] = None


class SubscriptionSchema(BaseModel):
    id: int
    user_id: int
    stripe_customer_id: str
    stripe_subscription_id: str
    stripe_price_ids: List[str] = Field(validation_alias='stripe_price_id')
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator('stripe_price_ids', mode='before')
    @classmethod
    def split_string(cls, v):
        if isinstance(v, str):
            return v.split(',')
        return v

class PaymentMethodAdd(BaseModel):
    payment_method_id: str

class CardDetails(BaseModel):
    brand: str
    last4: str
    exp_month: int
    exp_year: int

class PaymentMethodSchema(BaseModel):
    id: str
    card: CardDetails

class InvoiceSchema(BaseModel):
    id: str
    amount_due: int
    currency: str
    status: str
    invoice_pdf: Optional[str] = None
    created: datetime

class InvoiceCreate(BaseModel):
    school_id: int
    amount: float
    description: Optional[str] = None
    currency: str = "usd"

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
    id: str
    active: bool
    created: datetime
    updated: datetime

    model_config = ConfigDict(from_attributes=True)


class StripePriceCreate(BaseModel):
    stripe_product_id: str
    unit_amount: int
    currency: str = "usd"
    recurring_interval: str = "month"


class StripePriceUpdate(BaseModel):
    active: Optional[bool] = None


class StripePriceRecurring(BaseModel):
    interval: str

class StripePriceSchema(BaseModel):
    id: str
    active: bool
    currency: str
    unit_amount: int
    product: str
    recurring: Optional[StripePriceRecurring] = None
    created: datetime

    model_config = ConfigDict(from_attributes=True)

class BillingHistoryInvoiceSchema(BaseModel):
    invoice_no: str
    school_name: Optional[str] = None
    school_email: str
    amount: float
    date: datetime
    payment_method: Optional[str] = None
    status: str

class CheckoutSessionCreate(BaseModel):
    price_ids: List[str]
    success_url: str
    cancel_url: str

class CheckoutSession(BaseModel):
    id: str
    url: Optional[str] = None
