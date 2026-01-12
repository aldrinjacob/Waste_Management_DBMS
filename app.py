from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE CONNECTION ----------------
def get_db_connection():
    conn = sqlite3.connect('waste.db')
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- CREATE TABLES ----------------
with get_db_connection() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS waste (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area TEXT NOT NULL,
            waste_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            date TEXT NOT NULL
        )
    """)
    conn.commit()

with get_db_connection() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    conn.commit()

# ---------------- CREATE DEFAULT ADMIN ----------------
with get_db_connection() as conn:
    admin = conn.execute(
        "SELECT * FROM users WHERE username='admin'"
    ).fetchone()

    if not admin:
        conn.execute(
            "INSERT INTO users (username, password, role, status) VALUES (?, ?, ?, ?)",
            ('admin', 'admin123', 'admin', 'approved')
        )
        conn.commit()

# ---------------- ROOT (ALWAYS LOGIN FIRST) ----------------
@app.route('/')
def root():
    session.clear()
    return redirect(url_for('login'))

# ---------------- DASHBOARD (WASTE LIST + SORTING) ----------------
@app.route('/dashboard')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))

    sort = request.args.get('sort')
    query = "SELECT * FROM waste"

    if sort == "date_new":
        query += " ORDER BY date DESC"
    elif sort == "date_old":
        query += " ORDER BY date ASC"
    elif sort == "area":
        query += " ORDER BY area ASC"
    elif sort == "waste_type":
        query += " ORDER BY waste_type ASC"
    elif sort == "quantity":
        query += " ORDER BY quantity DESC"

    conn = get_db_connection()
    wastes = conn.execute(query).fetchall()
    conn.close()

    return render_template('index.html', wastes=wastes)

# ---------------- ADD WASTE ----------------
@app.route('/add', methods=('GET', 'POST'))
def add():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        area = request.form['area']
        waste_type = request.form['waste_type']
        quantity = request.form['quantity']
        date = request.form['date']

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO waste (area, waste_type, quantity, date) VALUES (?, ?, ?, ?)',
            (area, waste_type, quantity, date)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('add.html')

# ---------------- EDIT WASTE ----------------
@app.route('/edit/<int:id>', methods=('GET', 'POST'))
def edit(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    waste = conn.execute('SELECT * FROM waste WHERE id=?', (id,)).fetchone()

    if request.method == 'POST':
        area = request.form['area']
        waste_type = request.form['waste_type']
        quantity = request.form['quantity']
        date = request.form['date']

        conn.execute(
            'UPDATE waste SET area=?, waste_type=?, quantity=?, date=? WHERE id=?',
            (area, waste_type, quantity, date, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    conn.close()
    return render_template('edit.html', waste=waste)

# ---------------- DELETE WASTE ----------------
@app.route('/delete/<int:id>')
def delete(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM waste WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# ---------------- LOGIN ----------------
@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=? AND status='approved'",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session['user'] = username
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            return "Access denied. Invalid credentials or not approved."

    return render_template('login.html')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or session.get('role') != 'admin':
        return "Access denied. Admins only."

    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()

    return render_template('admin.html', users=users)

# ---------------- APPROVE USER ----------------
@app.route('/approve/<int:user_id>')
def approve_user(user_id):
    if 'user' not in session or session.get('role') != 'admin':
        return "Access denied. Admins only."

    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET status='approved' WHERE id=?",
        (user_id,)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))

# ---------------- ADD USER (ADMIN) ----------------
@app.route('/add_user', methods=('GET', 'POST'))
def add_user():
    if 'user' not in session or session.get('role') != 'admin':
        return "Access denied. Admins only."

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, password, role, status) VALUES (?, ?, ?, ?)",
                (username, password, 'user', 'pending')
            )
            conn.commit()
        except:
            conn.close()
            return "Username already exists"
        conn.close()

        return redirect(url_for('admin_dashboard'))

    return render_template('add_user.html')

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True, port=5001)