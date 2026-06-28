#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, redirect, url_for
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from my_restaurant_setup import Base, MyRestaurant, Menu, CustomerOrder, OrderItems
from datetime import datetime

app = Flask(__name__)

# Database setup
engine = create_engine('sqlite:///my_restaurant_v2.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

def get_session():
    return DBSession()

@app.route('/')
def index():
    """Home page - Restaurant info aur menu dikhaye"""
    session = get_session()
    try:
        restaurant = session.scalars(select(MyRestaurant)).first()
        menu_items = session.scalars(select(Menu)).all()
        
        # Agar data nahi hai toh setup karein
        if not restaurant:
            setup_database(session)
            restaurant = session.scalars(select(MyRestaurant)).first()
            menu_items = session.scalars(select(Menu)).all()
        
        return render_template('index.html', 
                             restaurant=restaurant, 
                             menu_items=menu_items)
    finally:
        session.close()

@app.route('/place_order', methods=['POST'])
def place_order():
    """Naya order place kare"""
    session = get_session()
    try:
        data = request.get_json()
        cust_name = data.get('customer_name')
        table_no = data.get('table_no')
        items_list = data.get('items')  # Format: [{"item_id": 1, "quantity": 2}, ...]
        
        if not all([cust_name, table_no, items_list]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create new order
        new_order = CustomerOrder(
            customer_name=cust_name, 
            table_no=table_no,
            order_time=datetime.now()
        )
        session.add(new_order)
        session.flush()
        
        final_bill = 0.0
        
        # Add items to order
        for item_data in items_list:
            item_id = item_data['item_id']
            qty = item_data['quantity']
            
            menu_item = session.get(Menu, item_id)
            if menu_item:
                order_item = OrderItems(
                    order_id=new_order.id, 
                    menu_id=item_id, 
                    quantity=qty
                )
                session.add(order_item)
                final_bill += (menu_item.price * qty)
        
        # Update total bill
        new_order.total_bill = final_bill
        session.commit()
        
        return jsonify({
            'success': True,
            'order_id': new_order.id,
            'total_bill': final_bill,
            'message': f'Order ID {new_order.id} placed successfully!'
        })
    
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@app.route('/orders')
def show_orders():
    """Saare orders dikhaye"""
    session = get_session()
    try:
        orders = session.scalars(select(CustomerOrder).order_by(CustomerOrder.order_time.desc())).all()
        
        orders_data = []
        for order in orders:
            # Explicitly fetch order items
            order_items_list = session.scalars(
                select(OrderItems).where(OrderItems.order_id == order.id)
            ).all()
            
            items_data = []
            for detail in order_items_list:
                menu_item = session.get(Menu, detail.menu_id)
                if menu_item:
                    items_data.append({
                        'item_name': menu_item.item_name,
                        'quantity': detail.quantity,
                        'price': menu_item.price
                    })
            
            orders_data.append({
                'id': order.id,
                'customer_name': order.customer_name,
                'table_no': order.table_no,
                'order_time': order.order_time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_bill': order.total_bill,
                'items': items_data
            })
        
        return render_template('orders.html', orders=orders_data)
    finally:
        session.close()

@app.route('/api/orders')
def api_orders():
    """API endpoint for orders (JSON format)"""
    session = get_session()
    try:
        orders = session.scalars(select(CustomerOrder).order_by(CustomerOrder.order_time.desc())).all()
        
        orders_data = []
        for order in orders:
            items_data = []
            for detail in order.items:
                items_data.append({
                    'item_name': detail.menu_item.item_name,
                    'quantity': detail.quantity,
                    'price': detail.menu_item.price
                })
            
            orders_data.append({
                'id': order.id,
                'customer_name': order.customer_name,
                'table_no': order.table_no,
                'order_time': order.order_time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_bill': order.total_bill,
                'items': items_data
            })
        
        return jsonify(orders_data)
    finally:
        session.close()

@app.route('/api/menu')
def api_menu():
    """API endpoint for menu items"""
    session = get_session()
    try:
        menu_items = session.scalars(select(Menu)).all()
        menu_data = [{
            'id': item.id,
            'item_name': item.item_name,
            'price': item.price,
            'description': item.description
        } for item in menu_items]
        return jsonify(menu_data)
    finally:
        session.close()

def setup_database(session):
    """Database mein initial data daale"""
    res = MyRestaurant(name="Lahore Night Cafe", address="Gulberg, Lahore")
    session.add(res)
    session.commit()
    
    items = [
        Menu(item_name="Chicken Biryani", price=380.0, description="Spicy Sindhi Biryani with Raita", restaurant_id=res.id),
        Menu(item_name="Cheese Burger", price=450.0, description="Juicy beef patty with extra cheddar", restaurant_id=res.id),
        Menu(item_name="Mint Margarita", price=180.0, description="Ice cold refreshing mint drink", restaurant_id=res.id)
    ]
    session.add_all(items)
    session.commit()

# ==========================================
# ADMIN ROUTES (Add, Update, Delete Menu)
# ==========================================
@app.route('/admin')
@app.route('/admin/menu')
def admin_menu():
    """Admin Dashboard - Jahan se items manage honge"""
    session = get_session()
    try:
        restaurant = session.scalars(select(MyRestaurant)).first()
        menu_items = session.scalars(select(Menu)).all()
        return render_template('admin_menu.html', restaurant=restaurant, menu_items=menu_items)
    finally:
        session.close()

@app.route('/admin/menu/add', methods=['POST'])
def add_item():
    """Naya menu item add karne ke liye"""
    session = get_session()
    try:
        # Form data receive kar rahe hain
        name = request.form.get('item_name')
        price = float(request.form.get('price'))
        desc = request.form.get('description')
        
        restaurant = session.scalars(select(MyRestaurant)).first()
        if not restaurant:
            return "Restaurant not found. Please load index page first.", 400
            
        new_item = Menu(item_name=name, price=price, description=desc, restaurant_id=restaurant.id)
        session.add(new_item)
        session.commit()
        return redirect(url_for('admin_menu'))
    except Exception as e:
        session.rollback()
        return f"Error: {str(e)}", 500
    finally:
        session.close()

@app.route('/admin/menu/update/<int:item_id>', methods=['POST'])
def update_item(item_id):
    """Existing item ko edit/update karne ke liye"""
    session = get_session()
    try:
        item = session.get(Menu, item_id)
        if item:
            item.item_name = request.form.get('item_name')
            item.price = float(request.form.get('price'))
            item.description = request.form.get('description')
            session.commit()
        return redirect(url_for('admin_menu'))
    except Exception as e:
        session.rollback()
        return f"Error: {str(e)}", 500
    finally:
        session.close()

@app.route('/admin/menu/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    """Item delete karne ke liye"""
    session = get_session()
    try:
        item = session.get(Menu, item_id)
        if item:
            session.delete(item)
            session.commit()
        return redirect(url_for('admin_menu'))
    except Exception as e:
        session.rollback()
        return f"Error: {str(e)}", 500
    finally:
        session.close()

if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
