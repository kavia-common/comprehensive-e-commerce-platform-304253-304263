"""
SQLAlchemy ORM models reflecting the existing ecommerce_database schema.

Important:
- These mappings assume the schema already exists (created/seeded by ecommerce_database).
- We do not attempt to create or migrate schema from this service.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import CHAR, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class TimestampMixin:
    """Common timestamp columns in the schema."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base, TimestampMixin):
    """users table."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    # NOTE: In DB this is citext; mapping as Text preserves values and works fine for queries.
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    full_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )
    addresses: Mapped[List["Address"]] = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    carts: Mapped[List["Cart"]] = relationship("Cart", back_populates="user")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")


class Role(Base, TimestampMixin):
    """roles table."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    users: Mapped[List[User]] = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
        lazy="selectin",
    )


class UserRole(Base):
    """user_roles join table."""

    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Category(Base, TimestampMixin):
    """categories table."""

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    parent: Mapped[Optional["Category"]] = relationship("Category", remote_side="Category.id", backref="children")

    products: Mapped[List["Product"]] = relationship(
        "Product",
        secondary="product_categories",
        back_populates="categories",
        lazy="selectin",
    )

    __table_args__ = (UniqueConstraint("parent_id", "name", name="categories_parent_id_name_key"),)


class Product(Base, TimestampMixin):
    """products table."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    sku: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    inventory: Mapped[Optional["Inventory"]] = relationship("Inventory", back_populates="product", uselist=False)
    categories: Mapped[List[Category]] = relationship(
        "Category",
        secondary="product_categories",
        back_populates="products",
        lazy="selectin",
    )

    __table_args__ = (CheckConstraint("price_cents >= 0", name="products_price_cents_check"),)


class ProductCategory(Base):
    """product_categories join table."""

    __tablename__ = "product_categories"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Inventory(Base):
    """inventory table."""

    __tablename__ = "inventory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True)

    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product: Mapped[Product] = relationship("Product", back_populates="inventory")

    __table_args__ = (
        CheckConstraint("quantity_on_hand >= 0", name="inventory_quantity_on_hand_check"),
        CheckConstraint("quantity_reserved >= 0", name="inventory_quantity_reserved_check"),
        CheckConstraint("reorder_level >= 0", name="inventory_reorder_level_check"),
    )


class Cart(Base, TimestampMixin):
    """carts table."""

    __tablename__ = "carts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")

    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[Optional[User]] = relationship("User", back_populates="carts")
    items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status in ('active','ordered','abandoned')", name="carts_status_check"),
    )


class CartItem(Base, TimestampMixin):
    """cart_items table."""

    __tablename__ = "cart_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    cart_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    cart: Mapped[Cart] = relationship("Cart", back_populates="items")
    product: Mapped[Product] = relationship("Product")

    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="cart_items_cart_id_product_id_key"),
        CheckConstraint("quantity > 0", name="cart_items_quantity_check"),
        CheckConstraint("unit_price_cents >= 0", name="cart_items_unit_price_cents_check"),
    )


class Address(Base, TimestampMixin):
    """addresses table."""

    __tablename__ = "addresses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recipient_name: Mapped[str] = mapped_column(Text, nullable=False)

    line1: Mapped[str] = mapped_column(Text, nullable=False)
    line2: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    city: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    postal_code: Mapped[str] = mapped_column(Text, nullable=False)
    country_code: Mapped[str] = mapped_column(CHAR(2), nullable=False)

    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_default_shipping: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_default_billing: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    user: Mapped[User] = relationship("User", back_populates="addresses")

    __table_args__ = (
        # These are partial unique indexes in Postgres; SQLAlchemy can't fully express
        # the WHERE predicate without dialect-specific Index constructs, so we omit them.
        # The DB enforces them already.
        (),
    )


class Order(Base, TimestampMixin):
    """orders table."""

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cart_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("carts.id", ondelete="SET NULL"), nullable=True, unique=True)

    order_number: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")

    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default="USD")

    subtotal_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    shipping_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tax_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    discount_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    shipping_address_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("addresses.id", ondelete="SET NULL"), nullable=True)
    billing_address_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("addresses.id", ondelete="SET NULL"), nullable=True)

    placed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[Optional[User]] = relationship("User", back_populates="orders")
    cart: Mapped[Optional[Cart]] = relationship("Cart")

    shipping_address: Mapped[Optional[Address]] = relationship("Address", foreign_keys=[shipping_address_id])
    billing_address: Mapped[Optional[Address]] = relationship("Address", foreign_keys=[billing_address_id])

    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status in ('pending','paid','fulfilled','cancelled','refunded')",
            name="orders_status_check",
        ),
        CheckConstraint("subtotal_cents >= 0", name="orders_subtotal_cents_check"),
        CheckConstraint("shipping_cents >= 0", name="orders_shipping_cents_check"),
        CheckConstraint("tax_cents >= 0", name="orders_tax_cents_check"),
        CheckConstraint("discount_cents >= 0", name="orders_discount_cents_check"),
        CheckConstraint("total_cents >= 0", name="orders_total_cents_check"),
    )


class OrderItem(Base):
    """order_items table."""

    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)

    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)

    sku: Mapped[str] = mapped_column(Text, nullable=False)
    product_name: Mapped[str] = mapped_column(Text, nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order: Mapped[Order] = relationship("Order", back_populates="items")
    product: Mapped[Optional[Product]] = relationship("Product")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="order_items_quantity_check"),
        CheckConstraint("unit_price_cents >= 0", name="order_items_unit_price_cents_check"),
        CheckConstraint("total_price_cents >= 0", name="order_items_total_price_cents_check"),
    )


class Payment(Base, TimestampMixin):
    """payments table."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)

    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_payment_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")

    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default="USD")

    idempotency_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True, unique=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    order: Mapped[Order] = relationship("Order", back_populates="payments")

    __table_args__ = (
        UniqueConstraint("provider", "provider_payment_id", name="payments_provider_provider_payment_id_key"),
        CheckConstraint(
            "status in ('pending','authorized','captured','failed','refunded','cancelled')",
            name="payments_status_check",
        ),
        CheckConstraint("amount_cents >= 0", name="payments_amount_cents_check"),
    )
