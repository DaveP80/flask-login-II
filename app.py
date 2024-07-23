from os import walk
from flask import Flask, render_template, request, redirect, url_for, current_app, session
from flask_login import LoginManager, UserMixin, logout_user, login_required, login_user, current_user 
import sqlite3
import secrets
from flask import flash

app = Flask(__name__)
secret_key = secrets.token_hex()
app.secret_key = secret_key
login_manager = LoginManager()
login_manager.init_app(app)
app.app_context().push()

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def is_active(self):
        return True

def get_user_by_id(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = {}'.format(int(user_id)))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[2])
    else:
        return None
# Callback to reload the user object
@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():

        if request.method == 'GET':
            return render_template('register.html')

        if request.method == 'POST':

            username = request.form['username']
            password = request.form['password']

            if not username or not password:
                flash("Please enter a username and password.")
                return render_template('register.html')

            conn = sqlite3.connect('database.db')

            c = conn.cursor()

            c.execute('SELECT * FROM users WHERE username = ?', (username,))
            existing_user = c.fetchone()
            if existing_user:
                error_message = "Username already exists. Please choose a different one."
                flash(error_message)
                return render_template('register.html')

            c.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                    (username, password))
            conn.commit()
            conn.close()

            flash("Registration successful! You can now log in.")
            return render_template('register.html')
        

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'GET':
        return render_template('login.html', error=error)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Connect to the database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        # Fetch user data by username
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        if user is None:
            error = 'Invalid username or password.'
        else:
            if password == user[2]:
                error = '...'
                session_user = User(user[0], user[1], user[2])
                login_user(session_user, remember=True)

                return redirect('/dashboard')

            else:
                error = 'Invalid username or password.'

        return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():

    if 'websites' not in session:
        session['websites'] = []

    if request.method == 'GET':
        return render_template('dashboard.html', websites=[item for item in session['websites'] if item is not None])
    if request.method == 'POST':
        name = request.form['website_name']
        url = request.form['website_url']


        conn = sqlite3.connect('database.db')

        c = conn.cursor()

        try:

            c.execute('INSERT INTO websites (user_id, name, url) VALUES (?, ?, ?) returning *',
                    (current_user.id, name, url))
            new_website = c.fetchone()
            conn.commit()
            conn.close()
            session['websites'].append({ "name": name, "url": url, "id": new_website[0] })
        except:
            print("check server db")

        return render_template('dashboard.html', websites=session['websites'])

@app.route('/dashboard/<int:website_id>/delete', methods=['POST'])
@login_required
def delete(website_id):

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Validate website ownership (security measure)
    is_user_website = c.execute("""
        SELECT COUNT(*) FROM websites WHERE id = ? AND user_id = ?
    """, (website_id, current_user.id)).fetchone()[0]

    if not is_user_website:
        print('You cannot delete websites you do not own.', 'error')
        return redirect(url_for('dashboard'))

    # Delete the website
    try:
        c.execute('DELETE FROM websites WHERE id = ?', (website_id,))
        conn.commit()
        conn.close()
        i = -1
        for k,v in enumerate(session['websites']):
            if v.id == website_id:
                i = k
        if i > -1:
            session['websites'][i] = None
    except Exception as e:
        print(e.message)

    return redirect(url_for('dashboard'))

def create_tables():
    # Creates new tables in the database.db database if they do not already exist.
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    with current_app.open_resource("schema.sql") as f:
        c.executescript(f.read().decode("utf8"))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
