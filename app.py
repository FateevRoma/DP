from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
import os
from flask.cli import with_appcontext
import click

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Модель товару
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    subcategory = db.Column(db.String(100), nullable=True)
    image = db.Column(db.String(200), nullable=True)

ADMIN_CREDENTIALS = {'login': 'admin', 'password': 'admin123'}

@app.route('/')
def index():
    query = request.args.get('q', '')
    max_price = request.args.get('price', '')
    category = request.args.get('category', '')
    subcategory = request.args.get('subcategory', '')
    sort = request.args.get('sort', '')

    filtered = Product.query

    if query:
        filtered = filtered.filter(Product.name.ilike(f'%{query}%'))
    if max_price.isdigit():
        filtered = filtered.filter(Product.price <= int(max_price))
    if category:
        filtered = filtered.filter_by(category=category)
    if subcategory:
        filtered = filtered.filter_by(subcategory=subcategory)
    if sort == 'price_asc':
        filtered = filtered.order_by(Product.price.asc())
    elif sort == 'price_desc':
        filtered = filtered.order_by(Product.price.desc())

    products = filtered.all()
    all_products = Product.query.all()
    categories = sorted(set(p.category for p in all_products))
    subcategories = {
        cat: sorted(set(p.subcategory for p in all_products if p.category == cat and p.subcategory))
        for cat in categories
    }

    return render_template('index.html', products=products, query=query, price=max_price,
                           categories=categories, subcategories=subcategories,
                           selected_category=category, selected_subcategory=subcategory,
                           selected_sort=sort)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    cart = session.get('cart', [])
    cart.append(product_id)
    session['cart'] = cart
    return redirect(url_for('index'))

@app.route('/cart')
def view_cart():
    cart_ids = session.get('cart', [])
    items = Product.query.filter(Product.id.in_(cart_ids)).all()
    total = sum(p.price for p in items)
    return render_template('cart.html', items=items, total=total)

@app.route('/clear_cart')
def clear_cart():
    session['cart'] = []
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']
        session['cart'] = []
        return f"<h2>Дякую за замовлення, {name}! Ми доставимо товар за адресою: {address}</h2><a href='/'>На головну</a>"
    return render_template('checkout.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        if login == ADMIN_CREDENTIALS['login'] and password == ADMIN_CREDENTIALS['password']:
            session['admin'] = True
            return redirect(url_for('admin_panel'))
        else:
            return "Невірний логін або пароль"
    return render_template('admin_login.html')

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    products = Product.query.all()
    return render_template('admin_panel.html', products=products)

@app.route('/admin/add', methods=['GET', 'POST'])
def add_product():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        image_file = request.files['image']
        filename = ''
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)

        new_product = Product(
            name=request.form['name'],
            price=int(request.form['price']),
            category=request.form['category'],
            subcategory=request.form['subcategory'],
            image=filename
        )
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('admin_panel'))  # ✅ виправлено
    return render_template('admin_add_edit.html', action='Додати', product={})

@app.route('/admin/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.price = int(request.form['price'])
        product.category = request.form['category']
        product.subcategory = request.form['subcategory']

        image_file = request.files['image']
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            product.image = filename

        db.session.commit()
        return redirect(url_for('admin_panel'))  # ✅ виправлено
    return render_template('admin_add_edit.html', action='Редагувати', product=product)

@app.route('/admin/delete/<int:product_id>')
def delete_product(product_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_panel'))

    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)

@app.cli.command("create-db")
@with_appcontext
def create_db():
    db.create_all()
    print("✅ Базу створено")

