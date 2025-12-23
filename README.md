# Zomato Clone (Tkinter + MySQL)

A desktop-based Zomato Clone built with Python Tkinter and MySQL.
It allows users to browse restaurants, view menus, place orders, write reviews, and simulate payments  — all from a GUI interface.

## Features

#### 🔑 User Authentication

  - Signup with name, email, phone, and password

  - Login with email + password (SHA256 encrypted)

#### 🏬 Restaurant & Menu Management

  - Browse restaurants by city and search by name/cuisine

  - Menu items categorized as Veg / Non-Veg

#### 🛒 Cart & Orders

  - Add/remove items from cart

  - Adjust quantity

  - Place order with multiple items

#### 💳 Payments

  - Choose payment method: Cash / Card / UPI

  - Cash on Delivery option

  - Simulated 95% success rate for Card/UPI payments

  -Tracks paid/unpaid orders

#### 📦 Order Tracking

  - View complete order history

  - Order statuses: PLACED → PREPARING → ON THE WAY → DELIVERED

  - Admin-like control to advance status

#### ⭐ Reviews & Ratings

  - Leave reviews with rating (1–5 stars)

  - Average ratings displayed in restaurant list

  - View past reviews

#### 📊 Database Schema (MySQL)

  - users, restaurants, menu_items, orders, order_items, reviews

  - Automatic database + tables setup

  - Auto-seeds restaurants and menus on first run

### Tech Stack

  - Python (Tkinter for GUI)

  - MySQL (via mysql.connector)

  - Dataclasses & Hashlib for secure user storage

  - Random module for payment simulation

### Setup Instructions

#### 1️⃣ Install Requirements

  - Make sure you have Python 3.x and MySQL installed.

  - pip install mysql-connector-python

#### 2️⃣ Configure Database

  Edit the DBConfig in zomato_clone_code.py if needed:



    host: str = "localhost"
    
    user: str = "root"
    
    password: str = "YOUR_PASSWORD"   # keep your mysql root password here.
    
    database: str = "zomato_clone"

    The app will automatically create the database and tables.

#### 3️⃣ Run the App

  python zomato_clone_code.py

### What I learned from this project


- Database design and SQL query optimization

- Python–MySQL integration

- Backend logic for food ordering workflows

- GUI development with Tkinter

- Real-world application structure and data flow

