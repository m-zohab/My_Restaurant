from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class MyRestaurant(Base):
    __tablename__ = 'my_restaurant'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    
    # Relationship with Menu
    menu_items = relationship("Menu", back_populates="restaurant")

class Menu(Base):
    __tablename__ = 'menu'
    
    id = Column(Integer, primary_key=True)
    item_name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String(300))
    restaurant_id = Column(Integer, ForeignKey('my_restaurant.id'))
    
    # Relationships
    restaurant = relationship("MyRestaurant", back_populates="menu_items")
    order_items = relationship("OrderItems", back_populates="menu_item")

class CustomerOrder(Base):
    __tablename__ = 'customer_order'
    
    id = Column(Integer, primary_key=True)
    customer_name = Column(String(100), nullable=False)
    table_no = Column(Integer, nullable=False)
    order_time = Column(DateTime, default=datetime.now)
    total_bill = Column(Float, default=0.0)
    
    # Relationship with OrderItems - YEH IMPORTANT HAI
    items = relationship("OrderItems", back_populates="order")

class OrderItems(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('customer_order.id'))
    menu_id = Column(Integer, ForeignKey('menu.id'))
    quantity = Column(Integer, nullable=False)
    
    # Relationships
    order = relationship("CustomerOrder", back_populates="items")
    menu_item = relationship("Menu", back_populates="order_items")

if __name__ == '__main__':
    engine = create_engine('sqlite:///my_restaurant_v2.db')
    Base.metadata.create_all(engine)
    print("✅ Tables created successfully!")