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

class BillingHistoryInvoiceSchema(BaseModel):
    invoice_no: str
    school_name: Optional[str] = None
    school_email: str
    amount: float
    date: datetime
    payment_method: Optional[str] = None
    status: str