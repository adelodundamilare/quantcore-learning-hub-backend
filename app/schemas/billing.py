from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Union
from datetime import datetime
from enum import Enum

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
    unit_amount: int
    currency: str = "usd"
    recurring_interval: str = "month"
    metadata: Optional[dict] = None

class StripeProductUpdate(StripeProductBase):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    metadata: Optional[dict] = None

class StripeProductSchema(StripeProductBase):
    id: str
    active: bool
    created: datetime
    updated: datetime

    model_config = ConfigDict(from_attributes=True)



class StripePriceUpdate(BaseModel):
    active: Optional[bool] = None
    metadata: Optional[dict] = None


class StripePriceRecurring(BaseModel):
    interval: str

class StripePriceSchema(BaseModel):
    id: str
    active: bool
    currency: str
    unit_amount: int
    product: StripeProductSchema
    recurring: Optional[StripePriceRecurring] = None
    created: datetime
    metadata: Optional[dict] = None

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

class BillingReportSchema(BaseModel):
    total_revenue: float
    total_active_subscriptions: int
    number_of_schools: int

class TimeseriesDataPoint(BaseModel):
    period: str
    revenue: float
    transactions: int

class TransactionTimeseriesReport(BaseModel):
    data: List[TimeseriesDataPoint]

class InvoiceStatusEnum(str, Enum):
    draft = "draft"
    open = "open"
    paid = "paid"
    uncollectible = "uncollectible"
    void = "void"

class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatusEnum

class SubscriptionDetailSchema(BaseModel):
    start_date: datetime
    end_date: datetime
    plan_name: str
    price: float
    payment_method: str
    invoice_no: str
    status: str


class SubscriptionAutoRenew(BaseModel):
    auto_renew: bool


class PortalSession(BaseModel):
    id: str
    url: str
