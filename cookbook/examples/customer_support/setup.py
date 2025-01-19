from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, inspect, Enum
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase
from datetime import datetime
import enum


def setup_database():
    db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

    engine = create_engine(db_url)

    class Base(DeclarativeBase):
        pass

    class OrderStatus(enum.Enum):
        ORDERED = "ordered"
        DISPATCHED = "dispatched"
        RETURNED = "returned"
        COMPLETED = "completed"
        CANCELLED = "cancelled"

    # Define models
    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        name = Column(String(100))
        email = Column(String(100))
        orders = relationship("Order", back_populates="user")

    class Product(Base):
        __tablename__ = "products"
        id = Column(Integer, primary_key=True)
        name = Column(String(100))
        description = Column(String(500))
        price = Column(Float)
        stock_quantity = Column(Integer, default=100)
        orders = relationship("OrderItem", back_populates="product")

    class Order(Base):
        __tablename__ = "orders"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        order_date = Column(DateTime)
        status = Column(Enum(OrderStatus), default=OrderStatus.ORDERED)
        items = relationship("OrderItem", back_populates="order")
        user = relationship("User", back_populates="orders")

    class OrderItem(Base):
        __tablename__ = "order_items"
        id = Column(Integer, primary_key=True)
        order_id = Column(Integer, ForeignKey("orders.id"))
        product_id = Column(Integer, ForeignKey("products.id"))
        quantity = Column(Integer)
        order = relationship("Order", back_populates="items")
        product = relationship("Product", back_populates="orders")

    # Check if tables exist
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if not all(table in tables for table in ["users", "products", "orders", "order_items"]):
        # Create tables
        Base.metadata.create_all(engine)

        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()

        # Add sample data
        sample_products = [
            Product(name="Laptop", description="High-performance laptop", price=999.99, stock_quantity=50),
            Product(name="Smartphone", description="Latest smartphone model", price=699.99, stock_quantity=100),
            Product(
                name="Headphone", description="Wireless noise-canceling headphones", price=199.99, stock_quantity=200
            ),
        ]
        session.add_all(sample_products)

        # Create sample user
        user = User(name="John Doe", email="john@example.com")
        session.add(user)

        # Create sample order
        order = Order(user=user, order_date=datetime.now(), status=OrderStatus.ORDERED)
        session.add(order)

        # Add order items and update stock
        order_items = [
            OrderItem(order=order, product=sample_products[0], quantity=1),
            OrderItem(order=order, product=sample_products[2], quantity=2),
        ]

        session.add_all(order_items)

        session.commit()
        session.close()

    return engine
