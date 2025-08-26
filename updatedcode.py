# zomato_clone_full.py
# Full Tkinter + MySQL Zomato clone with:
# - veg & non_veg columns
# - reviews & ratings
# - order status updates
# - payment simulation (CASH / CARD / UPI)

import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error
import hashlib
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
import random

# -----------------------
# Config & Database Layer
# -----------------------
@dataclass
class DBConfig:
    host: str = "localhost"
    user: str = "root"
    password: str = "SW2003@th#7"          # <-- set your MySQL password
    database: str = "zomato_clone"

class Database:
    def __init__(self, cfg: DBConfig):
        self.cfg = cfg
        self.conn = None
        self.ensure_connection()
        self.setup_schema()
        self.seed_data()

    def ensure_connection(self):
        try:
            # connect to server, create DB if missing
            self.conn = mysql.connector.connect(
                host=self.cfg.host,
                user=self.cfg.user,
                password=self.cfg.password,
            )
            self.conn.autocommit = True
            cur = self.conn.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS {self.cfg.database}")
            cur.close()
            self.conn.close()
            # reconnect to the specific database
            self.conn = mysql.connector.connect(
                host=self.cfg.host,
                user=self.cfg.user,
                password=self.cfg.password,
                database=self.cfg.database,
                autocommit=True,
            )
        except Error as e:
            messagebox.showerror("DB Error", f"Could not connect: {e}")
            raise

    def execute(self, query: str, params: Tuple = ()):
        try:
            cur = self.conn.cursor()
            cur.execute(query, params)
            last_id = cur.lastrowid
            cur.close()
            return last_id
        except Error as e:
            # show error if GUI available, else print
            try:
                messagebox.showerror("DB Error", f"Query failed: {e}\n{query}")
            except Exception:
                print("DB Error:", e, query)
            return None

    def fetchall(self, query: str, params: Tuple = ()):
        try:
            cur = self.conn.cursor(dictionary=True)
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            return rows
        except Error as e:
            try:
                messagebox.showerror("DB Error", f"Query failed: {e}\n{query}")
            except Exception:
                print("DB Error:", e, query)
            return []

    def fetchone(self, query: str, params: Tuple = ()):
        rows = self.fetchall(query, params)
        return rows[0] if rows else None

    def setup_schema(self):
        ddl = [
            # Users
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) UNIQUE NOT NULL,
                phone VARCHAR(20),
                password_hash VARCHAR(64) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """,
            # Restaurants
            """
            CREATE TABLE IF NOT EXISTS restaurants (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                cuisine VARCHAR(100),
                rating DECIMAL(2,1) DEFAULT 4.0,
                city VARCHAR(100) DEFAULT 'Hyderabad'
            ) ENGINE=InnoDB;
            """,
            # Menu Items (with veg and non_veg)
            """
            CREATE TABLE IF NOT EXISTS menu_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                restaurant_id INT NOT NULL,
                name VARCHAR(150) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                veg TINYINT(1) DEFAULT 1,
                non_veg TINYINT(1) DEFAULT 0,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB;
            """,
            # Orders (with payment fields)
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                restaurant_id INT NOT NULL,
                total DECIMAL(10,2) NOT NULL,
                status VARCHAR(20) DEFAULT 'PLACED',
                payment_method VARCHAR(20) DEFAULT 'CASH',
                paid TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
            ) ENGINE=InnoDB;
            """,
            # Order Items
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT NOT NULL,
                menu_item_id INT NOT NULL,
                quantity INT NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
            ) ENGINE=InnoDB;
            """,
            # Reviews
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                restaurant_id INT NOT NULL,
                rating TINYINT NOT NULL,
                review_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
            """,
        ]
        for stmt in ddl:
            self.execute(stmt)

        # Compatibility helper: check INFORMATION_SCHEMA and add missing columns
        def ensure_column_exists(table: str, column: str, definition: str):
            q = """
            SELECT COUNT(*) AS cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
            """
            res = self.fetchone(q, (self.cfg.database, table, column))
            if not res or res.get('cnt', 0) == 0:
                # add column (definition already contains '<col> <type> ...')
                self.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")

        # Ensure non_veg & payment columns exist for older DBs
        ensure_column_exists('menu_items', 'non_veg', "non_veg TINYINT(1) DEFAULT 0")
        ensure_column_exists('orders', 'payment_method', "payment_method VARCHAR(20) DEFAULT 'CASH'")
        ensure_column_exists('orders', 'paid', "paid TINYINT(1) DEFAULT 0")

    def seed_data(self):
        # Seed restaurants if empty
        count = self.fetchone("SELECT COUNT(*) AS c FROM restaurants")
        if count and count["c"] == 0:
            restaurants = [
                ("Biryani Bliss", "Hyderabadi", 4.5, "Hyderabad"),
                ("Tiffin Tales", "South Indian", 4.2, "Hyderabad"),
                ("Sushi Street", "Japanese", 4.6, "Bengaluru"),
                ("Pizza Plaza", "Italian", 4.0, "Chennai"),
            ]
            for r in restaurants:
                self.execute(
                    "INSERT INTO restaurants(name,cuisine,rating,city) VALUES(%s,%s,%s,%s)",
                    r,
                )
        # Seed menu items if empty
        count = self.fetchone("SELECT COUNT(*) AS c FROM menu_items")
        if count and count["c"] == 0:
            # Fetch restaurant ids
            rs = self.fetchall("SELECT id,name FROM restaurants")
            rid = {r["name"]: r["id"] for r in rs}
            items = [
                # Biryani Bliss
                (rid["Biryani Bliss"], "Chicken Biryani", 249.00, 0, 1),
                (rid["Biryani Bliss"], "Mutton Biryani", 329.00, 0, 1),
                (rid["Biryani Bliss"], "Veg Biryani", 199.00, 1, 0),
                # Tiffin Tales
                (rid["Tiffin Tales"], "Idli Sambar", 60.00, 1, 0),
                (rid["Tiffin Tales"], "Masala Dosa", 90.00, 1, 0),
                (rid["Tiffin Tales"], "Upma", 70.00, 1, 0),
                # Sushi Street
                (rid["Sushi Street"], "California Roll", 420.00, 0, 1),
                (rid["Sushi Street"], "Veg Tempura Roll", 380.00, 1, 0),
                # Pizza Plaza
                (rid["Pizza Plaza"], "Margherita", 249.00, 1, 0),
                (rid["Pizza Plaza"], "Farmhouse", 329.00, 1, 0),
                (rid["Pizza Plaza"], "Pepperoni", 349.00, 0, 1),
            ]
            for it in items:
                self.execute(
                    "INSERT INTO menu_items(restaurant_id,name,price,veg,non_veg) VALUES(%s,%s,%s,%s,%s)",
                    it,
                )

    # ==== Domain queries ====
    def create_user(self, name: str, email: str, phone: str, pwd_hash: str) -> Optional[int]:
        return self.execute(
            "INSERT INTO users(name,email,phone,password_hash) VALUES(%s,%s,%s,%s)",
            (name, email, phone, pwd_hash),
        )

    def find_user_by_email(self, email: str):
        return self.fetchone("SELECT * FROM users WHERE email=%s", (email,))

    def list_restaurants(self, search: str = "", city: str = ""):
        sql = (
            "SELECT r.id, r.name, r.cuisine, r.city, r.rating AS base_rating, "
            "COALESCE(ROUND(AVG(rv.rating),1), r.rating) AS avg_rating, COUNT(rv.id) AS review_count "
            "FROM restaurants r LEFT JOIN reviews rv ON rv.restaurant_id=r.id WHERE 1=1"
        )
        params: List = []
        if search:
            sql += " AND (r.name LIKE %s OR r.cuisine LIKE %s)"
            like = f"%{search}%"
            params += [like, like]
        if city:
            sql += " AND r.city=%s"
            params.append(city)
        sql += " GROUP BY r.id ORDER BY avg_rating DESC, r.name ASC"
        return self.fetchall(sql, tuple(params))

    def list_menu(self, restaurant_id: int):
        return self.fetchall(
            "SELECT * FROM menu_items WHERE restaurant_id=%s ORDER BY veg DESC, name",
            (restaurant_id,),
        )

    def place_order(self, user_id: int, restaurant_id: int, items: List[Tuple[int, int, float]], payment_method: str = 'CASH', paid: int = 0):
        # items: list of (menu_item_id, qty, price)
        total = sum(q * p for _, q, p in items)
        oid = self.execute(
            "INSERT INTO orders(user_id,restaurant_id,total,status,payment_method,paid) VALUES(%s,%s,%s,%s,%s,%s)",
            (user_id, restaurant_id, total, "PLACED", payment_method, paid),
        )
        if not oid:
            return None
        for mid, qty, price in items:
            self.execute(
                "INSERT INTO order_items(order_id,menu_item_id,quantity,price) VALUES(%s,%s,%s,%s)",
                (oid, mid, qty, price),
            )
        return oid

    def fetch_order_history(self, user_id: int):
        return self.fetchall(
            """
            SELECT o.id, o.total, o.status, o.created_at, r.name AS restaurant, o.payment_method, o.paid
            FROM orders o
            JOIN restaurants r ON r.id=o.restaurant_id
            WHERE o.user_id=%s
            ORDER BY o.created_at DESC
            """,
            (user_id,),
        )

    def get_order(self, order_id: int):
        return self.fetchone("SELECT * FROM orders WHERE id=%s", (order_id,))

    def update_order_status(self, order_id: int, status: str):
        return self.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))

    # ==== Reviews ====
    def create_review(self, user_id: int, restaurant_id: int, rating: int, review_text: str) -> Optional[int]:
        rating = max(1, min(5, int(rating)))
        return self.execute(
            "INSERT INTO reviews(user_id,restaurant_id,rating,review_text) VALUES(%s,%s,%s,%s)",
            (user_id, restaurant_id, rating, review_text),
        )

    def get_reviews(self, restaurant_id: int):
        return self.fetchall(
            "SELECT rv.*, u.name AS reviewer FROM reviews rv JOIN users u ON u.id=rv.user_id WHERE rv.restaurant_id=%s ORDER BY rv.created_at DESC",
            (restaurant_id,),
        )

# -----------------------
# Utilities
# -----------------------
def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

# -----------------------
# Tkinter UI
# -----------------------
class ZomatoApp(tk.Tk):
    def __init__(self, db: Database):
        super().__init__()
        self.title("Zomato Clone — Tkinter + MySQL")
        self.geometry("1000x650")
        self.db = db
        self.current_user: Optional[dict] = None
        self.cart: Dict[int, Dict] = {}  # menu_item_id -> {id,name,price,qty}
        self.current_restaurant: Optional[dict] = None

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except:
            pass

        self.create_navbar()
        self.create_frames()
        self.show_auth()  # show auth on start

    # ---- Navigation ----
    def create_navbar(self):
        self.nav = ttk.Frame(self)
        self.nav.pack(side=tk.TOP, fill=tk.X)

        self.brand = ttk.Label(self.nav, text="Zomato Clone", font=("Segoe UI", 16, "bold"))
        self.brand.pack(side=tk.LEFT, padx=12, pady=8)

        self.city_var = tk.StringVar(value="")
        self.search_var = tk.StringVar()
        self.entry_search = ttk.Entry(self.nav, textvariable=self.search_var, width=30)
        self.entry_search.pack(side=tk.LEFT, padx=8)
        ttk.Button(self.nav, text="Search", command=self.refresh_restaurants).pack(side=tk.LEFT, padx=4)

        ttk.Label(self.nav, text="City:").pack(side=tk.LEFT, padx=(16, 4))
        self.city_combo = ttk.Combobox(self.nav, width=14, textvariable=self.city_var, state="readonly")
        self.city_combo["values"] = ("", "Hyderabad", "Bengaluru", "Chennai")
        self.city_combo.current(0)
        self.city_combo.pack(side=tk.LEFT)
        self.city_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_restaurants())

        self.btn_cart = ttk.Button(self.nav, text="Cart (0)", command=self.show_cart_popup)
        self.btn_cart.pack(side=tk.RIGHT, padx=8)

        self.user_btn = ttk.Menubutton(self.nav, text="Sign In")
        self.user_menu = tk.Menu(self.user_btn, tearoff=0)
        self.user_btn["menu"] = self.user_menu
        self.user_btn.pack(side=tk.RIGHT)
        self.refresh_user_menu()

    def refresh_user_menu(self):
        self.user_menu.delete(0, tk.END)
        if self.current_user:
            self.user_btn.config(text=self.current_user["name"])
            self.user_menu.add_command(label="Order History", command=self.show_history)
            self.user_menu.add_separator()
            self.user_menu.add_command(label="Logout", command=self.logout)
        else:
            self.user_btn.config(text="Sign In")
            self.user_menu.add_command(label="Login / Signup", command=self.show_auth)

    # ---- Frames ----
    def create_frames(self):
        self.content = ttk.Frame(self)
        self.content.pack(fill=tk.BOTH, expand=True)

        # Left: Restaurants list
        left = ttk.Frame(self.content)
        left.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(left, text="Restaurants", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=6)
        self.rest_list = tk.Listbox(left, height=28, width=36)
        self.rest_list.pack(padx=10, pady=(0, 10), fill=tk.Y)
        self.rest_list.bind("<<ListboxSelect>>", self.on_rest_select)

        # Right: Menu and controls
        right = ttk.Frame(self.content)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        top_right = ttk.Frame(right)
        top_right.pack(fill=tk.BOTH, expand=True)

        self.menu_title = ttk.Label(top_right, text="Menu", font=("Segoe UI", 12, "bold"))
        self.menu_title.pack(anchor="w", padx=10, pady=6)

        # Reviews controls
        self.rev_frame = ttk.Frame(top_right)
        self.rev_frame.pack(anchor="w", padx=10)
        self.rev_count_lbl = ttk.Label(self.rev_frame, text="Reviews: 0")
        self.rev_count_lbl.pack(side=tk.LEFT)
        self.btn_show_reviews = ttk.Button(self.rev_frame, text="Show Reviews", command=self.show_reviews)
        self.btn_show_reviews.pack(side=tk.LEFT, padx=8)
        self.btn_add_review = ttk.Button(self.rev_frame, text="Add Review", command=self.add_review_dialog)
        self.btn_add_review.pack(side=tk.LEFT)

        cols = ("Name", "Type", "Price", "Add")
        self.menu_tree = ttk.Treeview(top_right, columns=cols, show="headings")
        for c in cols:
            self.menu_tree.heading(c, text=c)
        self.menu_tree.column("Name", width=300)
        self.menu_tree.column("Type", width=80, anchor=tk.CENTER)
        self.menu_tree.column("Price", width=100, anchor=tk.E)
        self.menu_tree.column("Add", width=80, anchor=tk.CENTER)
        self.menu_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.menu_tree.bind("<Double-1>", self.on_menu_double_click)

        # Bottom cart bar
        bottom = ttk.Frame(self)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        self.total_var = tk.StringVar(value="₹0.00")
        ttk.Label(bottom, text="Cart Total:").pack(side=tk.LEFT, padx=12, pady=8)
        self.total_label = ttk.Label(bottom, textvariable=self.total_var, font=("Segoe UI", 11, "bold"))
        self.total_label.pack(side=tk.LEFT)
        ttk.Button(bottom, text="Place Order", command=self.place_order).pack(side=tk.RIGHT, padx=12)

    # ---- Auth ----
    def show_auth(self):
        win = tk.Toplevel(self)
        win.title("Login / Signup")
        win.geometry("480x360")
        win.grab_set()

        nb = ttk.Notebook(win)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Login tab
        login_tab = ttk.Frame(nb)
        nb.add(login_tab, text="Login")

        lemail = tk.StringVar()
        lpwd = tk.StringVar()
        ttk.Label(login_tab, text="Email").pack(anchor="w", padx=8, pady=(12, 2))
        ttk.Entry(login_tab, textvariable=lemail).pack(fill=tk.X, padx=8)
        ttk.Label(login_tab, text="Password").pack(anchor="w", padx=8, pady=(12, 2))
        ttk.Entry(login_tab, show="*", textvariable=lpwd).pack(fill=tk.X, padx=8)

        def do_login():
            user = self.db.find_user_by_email(lemail.get().strip())
            if not user:
                messagebox.showerror("Login Failed", "No account found for that email.")
                return
            if user["password_hash"] != sha256(lpwd.get().strip()):
                messagebox.showerror("Login Failed", "Incorrect password.")
                return
            self.current_user = user
            self.refresh_user_menu()
            win.destroy()
            self.refresh_restaurants()
            messagebox.showinfo("Welcome", f"Hello {user['name']}! ✨")

        ttk.Button(login_tab, text="Login", command=do_login).pack(pady=16)

        # Signup tab
        signup_tab = ttk.Frame(nb)
        nb.add(signup_tab, text="Signup")

        s_name = tk.StringVar()
        s_email = tk.StringVar()
        s_phone = tk.StringVar()
        s_pwd = tk.StringVar()

        for label, var in (
            ("Full Name", s_name),
            ("Email", s_email),
            ("Phone", s_phone),
            ("Password", s_pwd),
        ):
            ttk.Label(signup_tab, text=label).pack(anchor="w", padx=8, pady=(12, 2))
            show = "*" if label == "Password" else None
            ttk.Entry(signup_tab, textvariable=var, show=show).pack(fill=tk.X, padx=8)

        def do_signup():
            name = s_name.get().strip()
            email = s_email.get().strip().lower()
            phone = s_phone.get().strip()
            pwd = s_pwd.get().strip()
            if not (name and email and pwd):
                messagebox.showerror("Error", "Name, Email and Password are required.")
                return
            if self.db.find_user_by_email(email):
                messagebox.showerror("Error", "Email already registered. Try logging in.")
                return
            uid = self.db.create_user(name, email, phone, sha256(pwd))
            if uid:
                messagebox.showinfo("Success", "Account created! You can now log in.")
                nb.select(0)

        ttk.Button(signup_tab, text="Create Account", command=do_signup).pack(pady=16)

    def logout(self):
        self.current_user = None
        self.cart.clear()
        self.update_cart_ui()
        self.refresh_user_menu()
        self.refresh_restaurants()
        messagebox.showinfo("Logged out", "You have been logged out.")

    # ---- Data/UI refresh ----
    def refresh_restaurants(self):
        self.rest_list.delete(0, tk.END)
        rows = self.db.list_restaurants(self.search_var.get().strip(), self.city_var.get())
        for r in rows:
            avg = r.get('avg_rating', r.get('base_rating', 4.0))
            rc = r.get('review_count', 0)
            self.rest_list.insert(tk.END, f"{r['name']}  •  {r['cuisine']}  ⭐ {avg} ({rc})")
        self.rest_rows = rows
        self.menu_title.config(text="Menu")
        for i in self.menu_tree.get_children():
            self.menu_tree.delete(i)
        self.rev_count_lbl.config(text="Reviews: 0")

    def on_rest_select(self, event=None):
        sel = self.rest_list.curselection()
        if not sel:
            return
        idx = sel[0]
        rest = self.rest_rows[idx]
        self.menu_title.config(text=f"Menu — {rest['name']}")
        items = self.db.list_menu(rest["id"])
        self.current_restaurant = rest
        # Populate menu
        for i in self.menu_tree.get_children():
            self.menu_tree.delete(i)
        for it in items:
            # type label based on veg/non_veg columns
            if it.get("veg", 0) == 1:
                typ = "Veg"
            elif it.get("non_veg", 0) == 1:
                typ = "Non-Veg"
            else:
                typ = "Non-veg"
            self.menu_tree.insert("", tk.END, iid=str(it["id"]), values=(it["name"], typ, f"₹{it['price']:.2f}", "Add"))
        # Update reviews count
        rvcount = rest.get('review_count', 0)
        self.rev_count_lbl.config(text=f"Reviews: {rvcount}")

    def on_menu_double_click(self, event):
        item_id = self.menu_tree.focus()
        if not item_id:
            return
        vals = self.menu_tree.item(item_id, "values")
        name = vals[0]
        price_text = vals[2].replace("₹", "").strip()
        try:
            price = float(price_text)
        except:
            return
        mid = int(item_id)
        self.add_to_cart(mid, name, price)

    def add_to_cart(self, mid: int, name: str, price: float):
        if mid not in self.cart:
            self.cart[mid] = {"id": mid, "name": name, "price": price, "qty": 0}
        self.cart[mid]["qty"] += 1
        self.update_cart_ui()

    def update_cart_ui(self):
        total = sum(v["price"] * v["qty"] for v in self.cart.values())
        self.total_var.set(f"₹{total:.2f}")
        qty = sum(v["qty"] for v in self.cart.values())
        self.btn_cart.config(text=f"Cart ({qty})")

    def show_cart_popup(self):
        if not self.cart:
            messagebox.showinfo("Cart", "Your cart is empty.")
            return
        win = tk.Toplevel(self)
        win.title("Your Cart")
        win.geometry("520x420")
        cols = ("Item", "Qty", "Price", "Actions")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c)
        tree.column("Item", width=260)
        tree.column("Qty", width=60, anchor=tk.CENTER)
        tree.column("Price", width=90, anchor=tk.E)
        tree.column("Actions", width=90, anchor=tk.CENTER)
        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        def refresh_tree():
            for i in tree.get_children():
                tree.delete(i)
            for v in self.cart.values():
                tree.insert("", tk.END, iid=str(v["id"]), values=(v["name"], v["qty"], f"₹{v['price']*v['qty']:.2f}", "-  +  🗑"))

        def on_double(e=None):
            iid = tree.focus()
            if not iid:
                return
            v = self.cart[int(iid)]
            # show adjust dialog
            self.adjust_item_dialog(int(iid))
            refresh_tree()
            self.update_cart_ui()

        tree.bind("<Double-1>", on_double)
        refresh_tree()

        ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)

    def adjust_item_dialog(self, mid: int):
        v = self.cart.get(mid)
        if not v:
            return
        win = tk.Toplevel(self)
        win.title(v["name"])
        win.geometry("320x180")
        q = tk.IntVar(value=v["qty"])
        ttk.Label(win, text=v["name"], font=("Segoe UI", 11, "bold")).pack(pady=(14, 4))
        ttk.Spinbox(win, from_=0, to=50, textvariable=q, width=6).pack()
        def apply():
            n = q.get()
            if n <= 0:
                self.cart.pop(mid, None)
            else:
                v["qty"] = n
            self.update_cart_ui()
            win.destroy()
        ttk.Button(win, text="Apply", command=apply).pack(pady=12)

    def place_order(self):
        if not self.current_user:
            messagebox.showwarning("Sign In", "Please login/sign up before placing an order.")
            self.show_auth()
            return
        if not self.cart:
            messagebox.showinfo("Cart", "Your cart is empty.")
            return
        rest = getattr(self, "current_restaurant", None)
        if not rest:
            messagebox.showwarning("Select Restaurant", "Please select a restaurant first.")
            return
        items = [(v["id"], v["qty"], v["price"]) for v in self.cart.values()]

        # Payment dialog
        pay_win = tk.Toplevel(self)
        pay_win.title("Payment")
        pay_win.geometry("420x300")
        pay_win.grab_set()

        method = tk.StringVar(value="CASH")
        ttk.Label(pay_win, text="Choose Payment Method:").pack(anchor="w", padx=12, pady=(12,4))
        ttk.Radiobutton(pay_win, text="Cash on Delivery", variable=method, value="CASH").pack(anchor="w", padx=20)
        ttk.Radiobutton(pay_win, text="Card", variable=method, value="CARD").pack(anchor="w", padx=20)
        ttk.Radiobutton(pay_win, text="UPI", variable=method, value="UPI").pack(anchor="w", padx=20)

        details_frame = ttk.Frame(pay_win)
        details_frame.pack(fill=tk.X, padx=12, pady=8)

        ttk.Label(details_frame, text="Details (card number / UPI id):").pack(anchor="w")
        details_var = tk.StringVar()
        details_entry = ttk.Entry(details_frame, textvariable=details_var)
        details_entry.pack(fill=tk.X)

        def do_pay_and_place():
            pm = method.get()
            details = details_var.get().strip()
            paid = 0
            if pm == 'CASH':
                paid = 0
                ok = messagebox.askyesno("Confirm", "Place order with Cash on Delivery?")
                if not ok:
                    return
            else:
                if not details:
                    messagebox.showerror("Error", "Enter card number or UPI id to simulate payment.")
                    return
                # simulate 95% success
                success = random.random() < 0.95
                if not success:
                    messagebox.showerror("Payment Failed", "The simulated payment failed. Try again.")
                    return
                paid = 1

            oid = self.db.place_order(self.current_user['id'], rest['id'], items, payment_method=pm, paid=paid)
            if oid:
                self.cart.clear()
                self.update_cart_ui()
                pay_win.destroy()
                messagebox.showinfo("Order Placed", f"Your order #{oid} has been placed!")
                self.refresh_restaurants()
            else:
                messagebox.showerror("Error", "Could not place order. Try again.")

        ttk.Button(pay_win, text="Pay & Place Order", command=do_pay_and_place).pack(pady=12)
        ttk.Button(pay_win, text="Cancel", command=pay_win.destroy).pack()

    def show_history(self):
        if not self.current_user:
            self.show_auth()
            return
        win = tk.Toplevel(self)
        win.title("Order History")
        win.geometry("740x420")
        cols = ("Order #", "Restaurant", "Total", "Status", "Placed At", "Paid", "Payment Method")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c)
        tree.column("Order #", width=80, anchor=tk.CENTER)
        tree.column("Restaurant", width=180)
        tree.column("Total", width=90, anchor=tk.E)
        tree.column("Status", width=110, anchor=tk.CENTER)
        tree.column("Placed At", width=140)
        tree.column("Paid", width=60, anchor=tk.CENTER)
        tree.column("Payment Method", width=100, anchor=tk.CENTER)
        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        rows = self.db.fetch_order_history(self.current_user["id"])
        for r in rows:
            ts = r["created_at"].strftime("%Y-%m-%d %H:%M") if isinstance(r["created_at"], datetime) else str(r["created_at"])
            paid_text = 'Yes' if r.get('paid', 0) else 'No'
            pm = r.get('payment_method', 'CASH')
            tree.insert("", tk.END, iid=str(r['id']), values=(r['id'], r['restaurant'], f"₹{r['total']:.2f}", r['status'], ts, paid_text, pm))

        def advance_status():
            iid = tree.focus()
            if not iid:
                messagebox.showinfo("Select order", "Select an order to advance status.")
                return
            oid = int(iid)
            order = self.db.get_order(oid)
            if not order:
                messagebox.showerror("Error", "Order not found.")
                return
            seq = ['PLACED', 'PREPARING', 'ON THE WAY', 'DELIVERED']
            cur = order.get('status', 'PLACED')
            try:
                idx = seq.index(cur)
                if idx < len(seq) - 1:
                    new = seq[idx + 1]
                else:
                    messagebox.showinfo("Already final", "This order is already delivered.")
                    return
            except ValueError:
                new = 'PREPARING'
            self.db.update_order_status(oid, new)
            messagebox.showinfo("Status Updated", f"Order #{oid} status updated to {new}.")
            win.destroy()
            self.show_history()

        def refresh():
            win.destroy()
            self.show_history()

        btns = ttk.Frame(win)
        btns.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(btns, text="Advance Status", command=advance_status).pack(side=tk.LEFT)
        ttk.Button(btns, text="Refresh", command=refresh).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="Close", command=win.destroy).pack(side=tk.RIGHT)

    # ---- Reviews UI ----
    def show_reviews(self):
        rest = getattr(self, 'current_restaurant', None)
        if not rest:
            messagebox.showinfo('Reviews', 'Select a restaurant first.')
            return
        rows = self.db.get_reviews(rest['id'])
        win = tk.Toplevel(self)
        win.title(f"Reviews — {rest['name']}")
        win.geometry('640x420')
        cols = ('Reviewer', 'Rating', 'Review', 'At')
        tree = ttk.Treeview(win, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
        tree.column('Reviewer', width=140)
        tree.column('Rating', width=60, anchor=tk.CENTER)
        tree.column('Review', width=320)
        tree.column('At', width=120)
        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        for r in rows:
            ts = r['created_at'].strftime('%Y-%m-%d %H:%M') if isinstance(r['created_at'], datetime) else str(r['created_at'])
            tree.insert('', tk.END, values=(r.get('reviewer','Unknown'), r.get('rating',0), (r.get('review_text') or '')[:300], ts))
        ttk.Button(win, text='Close', command=win.destroy).pack(pady=6)

    def add_review_dialog(self):
        if not self.current_user:
            messagebox.showwarning('Sign In', 'Please login to add a review.')
            self.show_auth()
            return
        rest = getattr(self, 'current_restaurant', None)
        if not rest:
            messagebox.showinfo('Add Review', 'Select a restaurant first.')
            return
        win = tk.Toplevel(self)
        win.title('Add Review')
        win.geometry('420x340')
        ttk.Label(win, text=f"Add review for {rest['name']}", font=(None, 11, 'bold')).pack(pady=(12,6))
        rating_var = tk.IntVar(value=5)
        ttk.Label(win, text='Rating (1-5)').pack(anchor='w', padx=12)
        ttk.Spinbox(win, from_=1, to=5, textvariable=rating_var, width=6).pack(padx=12)
        ttk.Label(win, text='Review text').pack(anchor='w', padx=12, pady=(8,2))
        txt = tk.Text(win, height=8)
        txt.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,8))

        def submit():
            rating = rating_var.get()
            review_text = txt.get('1.0', tk.END).strip()
            rid = self.db.create_review(self.current_user['id'], rest['id'], rating, review_text)
            if rid:
                messagebox.showinfo('Thanks', 'Your review has been posted.')
                win.destroy()
                self.refresh_restaurants()
            else:
                messagebox.showerror('Error', 'Could not post review. Try again.')

        ttk.Button(win, text='Submit', command=submit).pack(pady=8)
        ttk.Button(win, text='Cancel', command=win.destroy).pack()

# -----------------------
# App entrypoint
# -----------------------
if __name__ == "__main__":
    try:
        db = Database(DBConfig())   # <-- edit DBConfig if needed
        app = ZomatoApp(db)
        app.refresh_restaurants()
        app.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            messagebox.showerror("Fatal Error", str(e))
        except Exception:
            print("Fatal Error:", e)
