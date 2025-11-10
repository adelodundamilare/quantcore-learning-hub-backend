from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class StripeCustomer(Base):
    __tablename__ = "stripe_customers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    stripe_customer_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="stripe_customer")
    subscriptions = relationship("Subscription", back_populates="customer", cascade="all, delete-orphan")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stripe_customer_id = Column(String, ForeignKey("stripe_customers.stripe_customer_id"), nullable=False)
    stripe_subscription_id = Column(String, unique=True, index=True, nullable=False)
    stripe_price_id = Column(String, nullable=False)
    status = Column(String, nullable=False) # e.g., active, canceled, past_due
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="subscriptions")
    customer = relationship("StripeCustomer", back_populates="subscriptions")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    stripe_invoice_id = Column(String, unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="usd")
    status = Column(String, nullable=False)  # draft, open, paid, uncollectible, void
    description = Column(String, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    school = relationship("School", back_populates="invoices")

class StripeProduct(Base):
    __tablename__ = "stripe_products"

    id = Column(Integer, primary_key=True, index=True)
    stripe_product_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    prices = relationship("StripePrice", back_populates="product", cascade="all, delete-orphan")

class StripePrice(Base):
    __tablename__ = "stripe_prices"

    id = Column(Integer, primary_key=True, index=True)
    stripe_price_id = Column(String, unique=True, index=True, nullable=False)
    stripe_product_id = Column(String, ForeignKey("stripe_products.stripe_product_id"), nullable=False)
    unit_amount = Column(Integer, nullable=False) # Amount in cents
    currency = Column(String, nullable=False)
    recurring_interval = Column(String, nullable=True) # e.g., month, year
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    product = relationship("StripeProduct", back_populates="prices")
