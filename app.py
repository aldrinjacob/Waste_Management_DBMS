from flask import Flask, render_template, request, redirect, url_for, session
import pymysql

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE CONNECTION ----------------
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="waste_user",
        password="waste123",
        database="waste_management",
        cursorclass=pymysql.cursors.DictCursor
    )

# ---------------- ROOT → ALWAYS LOGIN FIRST ----------------
@app.route('/')
def root():
    session.clear()
    return redirect(url_for('login'))

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s AND status='approved'",
            (username, password)
        )
        user = cur.fetchone()
        conn.close()

        if user:
            session['user'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            return "Access denied. Invalid credentials or user not approved."

    return render_template('login.html')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------- DASHBOARD (JOIN + SORTING) ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    sort = request.args.get('sort')

    query = """
        SELECT 
            wr.record_id,
            a.area_name AS area,
            wt.type_name AS waste_type,
            wr.quantity,
            DATE_FORMAT(wr.record_date, '%d-%m-%Y') AS date
        FROM waste_records wr
        JOIN areas a ON wr.area_id = a.area_id
        JOIN waste_types wt ON wr.type_id = wt.type_id
    """

    if sort == "date_new":
        query += " ORDER BY wr.record_date DESC"
    elif sort == "date_old":
        query += " ORDER BY wr.record_date ASC"
    elif sort == "area":
        query += " ORDER BY a.area_name ASC"
    elif sort == "waste_type":
        query += " ORDER BY wt.type_name ASC"
    elif sort == "quantity":
        query += " ORDER BY wr.quantity DESC"

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query)
    wastes = cur.fetchall()
    conn.close()

    return render_template('index.html', wastes=wastes)

# ---------------- ADD WASTE ----------------
@app.route('/add', methods=['GET', 'POST'])
def add():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        cur.execute(
            """
            INSERT INTO waste_records (area_id, type_id, quantity, record_date)
            VALUES (%s, %s, %s, %s)
            """,
            (
                request.form['area_id'],
                request.form['type_id'],
                request.form['quantity'],
                request.form['date']
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    cur.execute("SELECT * FROM areas")
    areas = cur.fetchall()
    cur.execute("SELECT * FROM waste_types")
    waste_types = cur.fetchall()
    conn.close()

    return render_template('add.html', areas=areas, waste_types=waste_types)

# ---------------- EDIT WASTE ----------------
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        cur.execute(
            """
            UPDATE waste_records
            SET area_id=%s, type_id=%s, quantity=%s, record_date=%s
            WHERE record_id=%s
            """,
            (
                request.form['area_id'],
                request.form['type_id'],
                request.form['quantity'],
                request.form['date'],
                id
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    cur.execute("SELECT * FROM waste_records WHERE record_id=%s", (id,))
    waste = cur.fetchone()
    cur.execute("SELECT * FROM areas")
    areas = cur.fetchall()
    cur.execute("SELECT * FROM waste_types")
    waste_types = cur.fetchall()
    conn.close()

    return render_template('edit.html', waste=waste, areas=areas, waste_types=waste_types)

# ---------------- DELETE WASTE ----------------
@app.route('/delete/<int:id>')
def delete(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM waste_records WHERE record_id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or session.get('role') != 'admin':
        return "Access denied. Admins only."

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    conn.close()

    return render_template('admin.html', users=users)

# ---------------- APPROVE USER ----------------
@app.route('/approve/<int:user_id>')
def approve_user(user_id):
    if 'user' not in session or session.get('role') != 'admin':
        return "Access denied. Admins only."

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET status='approved' WHERE user_id=%s",
        (user_id,)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))

# ---------------- ADD USER (ADMIN ONLY) ----------------
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'user' not in session or session.get('role') != 'admin':
        return "Access denied. Admins only."

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO users (username, password, role, status)
                VALUES (%s, %s, 'user', 'pending')
                """,
                (username, password)
            )
            conn.commit()
        except:
            conn.close()
            return "Username already exists"
        conn.close()

        return redirect(url_for('admin_dashboard'))

    return render_template('add_user.html')

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True, port=5001)