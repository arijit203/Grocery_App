from flask import Flask, render_template, redirect, url_for, request,flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exists
from sqlalchemy.exc import SQLAlchemyError
from flask_wtf import FlaskForm
from wtforms import StringField,SubmitField,PasswordField,BooleanField,ValidationError,IntegerField,FloatField,SelectField
from wtforms.validators import DataRequired,EqualTo,Length,NumberRange
from datetime import datetime
from flask_wtf.csrf import generate_csrf

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt



from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import UserMixin, login_user,LoginManager, login_required, logout_user,current_user


app=Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///grocery.db'
app.config['SECRET_KEY']="my secret key"

db=SQLAlchemy(app)


#Flask Login Stuff
login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view='login'

class Users(db.Model,UserMixin):
    id=db.Column(db.Integer,primary_key=True,autoincrement=True)
    username=db.Column(db.String(200),nullable=False,unique=True)
    name=db.Column(db.String(200),nullable=False)
    email=db.Column(db.String(200),nullable=False,unique=True)
    date_added=db.Column(db.DateTime,default=datetime.utcnow)
    password_hash=db.Column(db.String(128))
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self,password):
        self.password_hash=generate_password_hash(password)

    def verify_password(self,password):
        return check_password_hash(self.password_hash,password) 
    #create string
    def __repr__(self):
        return '<Name %r>' %self.name



@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))




@app.route('/')
def primary():
    return render_template('front_page.html')

 
class LoginForm(FlaskForm):
    username=StringField("Username",validators=[DataRequired()])
    password_hash=PasswordField("Password",validators=[DataRequired()])
    submit=SubmitField("Login")

#create the Register Form Class
class UserForm(FlaskForm):
    username=StringField("Username",validators=[DataRequired()])
    name=StringField("Name",validators=[DataRequired()])
    email=StringField("Email",validators=[DataRequired()])
    password_hash=PasswordField('Password',validators=[DataRequired(),EqualTo('password_hash2',message='Passwords Must Match!')])
    password_hash2=PasswordField('Confirm Password',validators=[DataRequired()])
    submit=SubmitField("Submit")


@app.route('/user_register', methods=['GET', 'POST'])
def add_user():
    name = None
    form = UserForm()

    if form.validate_on_submit():
        existing_user = Users.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash("Username is already taken. Please choose a different username.")
            return render_template("user_register.html", name=name, form=form)
        user = Users.query.filter_by(email=form.email.data).first()

        if user is None:
            # hash the password!!!
            hashed_pw = generate_password_hash(form.password_hash.data)
            user = Users(username=form.username.data, name=form.name.data, email=form.email.data, password_hash=hashed_pw)

            
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('user_dashboard',username=form.username.data))
        else:
            flash("Email is already registered. Please use a different email.")
            return render_template("user_register.html", username=username, form=form, our_users=our_users,name=name)
    username = form.username.data
    form.username.data = ''
    form.name.data = ''
    form.email.data = ''
    form.password_hash.data = ''

    our_users = Users.query.order_by(Users.date_added)
    return render_template("user_register.html", name=name, form=form, our_users=our_users,username=username)

#Create Login Page
@app.route('/user_login',methods=['GET','POST'])

def login():
    form=LoginForm()
    if form.validate_on_submit():
        user=Users.query.filter_by(username=form.username.data).first()
        
        if user:
            #check the hash
            if check_password_hash(user.password_hash,form.password_hash.data):
                login_user(user) #creates the session
                return redirect(url_for('user_dashboard',username=form.username.data))

            else:
                flash('Wrong Password - Try Again!!')    
        else:
            flash("That User doesn't exist! Try Again...")            
    return render_template('user_login.html',form=form)



@app.route('/<username>/user_dashboard',methods=["GET","POST"])
@login_required
def user_dashboard(username):
    # name=request.args.get('username')
    categories = Category.query.all()
    category_items_dict = {}
    for category in categories:
        items = Order_items.query.filter_by(category_id=category.category_id).all()
        category_items_dict[category.category_id] = items

    return render_template('user_dashboard.html', categories=categories, category_items_dict=category_items_dict,username=username)

class Cart(db.Model):
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    cart_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Cart cart_id={self.cart_id} item_id={self.item_id} user_id={self.user_id} name={self.name} quantity={self.quantity}>'

class CartForm(FlaskForm):
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])

class BuyForm(FlaskForm):
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    
@app.route("/buy_item/<int:item_id>/<int:category_id>/<username>", methods=["GET", "POST"])
@login_required
def buy_item(item_id, category_id, username):
    form = BuyForm()

    # Get the item and category from the database based on the item_id and category_id
    item = Order_items.query.get(item_id)
    category = Category.query.get(category_id)
    user=Users.query.filter_by(username=username).first()
    if not item or not category:
        flash("Item or category not found.", "error")
        return redirect(url_for("user_dashboard",username=username))  # Redirect to some appropriate page

    if form.validate_on_submit():
        quantity = form.quantity.data

        # Perform any additional validation or checks here if required

        try:
            # Create a new entry in the placed_order table
            placed_order = Placed_orders(
                
                user_id=user.id,  # Replace this with the actual user_id of the logged-in user
                total_price=item.price*quantity
            )
            
            db.session.add(placed_order)
            db.session.commit()

            flash("Item purchased successfully!", "success")
            return redirect(url_for("user_dashboard",username=username))  # Redirect to a success page

        except Exception as e:
            db.session.rollback()
            flash(f'Error processing the purchase. {e}', "error")

    return render_template("buy_item.html", form=form, username=username,category=category,item=item)    

@app.route('/<username>/add_tocart/<int:category_id>/<int:item_id>', methods=['GET', 'POST'])
@login_required
def add_tocart(username,category_id, item_id):
    category = Category.query.get_or_404(category_id)
    item = Order_items.query.get_or_404(item_id)
    form = CartForm()

    if form.validate_on_submit():
        # Get the quantity from the form submission
        quantity = form.quantity.data
        unit=(item.unit).split("/")[1]
        # Perform any validation you need (e.g., checking if the quantity is available)
        if(quantity<=item.quantity):
            user=Users.query.filter_by(username=username).first()
            # Save the cart item to the database
            
            cart_item = Cart(category_id=category_id, item_id=item.id, user_id=user.id, username=username, quantity=quantity)
            db.session.add(cart_item)
            db.session.commit()

            flash(f'{quantity}{unit} {item.name} added to cart!', 'success')
            return redirect(url_for('user_dashboard',username=username))
        else:
            flash(f'{quantity} {item.name} cannot be added to cart!', 'Failure')
            return redirect(url_for('add_tocart',item_id=item_id,category_id=category_id,username=username))

        # Get the user ID (replace this with your actual user authentication method)
         # Replace with your user ID logic (e.g., current_user.id)



    return render_template('add_tocart.html', item=item, form=form,category=category,username=username)

#Edit cart Item
@app.route('/<username>/edit_cart_item/<int:cart_item_id>', methods=['GET', 'POST'])
@login_required
def edit_cart_item(username, cart_item_id):
    cart_item = Cart.query.get_or_404(cart_item_id)
    item = Order_items.query.get_or_404(cart_item.item_id)
    category = Category.query.get_or_404(cart_item.category_id)
    form = CartForm(obj=cart_item)

    if form.validate_on_submit():
        quantity = form.quantity.data
        unit = item.unit.split("/")[1]

        if quantity <= item.quantity:
            cart_item.quantity = quantity
            
            db.session.commit()
            flash(f'{quantity} {unit} {item.name} updated in cart!', 'success')
            return redirect(url_for('user_dashboard', username=username))
        else:
            flash(f'{quantity} {item.name} cannot be updated in cart!', 'failure')

    return render_template('edit_cart_item.html', item=item, form=form, category=category, username=username, cart_item=cart_item)


@app.route('/<username>/cart', methods=['GET', 'POST'])
@login_required
def cart(username):
    user = Users.query.filter_by(username=username).first()
    total_price = 0  # Variable to store the total price

    
    cart_items = db.session.query(Cart, Order_items, Category)\
        .join(Order_items, Cart.item_id == Order_items.id)\
        .join(Category, Order_items.category_id == Category.category_id)\
        .filter(Cart.user_id == user.id)\
        .all()
    for cart_item, item, category in cart_items:
        total_price += item.price * cart_item.quantity
    return render_template('cart.html', cart_items=cart_items,total_price=total_price,username=username)




def get_user_orders(user_id):
    orders = Placed_orders.query.filter_by(user_id=user_id).all()
    return orders

def get_user_details(username):
    user = Users.query.filter_by(username=username).first()
    return user

@app.route("/<username>/user_profile")
@login_required
def user_profile(username):
    user = get_user_details(username)
    orders = get_user_orders(user.id)
    return render_template("user_profile.html", user=user, orders=orders, username=username)

@app.route("/<username>/delete_from_cart/<int:item_id>",methods=['GET','POST'])
@login_required
def delete_from_cart(username,item_id):
    cart_item = Cart.query.filter_by(username=username, item_id=item_id).first()

    if cart_item:
        try:
            # Update the Order_items table and add the quantity back
            item = Order_items.query.get_or_404(item_id)
            item.quantity += cart_item.quantity

            
            db.session.delete(cart_item)
            db.session.commit()

            flash("Item deleted from the cart.", "success")
        except:
            flash("Error occurred while deleting the item from the cart. Please try again later.", "danger")
    else:
        flash("Item not found in the cart.", "danger")

    return redirect(url_for('cart', username=username))

class User_buy(db.Model):
    buy_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, nullable=False)
    category_name = db.Column(db.String(200), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    

class Placed_orders(db.Model):
    order_id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Placed_Orders order_id={self.order_id} user_id={self.user_id} order_date={self.order_date} total_price={self.total_price}>'
    
@app.route('/<username>/place_order', methods=['GET','POST'])

@login_required
def place_order(username):
    user_id = current_user.id
    cart_items = Cart.query.filter_by(user_id=user_id).all()
    total_price = 0

    if cart_items:
        try:
            # Calculate the total price of the order
            for cart_item in cart_items:
                item = Order_items.query.get_or_404(cart_item.item_id)
                total_price += item.price * cart_item.quantity

            
            # Update the Order_items table and subtract the ordered quantity
            for cart_item in cart_items:
                item = Order_items.query.filter_by(id=cart_item.item_id).first()
                if cart_item.quantity <= item.quantity:
                        # Save the order to the placed_order table
                    placed_order = Placed_orders(user_id=user_id, total_price=total_price)
                    db.session.add(placed_order)
                    db.session.commit()

                    category=Category.query.filter_by(category_id=item.category_id).first()
                    user_buyer = User_buy(
                        order_id=placed_order.order_id,
                        category_name=category.category_name,
                        item_name=item.name,
                        quantity=cart_item.quantity,
                        price=item.price
                    )   
                    
                       
                        
                    db.session.add(user_buyer)
                    db.session.commit()
                    db.session.flush()
                    item.quantity -= cart_item.quantity
                    db.session.delete(cart_item)
                    db.session.commit()
                else:
                    flash(f"Insufficient quantity for {item.name} available. Order cannot be placed.", "danger")
                    return redirect(url_for('cart', username=username))

            flash("Order placed successfully! Thank you for your purchase.", "success")
        except SQLAlchemyError as e:
            # Rollback the transaction on any database errors
            db.session.rollback()
            flash(f"Error occurred while placing the order: {str(e)}", "danger")

    return redirect(url_for('cart', username=username))   

class SearchForm(FlaskForm):
    search_query = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Search')

@app.route('/<username>/search', methods=['GET', 'POST'])
@login_required
def search_items(username):
    form = SearchForm()

    if form.validate_on_submit():
        search_query = form.search_query.data.strip().lower()

        if search_query:
            # Query the Category table to check if the search category exists
            category_results = Category.query.filter(Category.category_name.ilike(f'%{search_query}%')).all()

            # Query the Order_items table to check if the search query matches any item names
            item_results = Order_items.query.filter(Order_items.name.ilike(f'%{search_query}%')).all()

            return render_template('search_items.html', category_results=category_results, item_results=item_results,form=form)

    # If the form is not submitted or the search query is empty, stay on the user dashboard
    return render_template('user_dashboard.html', username=username, form=form)


# #create Logout page
@app.route('/user_logout',methods=['GET','POST'])
@login_required
def user_logout():
    logout_user()
    flash("You have been Logged Out!  Thanks for Stopping By...")
    return redirect(url_for('login'))

#####################################################################################################################################

class Managers(db.Model, UserMixin):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(200),nullable=False,unique=True)
    password_hash=db.Column(db.String(200),nullable=False)
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    def __repr__(self):
        return '<Name %r>' %self.name



class ManagerForm(FlaskForm):
    username=StringField("Username",validators=[DataRequired()])
    password_hash=PasswordField('Password',validators=[DataRequired()])
    submit=SubmitField("Login")



@app.route('/manager_login', methods=['GET', 'POST'])
def manager():
    form = ManagerForm()
    if form.validate_on_submit():
        user = Managers.query.filter_by(username=form.username.data).first()
        if user:
            # Compare plain text passwords (Not recommended for production)
            if user.password_hash == form.password_hash.data:
                login_user(user)# Creates the session
                return redirect(url_for('manager_dashboard',name=form.username.data))
            else:
                flash('Wrong Password - Try Again!!')
        else:
            flash("That manager doesn't exist! Try Again...")
    return render_template('manager_login.html', form=form)

# @app.route('/manager_dashboard',methods=['GET','POST'])
# def manager_dashboard():
#     name = request.args.get('name')
#     categories = Category.query.all()
#     items=Order_items.query.all()
#     return render_template('manager_dashboard.html',name=name,categories=categories,items=items)

@app.route("/<name>/manager_dashboard", methods=["GET","POST"])
def manager_dashboard(name):
    categories = Category.query.all()
    csrf_token = generate_csrf()
    # Create a dictionary to store items for each category
    category_items_dict = {}
    for category in categories:
        # Fetch items associated with the current category
        items = Order_items.query.filter_by(category_id=category.category_id).all()
        category_items_dict[category.category_id] = items
    
    return render_template("manager_dashboard.html", categories=categories, category_items_dict=category_items_dict, name=name, csrf_token=csrf_token)
    

@app.route('/<name>/summary')
def summary(name):
    user_buys = User_buy.query.all()

    # Process data for the first graph (category-wise utilization)
    category_utilization = {}
    for buy in user_buys:
        if buy.category_name in category_utilization:
            category_utilization[buy.category_name] += buy.quantity
        else:
            category_utilization[buy.category_name] = buy.quantity

    # Process data for the second graph (range of products bought in the present week)
    current_week = datetime.now().isocalendar()[1]
    price_ranges = [0, 10, 20, 30, 40, 50, 100, 200, 500, 1000]
    products_in_ranges = [0] * (len(price_ranges) - 1)
    for buy in user_buys:
        if buy.date_added.isocalendar()[1] == current_week:
            for i in range(len(price_ranges) - 1):
                if price_ranges[i] < buy.price <= price_ranges[i + 1]:
                    products_in_ranges[i] += 1
                    break

    # Plot the first graph (category-wise utilization)
    plt.figure(figsize=(8, 5))
    bar_width = 0.5
    bar_height = 0.2
    plt.bar(category_utilization.keys(), category_utilization.values(), width=bar_width)
    plt.xlabel('Category', fontsize=12)
    plt.ylabel('Total Quantity', fontsize=12)
    plt.title('Category-wise Utilization', fontsize=14)
    plt.xticks(rotation=45, fontsize=10)
    plt.yticks(fontsize=10)
    
    plt.tight_layout()
    plt.savefig('static/category_utilization.png')
    plt.close()

    # Plot the second graph (range of products bought in the present week)
    
    data = db.session.query(User_buy.item_name, db.func.sum(User_buy.quantity)).group_by(User_buy.item_name).all()
    
    # Unzip the data for plotting
    item_names, quantities = zip(*data)
    
    # Plot the bar graph
    plt.figure(figsize=(8, 5))
    plt.bar(item_names, quantities, width=bar_width)
    plt.xlabel("Item Name", fontsize=12)
    plt.ylabel("Quantity Purchased", fontsize=12)
    plt.title("Summary of Items Purchased", fontsize=14)
    plt.xticks(rotation=45, fontsize=10)
    plt.yticks(fontsize=10)
    plt.tight_layout()
    
    # Save the plot to a file
    plot_path = "static/summary_plot.png"
    plt.savefig(plot_path)
    
    # Close the plot to free up resources
    plt.close()

    return render_template('summary.html', name=name, plot_path=plot_path)


@app.route('/logout',methods=['GET','POST'])
@login_required
def logout():
    logout_user()
    flash("You have been Logged Out!  Thanks for Stopping By...")
    return redirect(url_for('manager'))

class Category(db.Model):
    category_id=db.Column(db.Integer,primary_key=True)
    category_name=db.Column(db.String(200),nullable=False,unique=True)

class CreateCategoryForm(FlaskForm):
    category_name = StringField('Category Name : ', validators=[DataRequired()])
    submit = SubmitField('Save')    

@app.route('/<name>/create_category',methods=["GET","POST"])
def create_category(name):
    form = CreateCategoryForm()

    if form.validate_on_submit():
        

        # Check if the manager is authorized to create a category (you'll need to implement this logic)
        # For simplicity, let's assume any logged-in user is considered a manager
        # You can enhance this by using Flask-Login or any other authentication mechanism.
        # if current_user.is_authenticated:
        # Create the category object
        existing_category = Category.query.filter_by(category_name=form.category_name.data).first()
        if existing_category:
            flash('A category with the same name already exists.', 'danger')
        else:
            # Create the category object
            new_category = Category(category_name=form.category_name.data)
            db.session.add(new_category)
            # Add the category to the database
            flash('Category created successfully!', 'success')
            db.session.commit()
            return redirect(url_for('manager_dashboard',name=name))  # Redirect to the home page or any other page
        

            
        # else:
        #     flash('You are not authorized to create a category.', 'danger')
    category_name = form.category_name.data
    form.category_name.data=''
    return render_template('create_category.html', category_name=category_name,form=form,name=name)


#for items class
class Order_items(db.Model):
    id=db.Column(db.Integer,primary_key=True, autoincrement=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'), nullable=False)
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float, nullable=False)
    name = db.Column(db.String(200), nullable=False,unique=True)
    unit=db.Column(db.String(20), nullable=False)
    MFD=db.Column(db.DateTime,default=datetime.utcnow)


class CreateItemForm(FlaskForm):
    product_name = StringField('Product Name :', validators=[DataRequired()])
    unit = SelectField('Unit :', choices=[('Rs/kg', 'Rs/kg'), ('Rs/L', 'Rs/L'), ('Rs/dozen', 'Rs/dozen'), ('Rs/gram', 'Rs/gram')], validators=[DataRequired()])
    rate_per_unit = FloatField('Rate/Unit :', validators=[DataRequired()])
    quantity = IntegerField('Quantity :', validators=[DataRequired(), NumberRange(min=0)])
    save_button = SubmitField('Save')


@app.route("/<name>/create_item/<int:category_id>", methods=["GET", "POST"])
def create_item(name,category_id):
    form = CreateItemForm()

    if form.is_submitted():
            # Get the form data
        product_name = form.product_name.data
        unit = form.unit.data
        rate_per_unit = form.rate_per_unit.data
        quantity = form.quantity.data

        # Create an entry in the OrderItem table or perform other actions as needed
        # For example:
        existing_item = Order_items.query.filter_by(name=product_name).first()
        if existing_item:
            flash(f'The product "{product_name}" already exists in the order_items table!', 'failure')
        else:    
            order_item = Order_items(name=product_name, unit=unit, price=rate_per_unit, quantity=quantity, category_id=category_id)
            # Save the order_item to the database (assuming OrderItem is your SQLAlchemy model)
            db.session.add(order_item)
            db.session.commit()

            # Redirect to the manager dashboard or any other page as needed
            return redirect(url_for('manager_dashboard',name=name))

    return render_template("create_item.html", form=form,name=name)

class EditItemForm(FlaskForm):
    name = StringField('Item Name', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    unit = SelectField('Unit', choices=[('Rs/kg', 'Rs/Kg'), ('Rs/L', 'Rs/L'), ('Rs/Dozen', 'Rs/dozen'), ('Rs/gram', 'Rs/gram')], validators=[DataRequired()])
    category_id = IntegerField('Category ID', validators=[DataRequired()])

@app.route("/<name>/edit_item/<int:item_id>", methods=["GET", "POST"])
def edit_item(name,item_id):
    item = Order_items.query.get_or_404(item_id)
    form = EditItemForm(obj=item)
    
    if form.validate_on_submit():
        form.populate_obj(item)
        db.session.commit()
        return redirect(url_for('manager_dashboard',name=name))

    return render_template("edit_item.html", form=form,name=name)

# Route to delete an item
@app.route("/<name>/delete_item/<int:item_id>", methods=["GET","POST"])
def delete_item(name, item_id):
    item = Order_items.query.get(item_id)
    if not item:
        flash("Item not found.", "error")
        return redirect(url_for("manager_dashboard", name=name))

    try:
        db.session.delete(item)
        db.session.commit()
        flash("Item deleted successfully.", "success")
        return redirect(url_for("manager_dashboard", name=name))
    except Exception as e:
        db.session.rollback()
        flash("Error deleting item.", "error")
        return redirect(url_for("manager_dashboard", name=name))




#now category

class EditCategoryForm(FlaskForm):
    category_name = StringField('Category Name', validators=[DataRequired(), Length(max=200)])
    submit = SubmitField('Save')

@app.route("/<name>/edit_category/<int:category_id>", methods=["GET", "POST"])
def edit_category(name,category_id):
    category = Category.query.get_or_404(category_id)
    form = EditCategoryForm()
    old_name=category.category_name
    if request.method == "POST" and form.validate_on_submit():
        new_category_name = form.category_name.data
        
        # Check if the new category name collides with any existing category name
        if category.category_name != new_category_name and db.session.query(exists().where(Category.category_name == new_category_name)).scalar():
            flash("A category with the same name already exists.", "danger")
        else:

            category.category_name = new_category_name
            db.session.commit()
            flash("Category name updated successfully!", "success")
            return redirect(url_for("manager_dashboard",name=name))

    return render_template("edit_category.html", form=form,name=name,category_name=old_name)


@app.route("/<name>/delete_category/<int:category_id>", methods=["GET","POST"])
def delete_category(name,category_id):
    # Fetch the category to delete
    category = Category.query.get(category_id)
    print(category_id)
    if not category:
        flash("Category not found.", "error")
        return redirect(url_for("manager_dashboard",name=name))

    try:
        # Delete the items associated with the category
        Order_items.query.filter_by(category_id=category_id).delete()

        # Delete the category
        db.session.delete(category)
        db.session.commit()

        flash("Category  and it's associated Items deleted successfully.", "success")
        return redirect(url_for("manager_dashboard",name=name))
    except Exception as e:
        db.session.rollback()
        flash("Error deleting category and items.", "error")
        return redirect(url_for("manager_dashboard",name=name))
# @app.route("/delete_category/<int:category_id>", methods=["GET", "POST"])
# def delete_category(category_id):
#     category = Category.query.get_or_404(category_id)

#     if request.method == "POST":
#         # Delete the category and its associated items from the database
#         items_to_delete = Order_items.query.filter_by(category_id=category_id).all()
#         for item in items_to_delete:
#             db.session.delete(item)
#         db.session.delete(category)
#         db.session.commit()
#         return redirect(url_for('manager_dashboard'))

#     return render_template("delete_category.html", category=category)

# ... (other routes)

app.run(debug=True)

