from flask import Flask, request, redirect, url_for, session, render_template_string, flash, abort
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# 1. Create the Flask application instance first
app = Flask(__name__)

# 2. THEN, set the secret key on that instance
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# AND UPDATE get_db_connection() function to:
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        database=os.getenv('DB_NAME', 'realestate_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', '1234')
    )

def get_user_role(email):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT Email FROM Renter WHERE Email = %s', (email,))
            if cur.fetchone():
                return 'renter'
            cur.execute('SELECT Email FROM Agent WHERE Email = %s', (email,))
            if cur.fetchone():
                return 'agent'
    return None

@app.route('/')
def home():
    user = session.get('user')
    role = session.get('role')
    name = None
    if user:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT Name FROM "User" WHERE Email = %s', (user,))
                result = cur.fetchone()
                if result:
                    name = result[0]
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h1>Real Estate Management</h1>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                {% if user %}
                    <p>Welcome, {{ name }} ({{ role }})</p>
                    <nav>
                        {% if role == 'renter' %}
                            <a href="/addresses">Manage Addresses</a>
                            <a href="/cards">Manage Credit Cards</a>
                            <a href="/bookings">My Bookings</a>
                            <a href="/search">Search Properties</a>
                            <a href="/rewards">View Reward Points</a>
                            <a href="/rewards/history">Reward Points History</a>
                        {% elif role == 'agent' %}
                            <a href="/properties">Manage Properties</a>
                            <a href="/bookings">View Bookings</a>
                            <a href="/search">Search Properties</a>
                            <a href="/neighborhoods">Manage Neighborhoods</a>
                        {% endif %}
                        <a href="/logout">Logout</a>
                    </nav>
                {% else %}
                    <nav>
                        <a href="/login">Login</a>
                        <a href="/register">Register</a>
                    </nav>
                {% endif %}
            </div>
        </body>
        </html>
    ''', user=user, role=role, name=name)

# --- Authentication ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        role = get_user_role(email)
        if role:
            session['user'] = email
            session['role'] = role
            flash(f'Logged in as {email} ({role})')
            return redirect(url_for('home'))
        else:
            flash('Login failed: User not found.')
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Login</h2>
                <form method="post">
                    <div>
                        <label for="email">Email:</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    <input type="submit" value="Login">
                </form>
                <a href="/" class="btn">Back to Home</a>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
            </div>
        </body>
        </html>
    ''')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        user_type = request.form['user_type']
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 FROM "User" WHERE Email = %s', (email,))
                if cur.fetchone():
                    flash('Registration failed: Email already exists.')
                    return redirect(url_for('register'))
                cur.execute('INSERT INTO "User" (Email, Name) VALUES (%s, %s)', (email, name))
                if user_type == 'agent':
                    job_title = request.form.get('job_title')
                    agency = request.form.get('agency')
                    contact_info = request.form.get('contact_info')
                    cur.execute('INSERT INTO Agent (Email, Job_Title, Agency, Contact_Info) VALUES (%s, %s, %s, %s)', (email, job_title, agency, contact_info))
                elif user_type == 'renter':
                    budget = request.form.get('budget', 0.0)
                    move_in_date = request.form.get('move_in_date', '2025-01-01')
                    preferred_location = request.form.get('preferred_location', '')
                    join_rewards = request.form.get('join_rewards') == 'on'
                    cur.execute('INSERT INTO Renter (Email, Budget, Move_in_Date, Preferred_Location) VALUES (%s, %s, %s, %s)', (email, budget, move_in_date, preferred_location))
                    if join_rewards:
                        cur.execute('INSERT INTO RewardProgram (Email, Points) VALUES (%s, %s)', (email, 0))
                conn.commit()
                flash('Registration successful! Please login.')
                return redirect(url_for('login'))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Register - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Register</h2>
                <form method="post">
                    <div>
                        <label for="name">Name:</label>
                        <input type="text" id="name" name="name" required>
                    </div>
                    <div>
                        <label for="email">Email:</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    <div>
                        <label for="user_type">Role:</label>
                        <select id="user_type" name="user_type" required>
                            <option value="renter">Renter</option>
                            <option value="agent">Agent</option>
                        </select>
                    </div>
                    <div id="agent-fields" style="display:none;">
                        <div>
                            <label for="job_title">Job Title:</label>
                            <input type="text" id="job_title" name="job_title">
                        </div>
                        <div>
                            <label for="agency">Agency:</label>
                            <input type="text" id="agency" name="agency">
                        </div>
                        <div>
                            <label for="contact_info">Contact Info:</label>
                            <input type="text" id="contact_info" name="contact_info">
                        </div>
                    </div>
                    <div id="renter-fields" style="display:none;">
                        <div>
                            <label for="budget">Budget:</label>
                            <input type="number" id="budget" name="budget" step="0.01">
                        </div>
                        <div>
                            <label for="move_in_date">Move-in Date:</label>
                            <input type="date" id="move_in_date" name="move_in_date">
                        </div>
                        <div>
                            <label for="preferred_location">Preferred Location:</label>
                            <input type="text" id="preferred_location" name="preferred_location">
                        </div>
                        <div>
                            <label>
                                <input type="checkbox" id="join_rewards" name="join_rewards"> Join Reward Program
                            </label>
                        </div>
                    </div>
                    <input type="submit" value="Register">
                </form>
                <a href="/" class="btn">Back to Home</a>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
            </div>
            <script>
                function toggleFields() {
                    var userType = document.getElementById('user_type').value;
                    document.getElementById('agent-fields').style.display = userType === 'agent' ? 'block' : 'none';
                    document.getElementById('renter-fields').style.display = userType === 'renter' ? 'block' : 'none';
                }
                document.getElementById('user_type').addEventListener('change', toggleFields);
                window.onload = toggleFields;
            </script>
        </body>
        </html>
    ''')

# --- Address Management (Renter) ---

@app.route('/addresses')
def addresses():
    if session.get('role') != 'renter':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT AddressID, Street, City, State, Zip, Primary_Address FROM Address WHERE Email = %s', (email,))
            addresses = cur.fetchall()
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Addresses - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Your Addresses</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <a href="{{ url_for('add_address') }}" class="btn">Add Address</a>
                <div class="property-details">
                    {% for addr in addresses %}
                        <div class="address-card">
                            <h3>Address ID: {{ addr[0] }}</h3>
                            <p>{{ addr[1] }}, {{ addr[2] }}, {{ addr[3] }} {{ addr[4] }}</p>
                            <p>Primary: {{ 'Yes' if addr[5] else 'No' }}</p>
                            <div class="btn-group">
                                <a href="{{ url_for('edit_address', address_id=addr[0]) }}" class="btn">Edit</a>
                                <a href="{{ url_for('delete_address', address_id=addr[0]) }}" class="btn btn-danger">Delete</a>
                            </div>
                        </div>
                    {% endfor %}
                </div>
                <a href="/" class="btn">Back to Home</a>
            </div>
        </body>
        </html>
    ''', addresses=addresses)

@app.route('/addresses/add', methods=['GET', 'POST'])
def add_address():
    if session.get('role') != 'renter':
        abort(403)
    if request.method == 'POST':
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip']
        primary = request.form.get('primary') == 'on'
        email = session['user']
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if primary:
                    cur.execute('UPDATE Address SET Primary_Address = FALSE WHERE Email = %s', (email,))
                cur.execute('INSERT INTO Address (Street, City, State, Zip, Email, Primary_Address) VALUES (%s, %s, %s, %s, %s, %s)', (street, city, state, zip_code, email, primary))
                conn.commit()
        flash('Address added!')
        return redirect(url_for('addresses'))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Add Address - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Add Address</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <form method="post">
                    <div>
                        <label for="street">Street:</label>
                        <input type="text" id="street" name="street" required>
                    </div>
                    <div>
                        <label for="city">City:</label>
                        <input type="text" id="city" name="city" required>
                    </div>
                    <div>
                        <label for="state">State:</label>
                        <input type="text" id="state" name="state" required>
                    </div>
                    <div>
                        <label for="zip">Zip:</label>
                        <input type="text" id="zip" name="zip" required>
                    </div>
                    <div>
                        <label>
                            <input type="checkbox" name="primary"> Primary Address
                        </label>
                    </div>
                    <div class="btn-group">
                        <input type="submit" value="Add" class="btn">
                        <a href="{{ url_for('addresses') }}" class="btn">Back</a>
                    </div>
                </form>
            </div>
        </body>
        </html>
    ''')

@app.route('/addresses/edit/<int:address_id>', methods=['GET', 'POST'])
def edit_address(address_id):
    if session.get('role') != 'renter':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT Street, City, State, Zip, Primary_Address FROM Address WHERE Email = %s AND AddressID = %s', (email, address_id))
            addr = cur.fetchone()
            if not addr:
                abort(404)
            if request.method == 'POST':
                street = request.form['street']
                city = request.form['city']
                state = request.form['state']
                zip_code = request.form['zip']
                primary = request.form.get('primary') == 'on'
                if primary:
                    cur.execute('UPDATE Address SET Primary_Address = FALSE WHERE Email = %s', (email,))
                cur.execute('UPDATE Address SET Street=%s, City=%s, State=%s, Zip=%s, Primary_Address=%s WHERE Email=%s AND AddressID=%s',
                            (street, city, state, zip_code, primary, email, address_id))
                conn.commit()
                flash('Address updated!')
                return redirect(url_for('addresses'))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Edit Address - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Edit Address</h2>
                <form method="post">
                    <div>
                        <label for="street">Street:</label>
                        <input type="text" id="street" name="street" value="{{ addr[0] }}" required>
                    </div>
                    <div>
                        <label for="city">City:</label>
                        <input type="text" id="city" name="city" value="{{ addr[1] }}" required>
                    </div>
                    <div>
                        <label for="state">State:</label>
                        <input type="text" id="state" name="state" value="{{ addr[2] }}" required>
                    </div>
                    <div>
                        <label for="zip">Zip:</label>
                        <input type="text" id="zip" name="zip" value="{{ addr[3] }}" required>
                    </div>
                    <div>
                        <label>
                            <input type="checkbox" name="primary" {% if addr[4] %}checked{% endif %}> Primary Address
                        </label>
                    </div>
                    <input type="submit" value="Update">
                </form>
                <a href="{{ url_for('addresses') }}" class="btn">Back</a>
            </div>
        </body>
        </html>
    ''', addr=addr)

@app.route('/addresses/delete/<int:address_id>')
def delete_address(address_id):
    if session.get('role') != 'renter':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check if address is used as billing address for any credit cards
            cur.execute('''
                SELECT 1 FROM CreditCard 
                WHERE Billing_Address = %s AND Renter_Email = %s
            ''', (address_id, email))
            if cur.fetchone():
                flash('Cannot delete: Address is used as billing address for a credit card.')
                return redirect(url_for('addresses'))
            
            # Check if address is used in any bookings
            cur.execute('''
                SELECT 1 FROM Booking b
                JOIN Property p ON b.Property_ID = p.Property_ID
                WHERE p.Street = (SELECT Street FROM Address WHERE AddressID = %s)
                AND p.City = (SELECT City FROM Address WHERE AddressID = %s)
                AND p.State = (SELECT State FROM Address WHERE AddressID = %s)
                AND p.Zip = (SELECT Zip FROM Address WHERE AddressID = %s)
            ''', (address_id, address_id, address_id, address_id))
            if cur.fetchone():
                flash('Cannot delete: Address is associated with an active booking.')
                return redirect(url_for('addresses'))
            
            # If no dependencies, delete the address
            cur.execute('DELETE FROM Address WHERE Email = %s AND AddressID = %s', (email, address_id))
            conn.commit()
    flash('Address deleted!')
    return redirect(url_for('addresses'))

# --- Credit Card Management (Renter) ---

@app.route('/cards')
def cards():
    if session.get('role') != 'renter':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT c.Card_Number, c.CVV, c.Expiry_Date, c.Billing_Address,
                       a.Street, a.City, a.State, a.Zip
                FROM CreditCard c
                LEFT JOIN Address a ON c.Billing_Address = a.AddressID AND c.Renter_Email = a.Email
                WHERE c.Renter_Email = %s
            ''', (email,))
            cards = cur.fetchall()
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Credit Cards - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Your Credit Cards</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <a href="{{ url_for('add_card') }}" class="btn">Add Credit Card</a>
                <div class="property-details">
                    {% for card in cards %}
                        <div class="credit-card">
                            <h3>Card Number: {{ card[0] }}</h3>
                            <p>CVV: {{ card[1] }}</p>
                            <p>Expiry: {{ card[2].strftime('%m/%Y') }}</p>
                            <p>Billing Address: {{ card[4] }}, {{ card[5] }}, {{ card[6] }} {{ card[7] if card[4] else 'N/A' }}</p>
                            <div class="btn-group">
                                <a href="{{ url_for('edit_card', card_number=card[0]) }}" class="btn">Edit</a>
                                <a href="{{ url_for('delete_card', card_number=card[0]) }}" class="btn btn-danger">Delete</a>
                            </div>
                        </div>
                    {% endfor %}
                </div>
                <a href="/" class="btn">Back to Home</a>
            </div>
        </body>
        </html>
    ''', cards=cards)

@app.route('/cards/add', methods=['GET', 'POST'])
def add_card():
    if session.get('role') != 'renter':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT AddressID, Street, City, State, Zip FROM Address WHERE Email = %s', (email,))
            addresses = cur.fetchall()
    if request.method == 'POST':
        card_number = request.form['card_number']
        cvv = request.form['cvv']
        expiry_month = request.form['expiry_month']
        expiry_year = request.form['expiry_year']
        billing_address = request.form['billing_address']
        
        if not (card_number.isdigit() and len(card_number) == 16):
            flash('Card number must be 16 digits.')
            return redirect(url_for('add_card'))
        if not (cvv.isdigit() and len(cvv) == 3):
            flash('CVV must be 3 digits.')
            return redirect(url_for('add_card'))
            
        try:
            expiry_date = datetime(int(expiry_year), int(expiry_month), 1)
            if expiry_date <= datetime.now():
                flash('Card has expired.')
                return redirect(url_for('add_card'))
        except ValueError:
            flash('Invalid expiry date.')
            return redirect(url_for('add_card'))
            
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 FROM Address WHERE Email = %s AND AddressID = %s', (email, billing_address))
                if not cur.fetchone():
                    flash('Billing address does not exist or does not belong to you.')
                    return redirect(url_for('add_card'))
                # Check if card already exists
                cur.execute('SELECT 1 FROM CreditCard WHERE Renter_Email = %s AND Card_Number = %s', (email, card_number))
                if cur.fetchone():
                    flash('This card is already registered.')
                    return redirect(url_for('add_card'))
                cur.execute('''
                    INSERT INTO CreditCard (Card_Number, CVV, Expiry_Date, Renter_Email, Billing_Address)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (card_number, cvv, expiry_date, email, billing_address))
                conn.commit()
        flash('Credit card added!')
        return redirect(url_for('cards'))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Add Credit Card - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Add Credit Card</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <form method="post">
                    <div>
                        <label for="card_number">Card Number:</label>
                        <input type="text" id="card_number" name="card_number" maxlength="16" required>
                    </div>
                    <div>
                        <label for="cvv">CVV:</label>
                        <input type="text" id="cvv" name="cvv" maxlength="3" required>
                    </div>
                    <div>
                        <label for="expiry_month">Expiry Month:</label>
                        <select id="expiry_month" name="expiry_month" required>
                            {% for month in range(1, 13) %}
                                <option value="{{ '%02d' % month }}">{{ '%02d' % month }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div>
                        <label for="expiry_year">Expiry Year:</label>
                        <select id="expiry_year" name="expiry_year" required>
                            {% for year in range(datetime.now().year, datetime.now().year + 10) %}
                                <option value="{{ year }}">{{ year }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div>
                        <label for="billing_address">Billing Address:</label>
                        <select id="billing_address" name="billing_address" required>
                            {% for addr in addresses %}
                                <option value="{{ addr[0] }}">{{ addr[1] }}, {{ addr[2] }}, {{ addr[3] }} {{ addr[4] }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="btn-group">
                        <input type="submit" value="Add" class="btn">
                        <a href="{{ url_for('cards') }}" class="btn">Back</a>
                    </div>
                </form>
            </div>
        </body>
        </html>
    ''', addresses=addresses, datetime=datetime)

@app.route('/cards/edit/<card_number>', methods=['GET', 'POST'])
def edit_card(card_number):
    if session.get('role') != 'renter':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT CVV, Expiry_Date, Billing_Address FROM CreditCard WHERE Renter_Email = %s AND Card_Number = %s', (email, card_number))
            card = cur.fetchone()
            if not card:
                abort(404)
            cur.execute('SELECT AddressID, Street, City, State, Zip FROM Address WHERE Email = %s', (email,))
            addresses = cur.fetchall()
    if request.method == 'POST':
        cvv = request.form['cvv']
        expiry_month = request.form['expiry_month']
        expiry_year = request.form['expiry_year']
        billing_address = request.form['billing_address']
        if not (cvv.isdigit() and len(cvv) == 3):
            flash('CVV must be 3 digits.')
            return redirect(url_for('edit_card', card_number=card_number))
        try:
            expiry_date = datetime(int(expiry_year), int(expiry_month), 1)
            if expiry_date <= datetime.now():
                flash('Card has expired.')
                return redirect(url_for('edit_card', card_number=card_number))
        except ValueError:
            flash('Invalid expiry date.')
            return redirect(url_for('edit_card', card_number=card_number))
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE CreditCard SET CVV=%s, Expiry_Date=%s, Billing_Address=%s WHERE Renter_Email=%s AND Card_Number=%s',
                            (cvv, expiry_date, billing_address, email, card_number))
                conn.commit()
        flash('Credit card updated!')
        return redirect(url_for('cards'))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Edit Credit Card - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Edit Credit Card</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <form method="post">
                    <div>
                        <label for="card_number">Card Number:</label>
                        <input type="text" id="card_number" value="{{ card_number }}" disabled>
                    </div>
                    <div>
                        <label for="cvv">CVV:</label>
                        <input type="text" id="cvv" name="cvv" maxlength="3" value="{{ card[0] }}" required>
                    </div>
                    <div>
                        <label for="expiry_month">Expiry Month:</label>
                        <select id="expiry_month" name="expiry_month" required>
                            {% for month in range(1, 13) %}
                                <option value="{{ '%02d' % month }}" {% if card[1].month == month %}selected{% endif %}>{{ '%02d' % month }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div>
                        <label for="expiry_year">Expiry Year:</label>
                        <select id="expiry_year" name="expiry_year" required>
                            {% for year in range(datetime.now().year, datetime.now().year + 10) %}
                                <option value="{{ year }}" {% if card[1].year == year %}selected{% endif %}>{{ year }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div>
                        <label for="billing_address">Billing Address:</label>
                        <select id="billing_address" name="billing_address" required>
                            {% for addr in addresses %}
                                <option value="{{ addr[0] }}" {% if addr[0] == card[2] %}selected{% endif %}>{{ addr[1] }}, {{ addr[2] }}, {{ addr[3] }} {{ addr[4] }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="btn-group">
                        <input type="submit" value="Update" class="btn">
                        <a href="{{ url_for('cards') }}" class="btn">Back</a>
                    </div>
                </form>
            </div>
        </body>
        </html>
    ''', card=card, card_number=card_number, addresses=addresses, datetime=datetime)

@app.route('/cards/delete/<card_number>')
def delete_card(card_number):
    if session.get('role') != 'renter':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM Booking WHERE Renter_Email = %s AND Card_Number = %s', (email, card_number))
            if cur.fetchone():
                flash('Cannot delete: Card is used in a booking.')
                return redirect(url_for('cards'))
            cur.execute('DELETE FROM CreditCard WHERE Renter_Email = %s AND Card_Number = %s', (email, card_number))
            conn.commit()
    flash('Credit card deleted!')
    return redirect(url_for('cards'))

# --- Neighborhood Management (Agent, BONUS) ---
# (Paste the full neighborhood management code from previous responses here.)

# --- Property Management (Agent) ---

@app.route('/properties')
def properties():
    if session.get('role') != 'agent':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT p.Property_ID, p.Street, p.City, p.State, p.Zip, p.Price, p.Availability, 
                       p.Square_Footage, p.Description, p.Type, n.Name,
                       COALESCE(h.Number_of_rooms, a.Number_of_rooms, v.Number_of_rooms, NULL) as Bedrooms,
                       a.Floor, l.Purpose_of_land, c.Business_Type
                FROM Property p
                LEFT JOIN House h ON p.Property_ID = h.Property_ID
                LEFT JOIN Apartment a ON p.Property_ID = a.Property_ID
                LEFT JOIN Vacation_Home v ON p.Property_ID = v.Property_ID
                LEFT JOIN Land l ON p.Property_ID = l.Property_ID
                LEFT JOIN Commercial_Building c ON p.Property_ID = c.Property_ID
                LEFT JOIN Neighborhood n ON p.Neighborhood = n.Name
                WHERE p.Agent_Email = %s
            ''', (email,))
            properties = cur.fetchall()
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Properties - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Your Properties</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <a href="{{ url_for('add_property') }}" class="btn">Add Property</a>
                <div class="property-details">
                    {% for prop in properties %}
                        <div class="property-card">
                            <h3>Property ID: {{ prop[0] }}</h3>
                            <p>Address: {{ prop[1] }}, {{ prop[2] }}, {{ prop[3] }} {{ prop[4] }}</p>
                            <p>Price: ${{ prop[5] }}</p>
                            <p>Status: {{ 'Available' if prop[6] else 'Unavailable' }}</p>
                            <p>Square Footage: {{ prop[7] }}</p>
                            <p>Description: {{ prop[8] }}</p>
                            <p>Type: {{ prop[9] }}</p>
                            <p>Neighborhood: {{ prop[10] if prop[10] else 'N/A' }}</p>
                            {% if prop[11] %}
                                <p>Bedrooms: {{ prop[11] }}</p>
                            {% endif %}
                            {% if prop[9] == 'Apartment' and prop[12] %}
                                <p>Floor: {{ prop[12] }}</p>
                            {% elif prop[9] == 'Land' and prop[13] %}
                                <p>Purpose: {{ prop[13] }}</p>
                            {% elif prop[9] == 'Commercial Building' and prop[14] %}
                                <p>Business Type: {{ prop[14] }}</p>
                            {% endif %}
                            <div class="btn-group">
                                <a href="{{ url_for('edit_property', property_id=prop[0]) }}" class="btn">Edit</a>
                                <a href="{{ url_for('delete_property', property_id=prop[0]) }}" class="btn btn-danger">Delete</a>
                            </div>
                        </div>
                    {% endfor %}
                </div>
                <a href="/" class="btn">Back to Home</a>
            </div>
        </body>
        </html>
    ''', properties=properties)

@app.route('/properties/add', methods=['GET', 'POST'])
def add_property():
    if session.get('role') != 'agent':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT Name FROM Neighborhood')
            neighborhoods = cur.fetchall()
    if request.method == 'POST':
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip']
        price = request.form['price']
        available = 'available' in request.form
        square_footage = request.form['square_footage']
        description = request.form['description']
        property_type = request.form['type']
        neighborhood = request.form['neighborhood']
        
        # Property type specific fields
        number_of_rooms = request.form.get('number_of_rooms')
        building_type = request.form.get('building_type')
        purpose_of_land = request.form.get('purpose_of_land')
        business_type = request.form.get('business_type')
        
        try:
            price = float(price)
            square_footage = float(square_footage)
            if number_of_rooms:
                number_of_rooms = int(number_of_rooms)
        except ValueError:
            flash('Invalid numeric values provided.')
            return redirect(url_for('add_property'))
            
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Insert into Property table
                cur.execute('''
                    INSERT INTO Property (Street, City, State, Zip, Price, Availability, Square_Footage, 
                                        Description, Type, Agent_Email, Neighborhood)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING Property_ID
                ''', (street, city, state, zip_code, price, available, square_footage, 
                      description, property_type, email, neighborhood))
                property_id = cur.fetchone()[0]
                
                # Insert into specific property type table
                if property_type == 'House':
                    cur.execute('INSERT INTO House (Property_ID, Number_of_rooms) VALUES (%s, %s)',
                              (property_id, number_of_rooms))
                elif property_type == 'Apartment':
                    cur.execute('INSERT INTO Apartment (Property_ID, Number_of_rooms, Floor) VALUES (%s, %s, %s)',
                              (property_id, number_of_rooms, building_type))
                elif property_type == 'Commercial Building':
                    cur.execute('INSERT INTO Commercial_Building (Property_ID, Business_Type) VALUES (%s, %s)',
                              (property_id, business_type))
                elif property_type == 'Land':
                    cur.execute('INSERT INTO Land (Property_ID, Purpose_of_land) VALUES (%s, %s)',
                              (property_id, purpose_of_land))
                elif property_type == 'Vacation Home':
                    cur.execute('INSERT INTO Vacation_Home (Property_ID, Number_of_rooms) VALUES (%s, %s)',
                              (property_id, number_of_rooms))
                
                conn.commit()
        flash('Property added!')
        return redirect(url_for('properties'))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Add Property - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Add Property</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <form method="post">
                    <div>
                        <label for="street">Street:</label>
                        <input type="text" id="street" name="street" required>
                    </div>
                    <div>
                        <label for="city">City:</label>
                        <input type="text" id="city" name="city" required>
                    </div>
                    <div>
                        <label for="state">State:</label>
                        <input type="text" id="state" name="state" required>
                    </div>
                    <div>
                        <label for="zip">Zip:</label>
                        <input type="text" id="zip" name="zip" required>
                    </div>
                    <div>
                        <label for="price">Price:</label>
                        <input type="number" id="price" name="price" step="0.01" required>
                    </div>
                    <div>
                        <label for="available">Available:</label>
                        <input type="checkbox" id="available" name="available">
                    </div>
                    <div>
                        <label for="square_footage">Square Footage:</label>
                        <input type="number" id="square_footage" name="square_footage" step="0.01" required>
                    </div>
                    <div>
                        <label for="description">Description:</label>
                        <textarea id="description" name="description" required></textarea>
                    </div>
                    <div>
                        <label for="type">Type:</label>
                        <select id="type" name="type" required onchange="showTypeSpecificFields()">
                            <option value="House">House</option>
                            <option value="Apartment">Apartment</option>
                            <option value="Commercial Building">Commercial Building</option>
                            <option value="Vacation Home">Vacation Home</option>
                            <option value="Land">Land</option>
                        </select>
                    </div>
                    <div id="rooms-field" style="display: none;">
                        <label for="number_of_rooms">Number of Rooms:</label>
                        <input type="number" id="number_of_rooms" name="number_of_rooms" min="1">
                    </div>
                    <div id="building-type-field" style="display: none;">
                        <label for="building_type">Floor:</label>
                        <input type="number" id="building_type" name="building_type" min="1">
                    </div>
                    <div id="business-type-field" style="display: none;">
                        <label for="business_type">Business Type:</label>
                        <input type="text" id="business_type" name="business_type">
                    </div>
                    <div id="purpose-field" style="display: none;">
                        <label for="purpose_of_land">Purpose of Land:</label>
                        <textarea id="purpose_of_land" name="purpose_of_land"></textarea>
                    </div>
                    <div>
                        <label for="neighborhood">Neighborhood:</label>
                        <select id="neighborhood" name="neighborhood" required>
                            {% for n in neighborhoods %}
                                <option value="{{ n[0] }}">{{ n[0] }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="btn-group">
                        <input type="submit" value="Add" class="btn">
                        <a href="{{ url_for('properties') }}" class="btn">Back</a>
                    </div>
                </form>
            </div>
            <script>
                function showTypeSpecificFields() {
                    const type = document.getElementById('type').value;
                    document.getElementById('rooms-field').style.display = 
                        (type === 'House' || type === 'Apartment' || type === 'Vacation Home') ? 'block' : 'none';
                    document.getElementById('building-type-field').style.display = 
                        type === 'Apartment' ? 'block' : 'none';
                    document.getElementById('business-type-field').style.display = 
                        type === 'Commercial Building' ? 'block' : 'none';
                    document.getElementById('purpose-field').style.display = 
                        type === 'Land' ? 'block' : 'none';
                }
                // Initialize fields on page load
                showTypeSpecificFields();
            </script>
        </body>
        </html>
    ''', neighborhoods=neighborhoods)

@app.route('/properties/edit/<int:property_id>', methods=['GET', 'POST'])
def edit_property(property_id):
    if session.get('role') != 'agent':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT p.Street, p.City, p.State, p.Zip, p.Price, p.Availability, p.Square_Footage, 
                       p.Description, p.Type, p.Neighborhood,
                       COALESCE(h.Number_of_rooms, a.Number_of_rooms, v.Number_of_rooms, NULL) as Bedrooms,
                       a.Floor, l.Purpose_of_land, c.Business_Type
                FROM Property p
                LEFT JOIN House h ON p.Property_ID = h.Property_ID
                LEFT JOIN Apartment a ON p.Property_ID = a.Property_ID
                LEFT JOIN Vacation_Home v ON p.Property_ID = v.Property_ID
                LEFT JOIN Land l ON p.Property_ID = l.Property_ID
                LEFT JOIN Commercial_Building c ON p.Property_ID = c.Property_ID
                WHERE p.Property_ID = %s AND p.Agent_Email = %s
            ''', (property_id, email))
            property = cur.fetchone()
            if not property:
                abort(404)
            cur.execute('SELECT Name FROM Neighborhood')
            neighborhoods = cur.fetchall()
    if request.method == 'POST':
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip']
        price = request.form['price']
        available = 'available' in request.form
        square_footage = request.form['square_footage']
        description = request.form['description']
        property_type = request.form['type']
        neighborhood = request.form['neighborhood']
        
        # Property type specific fields
        number_of_rooms = request.form.get('number_of_rooms')
        building_type = request.form.get('building_type')
        purpose_of_land = request.form.get('purpose_of_land')
        business_type = request.form.get('business_type')
        
        try:
            price = float(price)
            square_footage = float(square_footage)
            if number_of_rooms:
                number_of_rooms = int(number_of_rooms)
        except ValueError:
            flash('Invalid numeric values provided.')
            return redirect(url_for('edit_property', property_id=property_id))
            
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Update Property table
                cur.execute('''
                    UPDATE Property
                    SET Street = %s, City = %s, State = %s, Zip = %s, Price = %s, 
                        Availability = %s, Square_Footage = %s, Description = %s, 
                        Type = %s, Neighborhood = %s
                    WHERE Property_ID = %s AND Agent_Email = %s
                ''', (street, city, state, zip_code, price, available, square_footage, 
                      description, property_type, neighborhood, property_id, email))
                
                # Delete old property type record
                cur.execute('DELETE FROM House WHERE Property_ID = %s', (property_id,))
                cur.execute('DELETE FROM Apartment WHERE Property_ID = %s', (property_id,))
                cur.execute('DELETE FROM Commercial_Building WHERE Property_ID = %s', (property_id,))
                cur.execute('DELETE FROM Land WHERE Property_ID = %s', (property_id,))
                cur.execute('DELETE FROM Vacation_Home WHERE Property_ID = %s', (property_id,))
                
                # Insert new property type record
                if property_type == 'House':
                    cur.execute('INSERT INTO House (Property_ID, Number_of_rooms) VALUES (%s, %s)',
                              (property_id, number_of_rooms))
                elif property_type == 'Apartment':
                    cur.execute('INSERT INTO Apartment (Property_ID, Number_of_rooms, Floor) VALUES (%s, %s, %s)',
                              (property_id, number_of_rooms, building_type))
                elif property_type == 'Commercial Building':
                    cur.execute('INSERT INTO Commercial_Building (Property_ID, Business_Type) VALUES (%s, %s)',
                              (property_id, business_type))
                elif property_type == 'Land':
                    cur.execute('INSERT INTO Land (Property_ID, Purpose_of_land) VALUES (%s, %s)',
                              (property_id, purpose_of_land))
                elif property_type == 'Vacation Home':
                    cur.execute('INSERT INTO Vacation_Home (Property_ID, Number_of_rooms) VALUES (%s, %s)',
                              (property_id, number_of_rooms))
                
                conn.commit()
        flash('Property updated!')
        return redirect(url_for('properties'))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Edit Property - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Edit Property</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <form method="post">
                    <div>
                        <label for="street">Street:</label>
                        <input type="text" id="street" name="street" value="{{ property[0] }}" required>
                    </div>
                    <div>
                        <label for="city">City:</label>
                        <input type="text" id="city" name="city" value="{{ property[1] }}" required>
                    </div>
                    <div>
                        <label for="state">State:</label>
                        <input type="text" id="state" name="state" value="{{ property[2] }}" required>
                    </div>
                    <div>
                        <label for="zip">Zip:</label>
                        <input type="text" id="zip" name="zip" value="{{ property[3] }}" required>
                    </div>
                    <div>
                        <label for="price">Price:</label>
                        <input type="number" id="price" name="price" step="0.01" value="{{ property[4] }}" required>
                    </div>
                    <div>
                        <label for="available">Available:</label>
                        <input type="checkbox" id="available" name="available" {% if property[5] %}checked{% endif %}>
                    </div>
                    <div>
                        <label for="square_footage">Square Footage:</label>
                        <input type="number" id="square_footage" name="square_footage" step="0.01" value="{{ property[6] }}" required>
                    </div>
                    <div>
                        <label for="description">Description:</label>
                        <textarea id="description" name="description" required>{{ property[7] }}</textarea>
                    </div>
                    <div>
                        <label for="type">Type:</label>
                        <select id="type" name="type" required onchange="showTypeSpecificFields()">
                            <option value="House" {% if property[8] == 'House' %}selected{% endif %}>House</option>
                            <option value="Apartment" {% if property[8] == 'Apartment' %}selected{% endif %}>Apartment</option>
                            <option value="Commercial Building" {% if property[8] == 'Commercial Building' %}selected{% endif %}>Commercial Building</option>
                            <option value="Vacation Home" {% if property[8] == 'Vacation Home' %}selected{% endif %}>Vacation Home</option>
                            <option value="Land" {% if property[8] == 'Land' %}selected{% endif %}>Land</option>
                        </select>
                    </div>
                    <div id="rooms-field" style="display: none;">
                        <label for="number_of_rooms">Number of Rooms:</label>
                        <input type="number" id="number_of_rooms" name="number_of_rooms" min="1" value="{{ property[10] if property[10] else '' }}">
                    </div>
                    <div id="building-type-field" style="display: none;">
                        <label for="building_type">Floor:</label>
                        <input type="number" id="building_type" name="building_type" min="1" value="{{ property[11] if property[8] == 'Apartment' and property[11] else '' }}">
                    </div>
                    <div id="business-type-field" style="display: none;">
                        <label for="business_type">Business Type:</label>
                        <input type="text" id="business_type" name="business_type" value="{{ property[13] if property[8] == 'Commercial Building' and property[13] else '' }}">
                    </div>
                    <div id="purpose-field" style="display: none;">
                        <label for="purpose_of_land">Purpose of Land:</label>
                        <textarea id="purpose_of_land" name="purpose_of_land">{{ property[12] if property[8] == 'Land' and property[12] else '' }}</textarea>
                    </div>
                    <div>
                        <label for="neighborhood">Neighborhood:</label>
                        <select id="neighborhood" name="neighborhood" required>
                            {% for n in neighborhoods %}
                                <option value="{{ n[0] }}" {% if n[0] == property[9] %}selected{% endif %}>{{ n[0] }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="btn-group">
                        <input type="submit" value="Update" class="btn">
                        <a href="{{ url_for('properties') }}" class="btn">Back</a>
                    </div>
                </form>
            </div>
            <script>
                function showTypeSpecificFields() {
                    const type = document.getElementById('type').value;
                    document.getElementById('rooms-field').style.display = 
                        (type === 'House' || type === 'Apartment' || type === 'Vacation Home') ? 'block' : 'none';
                    document.getElementById('building-type-field').style.display = 
                        type === 'Apartment' ? 'block' : 'none';
                    document.getElementById('business-type-field').style.display = 
                        type === 'Commercial Building' ? 'block' : 'none';
                    document.getElementById('purpose-field').style.display = 
                        type === 'Land' ? 'block' : 'none';
                }
                // Initialize fields on page load
                showTypeSpecificFields();
            </script>
        </body>
        </html>
    ''', property=property, neighborhoods=neighborhoods)

@app.route('/properties/delete/<int:property_id>')
def delete_property(property_id):
    if session.get('role') != 'agent':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # First check if property exists and belongs to the agent
            cur.execute('SELECT Type FROM Property WHERE Property_ID = %s AND Agent_Email = %s', (property_id, email))
            property_type = cur.fetchone()
            if not property_type:
                flash('Property not found or you do not have permission to delete it.')
                return redirect(url_for('properties'))

            # Check for bookings
            cur.execute('SELECT 1 FROM Booking WHERE Property_ID = %s', (property_id,))
            if cur.fetchone():
                flash('Cannot delete: Property has bookings.')
                return redirect(url_for('properties'))

            # Delete from property-specific table first
            if property_type[0] == 'House':
                cur.execute('DELETE FROM House WHERE Property_ID = %s', (property_id,))
            elif property_type[0] == 'Apartment':
                cur.execute('DELETE FROM Apartment WHERE Property_ID = %s', (property_id,))
            elif property_type[0] == 'Commercial Building':
                cur.execute('DELETE FROM Commercial_Building WHERE Property_ID = %s', (property_id,))
            elif property_type[0] == 'Land':
                cur.execute('DELETE FROM Land WHERE Property_ID = %s', (property_id,))
            elif property_type[0] == 'Vacation Home':
                cur.execute('DELETE FROM Vacation_Home WHERE Property_ID = %s', (property_id,))

            # Finally delete from Property table
            cur.execute('DELETE FROM Property WHERE Property_ID = %s', (property_id,))
            conn.commit()
    flash('Property deleted!')
    return redirect(url_for('properties'))

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    if request.method == 'POST':
        location = request.form['location']
        ptype = request.form.get('ptype')
        min_bed = request.form.get('min_bed')
        max_bed = request.form.get('max_bed')
        min_price = request.form.get('min_price')
        max_price = request.form.get('max_price')
        order_by = request.form.get('order_by')
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = '''
                    SELECT p.Property_ID, p.Street, p.City, p.State, p.Zip, p.Price, p.Type, p.Description, 
                        COALESCE(h.Number_of_rooms, a.Number_of_rooms, v.Number_of_rooms, NULL) as Bedrooms,
                        p.Square_Footage, p.Neighborhood, n.Crime_Rate, n.Nearby_Schools,
                        a.Floor, l.Purpose_of_land, c.Business_Type
                    FROM Property p
                    LEFT JOIN House h ON p.Property_ID = h.Property_ID
                    LEFT JOIN Apartment a ON p.Property_ID = a.Property_ID
                    LEFT JOIN Vacation_Home v ON p.Property_ID = v.Property_ID
                    LEFT JOIN Land l ON p.Property_ID = l.Property_ID
                    LEFT JOIN Commercial_Building c ON p.Property_ID = c.Property_ID
                    LEFT JOIN Neighborhood n ON p.Neighborhood = n.Name
                    WHERE p.Availability = TRUE
                '''
                params = []
                if location:
                    query += ' AND p.City = %s'
                    params.append(location)
                if ptype:
                    query += ' AND p.Type = %s'
                    params.append(ptype)
                if min_bed:
                    query += ' AND COALESCE(h.Number_of_rooms, a.Number_of_rooms, v.Number_of_rooms, 0) >= %s'
                    params.append(min_bed)
                if max_bed:
                    query += ' AND COALESCE(h.Number_of_rooms, a.Number_of_rooms, v.Number_of_rooms, 100) <= %s'
                    params.append(max_bed)
                if min_price:
                    query += ' AND p.Price >= %s'
                    params.append(min_price)
                if max_price:
                    query += ' AND p.Price <= %s'
                    params.append(max_price)
                if order_by in ['price', 'bedrooms']:
                    query += f' ORDER BY { "p.Price" if order_by == "price" else "Bedrooms" }'
                cur.execute(query, params)
                results = cur.fetchall()
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Search Properties - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Search Properties</h2>
                <form method="post" class="search-form">
                    <div>
                        <label for="location">City:</label>
                        <input type="text" id="location" name="location">
                    </div>
                    <div>
                        <label for="ptype">Type:</label>
                        <select id="ptype" name="ptype">
                            <option value="">Any</option>
                            <option value="House">House</option>
                            <option value="Apartment">Apartment</option>
                            <option value="Commercial Building">Commercial Building</option>
                            <option value="Vacation Home">Vacation Home</option>
                            <option value="Land">Land</option>
                        </select>
                    </div>
                    <div>
                        <label for="min_bed">Min Bedrooms:</label>
                        <input type="number" id="min_bed" name="min_bed" min="0">
                    </div>
                    <div>
                        <label for="max_bed">Max Bedrooms:</label>
                        <input type="number" id="max_bed" name="max_bed" min="0">
                    </div>
                    <div>
                        <label for="min_price">Min Price:</label>
                        <input type="number" id="min_price" name="min_price" min="0">
                    </div>
                    <div>
                        <label for="max_price">Max Price:</label>
                        <input type="number" id="max_price" name="max_price" min="0">
                    </div>
                    <div>
                        <label for="order_by">Order by:</label>
                        <select id="order_by" name="order_by">
                            <option value="">None</option>
                            <option value="price">Price</option>
                            <option value="bedrooms">Bedrooms</option>
                        </select>
                    </div>
                    <div>
                        <input type="submit" value="Search" class="btn">
                    </div>
                </form>
                <div class="property-details">
                    {% for r in results %}
                        <div class="property-card">
                            <h3>Property ID: {{ r[0] }}</h3>
                            <p>Address: {{ r[1] }}, {{ r[2] }}, {{ r[3] }} {{ r[4] }}</p>
                            <p class="price">Price: ${{ r[5] }}</p>
                            <p>Type: {{ r[6] }}</p>
                            <p>Description: {{ r[7] }}</p>
                            <p>Bedrooms: {{ r[8] if r[8] else 'N/A' }}</p>
                            <p>Square Footage: {{ r[9] }}</p>
                            <div class="neighborhood-info">
                                <p>Neighborhood: {{ r[10] if r[10] else 'N/A' }}</p>
                                <p>Crime Rate: {{ r[11] if r[11] else 'N/A' }}</p>
                                <p>Nearby Schools: {{ r[12] if r[12] else 'N/A' }}</p>
                            </div>
                            {% if r[6] == 'Apartment' and r[13] %}
                                <p>Floor: {{ r[13] }}</p>
                            {% elif r[6] == 'Land' and r[14] %}
                                <p>Purpose: {{ r[14] }}</p>
                            {% elif r[6] == 'Commercial Building' and r[15] %}
                                <p>Business Type: {{ r[15] }}</p>
                            {% endif %}
                            {% if session.get('role') == 'renter' %}
                                <div class="btn-group">
                                    <a href="{{ url_for('book_property', property_id=r[0]) }}" class="btn">Book</a>
                                </div>
                            {% endif %}
                        </div>
                    {% endfor %}
                </div>
                <a href="/" class="btn">Back to Home</a>
            </div>
        </body>
        </html>
    ''', results=results)

@app.route('/bookings')
def bookings():
    role = session.get('role')
    email = session.get('user')
    bookings = []
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if role == 'renter':
                cur.execute('''
                    SELECT b.Booking_ID, b.Property_ID, b.Booking_Date, b.Card_Number, p.Street, p.City, p.State, p.Zip, p.Price, p.Type, p.Description
                    FROM Booking b
                    JOIN Property p ON b.Property_ID = p.Property_ID
                    WHERE b.Renter_Email = %s
                ''', (email,))
                bookings = cur.fetchall()
            elif role == 'agent':
                cur.execute('''
                    SELECT b.Booking_ID, b.Property_ID, b.Booking_Date, b.Card_Number, b.Renter_Email, p.Street, p.City, p.State, p.Zip, p.Price, p.Type, p.Description
                    FROM Booking b
                    JOIN Property p ON b.Property_ID = p.Property_ID
                    WHERE p.agent_email = %s
                ''', (email,))
                bookings = cur.fetchall()
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bookings - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Bookings</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <div class="property-details">
                    {% for b in bookings %}
                        <div class="property-card">
                            <h3>Booking ID: {{ b[0] }}</h3>
                            <p>Property ID: {{ b[1] }}</p>
                            <p>Booking Date: {{ b[2] }}</p>
                            <p>Card: {{ b[3] }}</p>
                            {% if session.get('role') == 'agent' %}
                                <p>Renter: {{ b[4] }}</p>
                            {% endif %}
                            <p>Address: {{ b[4 if session.get('role') == 'renter' else 5] }}, {{ b[5 if session.get('role') == 'renter' else 6] }}, {{ b[6 if session.get('role') == 'renter' else 7] }} {{ b[7 if session.get('role') == 'renter' else 8] }}</p>
                            <p class="price">Price: {{ b[8 if session.get('role') == 'renter' else 9] }}</p>
                            <p>Type: {{ b[9 if session.get('role') == 'renter' else 10] }}</p>
                            <p>Description: {{ b[10 if session.get('role') == 'renter' else 11] }}</p>
                            <div class="btn-group">
                                <a href="{{ url_for('cancel_booking', booking_id=b[0]) }}" class="btn btn-danger">Cancel</a>
                            </div>
                        </div>
                    {% endfor %}
                </div>
                <a href="/" class="btn">Back to Home</a>
            </div>
        </body>
        </html>
    ''', bookings=bookings)

@app.route('/bookings/cancel/<int:booking_id>')
def cancel_booking(booking_id):
    role = session.get('role')
    email = session.get('user')
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if role == 'renter':
                cur.execute('DELETE FROM Booking WHERE Booking_ID = %s AND Renter_Email = %s', (booking_id, email))
            elif role == 'agent':
                cur.execute('''
                    DELETE FROM Booking
                    WHERE Booking_ID = %s AND EXISTS (
                        SELECT 1 FROM Property p
                        WHERE p.Property_ID = Booking.Property_ID AND p.agent_email = %s
                    )
                ''', (booking_id, email))
            conn.commit()
    flash('Booking canceled!')
    return redirect(url_for('bookings'))

@app.route('/neighborhoods')
def neighborhoods():
    if session.get('role') != 'agent':
        abort(403)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT Name, Crime_Rate, Nearby_Schools FROM Neighborhood')
            neighborhoods = cur.fetchall()
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Neighborhoods - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Neighborhoods</h2>
                <a href="{{ url_for('add_neighborhood') }}" class="btn">Add Neighborhood</a>
                <div class="property-details">
                    {% for n in neighborhoods %}
                        <div class="property-card">
                            <h3>{{ n[0] }}</h3>
                            <div class="neighborhood-info">
                                <p>Crime Rate: {{ n[1] }}</p>
                                <p>Nearby Schools: {{ n[2] }}</p>
                            </div>
                            <a href="{{ url_for('edit_neighborhood', name=n[0]) }}" class="btn">Edit</a>
                        </div>
                    {% endfor %}
                </div>
                <a href="/" class="btn">Back to Home</a>
            </div>
        </body>
        </html>
    ''', neighborhoods=neighborhoods)

@app.route('/neighborhoods/add', methods=['GET', 'POST'])
def add_neighborhood():
    if session.get('role') != 'agent':
        abort(403)
    if request.method == 'POST':
        name = request.form['name']
        crime = request.form['crime']
        schools = request.form['schools']
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check if neighborhood already exists
                cur.execute('SELECT 1 FROM Neighborhood WHERE Name = %s', (name,))
                if cur.fetchone():
                    flash('Neighborhood already exists.')
                    return redirect(url_for('neighborhoods'))
                cur.execute('INSERT INTO Neighborhood (Name, Crime_Rate, Nearby_Schools) VALUES (%s, %s, %s)', 
                          (name, crime, schools))
                conn.commit()
        flash('Neighborhood added!')
        return redirect(url_for('neighborhoods'))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Add Neighborhood - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Add Neighborhood</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <form method="post">
                    <div>
                        <label for="name">Name:</label>
                        <input type="text" id="name" name="name" required>
                    </div>
                    <div>
                        <label for="crime">Crime Rate (0-100):</label>
                        <input type="number" id="crime" name="crime" min="0" max="100" required>
                    </div>
                    <div>
                        <label for="schools">Nearby Schools:</label>
                        <input type="number" id="schools" name="schools" min="0" required>
                    </div>
                    <input type="submit" value="Add" class="btn">
                </form>
                <a href="{{ url_for('neighborhoods') }}" class="btn">Back</a>
            </div>
        </body>
        </html>
    ''')

@app.route('/neighborhoods/edit/<name>', methods=['GET', 'POST'])
def edit_neighborhood(name):
    if session.get('role') != 'agent':
        abort(403)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT Name, Crime_Rate, Nearby_Schools FROM Neighborhood WHERE Name = %s', (name,))
            n = cur.fetchone()
    if not n:
        abort(404)
    if request.method == 'POST':
        crime = request.form['crime']
        schools = request.form['schools']
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE Neighborhood SET Crime_Rate=%s, Nearby_Schools=%s WHERE Name=%s', (crime, schools, name))
                conn.commit()
        flash('Neighborhood updated!')
        return redirect(url_for('neighborhoods'))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Edit Neighborhood - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Edit Neighborhood</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <form method="post">
                    <div>
                        <label for="name">Name:</label>
                        <input type="text" id="name" value="{{ n[0] }}" disabled>
                    </div>
                    <div>
                        <label for="crime">Crime Rate (0-100):</label>
                        <input type="number" id="crime" name="crime" min="0" max="100" value="{{ n[1] }}" required>
                    </div>
                    <div>
                        <label for="schools">Nearby Schools:</label>
                        <input type="number" id="schools" name="schools" min="0" value="{{ n[2] }}" required>
                    </div>
                    <input type="submit" value="Update" class="btn">
                </form>
                <a href="{{ url_for('neighborhoods') }}" class="btn">Back</a>
            </div>
        </body>
        </html>
    ''', n=n)

@app.route('/rewards')
def rewards():
    if session.get('role') != 'renter':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT Points FROM RewardProgram WHERE Email = %s
            ''', (email,))
            points = cur.fetchone()
            if not points:
                flash('You are not enrolled in the reward program.')
                return redirect(url_for('home'))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reward Points - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Reward Points</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <div class="property-card">
                    <h3>Your Current Points</h3>
                    <p class="points">{{ points[0]|int }}</p>
                </div>
                <a href="{{ url_for('rewards_history') }}" class="btn">View History</a>
                <a href="/" class="btn">Back to Home</a>
            </div>
        </body>
        </html>
    ''', points=points)

@app.route('/rewards/history')
def rewards_history():
    if session.get('role') != 'renter':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check if user is enrolled in reward program
            cur.execute('SELECT 1 FROM RewardProgram WHERE Email = %s', (email,))
            if not cur.fetchone():
                flash('You are not enrolled in the reward program.')
                return redirect(url_for('home'))
            
            # Get current total points
            cur.execute('SELECT Points FROM RewardProgram WHERE Email = %s', (email,))
            total_points = cur.fetchone()[0]
            
            # Get booking history with points earned and duration
            cur.execute('''
                WITH BookingGroups AS (
                    SELECT 
                        MIN(b.Booking_ID) as Booking_ID,
                        MIN(b.Booking_Date) as Booking_Date,
                        b.Property_ID,
                        b.Renter_Email,
                        COUNT(*) as Duration
                    FROM Booking b
                    WHERE b.Renter_Email = %s
                    GROUP BY b.Property_ID, b.Renter_Email, b.Booking_Date::date
                )
                SELECT 
                    bg.Booking_ID,
                    bg.Booking_Date,
                    p.Property_ID,
                    p.Street,
                    p.City,
                    p.State,
                    p.Zip,
                    p.Price,
                    (bg.Duration * p.Price) as Points_Earned,
                    bg.Duration
                FROM BookingGroups bg
                JOIN Property p ON bg.Property_ID = p.Property_ID
                ORDER BY bg.Booking_Date DESC
            ''', (email,))
            bookings = cur.fetchall()
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reward Points History - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Reward Points History</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <div class="property-card">
                    <h3>Current Total Points</h3>
                    <p class="points">{{ total_points|int }}</p>
                </div>
                <h3>Booking History</h3>
                <div class="property-details">
                    {% for b in bookings %}
                        <div class="property-card">
                            <h3>Booking ID: {{ b[0] }}</h3>
                            <p>Date: {{ b[1] }}</p>
                            <p>Property ID: {{ b[2] }}</p>
                            <p>Address: {{ b[3] }}, {{ b[4] }}, {{ b[5] }} {{ b[6] }}</p>
                            <p>Price per day: ${{ b[7] }}</p>
                            <p>Duration: {{ b[9] }} days</p>
                            <p class="points">Points Earned: {{ b[8]|int }}</p>
                        </div>
                    {% endfor %}
                </div>
                <a href="{{ url_for('rewards') }}" class="btn">Back to Rewards</a>
                <a href="/" class="btn">Back to Home</a>
            </div>
        </body>
        </html>
    ''', bookings=bookings, total_points=total_points)

@app.route('/book/<int:property_id>', methods=['GET', 'POST'])
def book_property(property_id):
    if session.get('role') != 'renter':
        abort(403)
    email = session['user']
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT Card_Number FROM CreditCard WHERE Renter_Email = %s', (email,))
            cards = [c[0] for c in cur.fetchall()]
            cur.execute('''
                SELECT p.Street, p.City, p.State, p.Zip, p.Price, p.Type, p.Description,
                       n.Crime_Rate, n.Nearby_Schools
                FROM Property p
                LEFT JOIN Neighborhood n ON p.Neighborhood = n.Name
                WHERE p.Property_ID = %s
            ''', (property_id,))
            prop = cur.fetchall()
    if request.method == 'POST':
        card = request.form['card']
        start_date = request.form['start_date']
        duration = int(request.form['duration'])
        
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            if duration < 1:
                flash('Duration must be at least 1 day.')
                return redirect(url_for('book_property', property_id=property_id))
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.')
            return redirect(url_for('book_property', property_id=property_id))
            
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check for overlapping bookings
                for i in range(duration):
                    check_date = start + timedelta(days=i)
                    cur.execute('''
                        SELECT 1 FROM Booking 
                        WHERE Property_ID = %s 
                        AND Booking_Date = %s
                    ''', (property_id, check_date))
                    if cur.fetchone():
                        flash('Property is not available for the selected dates.')
                        return redirect(url_for('book_property', property_id=property_id))
                
                # Calculate rental cost
                price = float(prop[0][4])  # prop[0][4] is the price
                total_cost = price * duration
                
                # Create bookings for each day
                for i in range(duration):
                    booking_date = start + timedelta(days=i)
                    cur.execute('''
                        INSERT INTO Booking (Property_ID, Renter_Email, Booking_Date, Card_Number)
                        VALUES (%s, %s, %s, %s)
                    ''', (property_id, email, booking_date, card))
                
                # Update reward points only if user is enrolled
                cur.execute('SELECT 1 FROM RewardProgram WHERE Email = %s', (email,))
                if cur.fetchone():
                    cur.execute('''
                        UPDATE RewardProgram 
                        SET Points = Points + %s 
                        WHERE Email = %s
                    ''', (int(total_cost), email))
                    flash(f'Booking successful! You earned {int(total_cost)} reward points.')
                else:
                    flash('Booking successful!')
                
                conn.commit()
        return redirect(url_for('bookings'))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Book Property - Real Estate Management</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <div class="container">
                <h2>Book Property</h2>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash-messages">
                        {% for msg in messages %}
                            <div class="flash-message">{{ msg }}</div>
                        {% endfor %}
                    </div>
                  {% endif %}
                {% endwith %}
                <div class="property-card">
                    <h3>Property Details</h3>
                    <p>Address: {{ prop[0][0] }}, {{ prop[0][1] }}, {{ prop[0][2] }} {{ prop[0][3] }}</p>
                    <p class="price">Price: ${{ prop[0][4] }}/day</p>
                    <p>Type: {{ prop[0][5] }}</p>
                    <p>Description: {{ prop[0][6] }}</p>
                    <div class="neighborhood-info">
                        <p>Crime Rate: {{ prop[0][7] if prop[0][7] else 'N/A' }}</p>
                        <p>Nearby Schools: {{ prop[0][8] if prop[0][8] else 'N/A' }}</p>
                    </div>
                </div>
                <form method="post" class="booking-form">
                    <div>
                        <label for="card">Select Card:</label>
                        <select name="card" id="card" required>
                            {% for c in cards %}
                                <option value="{{ c }}">{{ c }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div>
                        <label for="start_date">Start Date:</label>
                        <input type="date" name="start_date" id="start_date" required>
                    </div>
                    <div>
                        <label for="duration">Duration (days):</label>
                        <input type="number" name="duration" id="duration" min="1" required>
                    </div>
                    <input type="submit" value="Book Property" class="btn">
                </form>
                <a href="{{ url_for('search') }}" class="btn">Back to Search</a>
            </div>
        </body>
        </html>
    ''', cards=cards, prop=prop)

if __name__ == '__main__':
    app.run(debug=True)