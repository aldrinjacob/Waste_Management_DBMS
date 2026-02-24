from flask import Flask, render_template, request, redirect, url_for, session
import pymysql

app = Flask(__name__)
app.secret_key = "secret123"

# ================= DATABASE CONNECTION =================
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="waste_user",
        password="waste123",
        database="waste_management",
        cursorclass=pymysql.cursors.DictCursor
    )

# ================= HOME =================
@app.route('/')
def root():
    if 'user' in session:
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session['role'] == 'cleaner':
            return redirect(url_for('cleaner_dashboard'))
        elif session['role'] == 'user':
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM users
            WHERE username=%s AND password=%s
        """, (username, password))
        user = cur.fetchone()
        conn.close()

        if user and user['status'] == 'approved':
            session['user'] = user['username']
            session['role'] = user['role']
            session['area_id'] = user.get('area_id')

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'cleaner':
                return redirect(url_for('cleaner_dashboard'))
            elif user['role'] == 'user':
                return redirect(url_for('dashboard'))

        return "Invalid credentials or user not approved."

    return render_template('login.html')

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ================= USER DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'user' not in session or session['role'] != 'user':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            wr.record_id,
            a.area_name AS area,
            wt.type_name AS waste_type,
            wr.quantity,
            DATE_FORMAT(wr.record_date,'%d-%m-%Y') AS date,
            wr.status,
            DATE_FORMAT(wr.cleared_date,'%d-%m-%Y') AS cleared_date
        FROM waste_records wr
        JOIN areas a ON wr.area_id = a.area_id
        JOIN waste_types wt ON wr.type_id = wt.type_id
        ORDER BY wr.record_date DESC
    """)

    wastes = cur.fetchall()
    conn.close()

    return render_template('index.html', wastes=wastes)

# ================= ADD WASTE =================
@app.route('/add', methods=['GET', 'POST'])
def add():
    if 'user' not in session or session['role'] != 'user':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        cur.execute("""
            INSERT INTO waste_records (area_id, type_id, quantity, record_date, status)
            VALUES (%s, %s, %s, %s, 'Pending')
        """, (
            request.form['area_id'],
            request.form['type_id'],
            request.form['quantity'],
            request.form['date']
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    cur.execute("SELECT * FROM areas")
    areas = cur.fetchall()
    cur.execute("SELECT * FROM waste_types")
    waste_types = cur.fetchall()
    conn.close()

    return render_template('add.html', areas=areas, waste_types=waste_types)

# ================= EDIT WASTE =================
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if 'user' not in session or session['role'] != 'user':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        cur.execute("""
            UPDATE waste_records
            SET area_id=%s, type_id=%s, quantity=%s, record_date=%s
            WHERE record_id=%s
        """, (
            request.form['area_id'],
            request.form['type_id'],
            request.form['quantity'],
            request.form['date'],
            id
        ))
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

# ================= DELETE (ADMIN ONLY) =================
@app.route('/delete/<int:id>')
def delete(id):
    if 'user' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM waste_records WHERE record_id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

# ================= CLEANER DASHBOARD =================
@app.route('/cleaner_dashboard')
def cleaner_dashboard():
    if 'user' not in session or session['role'] != 'cleaner':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            wr.record_id,
            a.area_name AS area,
            wt.type_name AS waste_type,
            wr.quantity,
            DATE_FORMAT(wr.record_date,'%d-%m-%Y') AS date,
            wr.status
        FROM waste_records wr
        JOIN areas a ON wr.area_id = a.area_id
        JOIN waste_types wt ON wr.type_id = wt.type_id
        WHERE wr.status='Pending'
        ORDER BY wr.record_date ASC
    """)

    wastes = cur.fetchall()
    conn.close()

    return render_template('cleaner_dashboard.html', wastes=wastes)

# ================= MARK AS CLEARED =================
@app.route('/mark_cleared/<int:id>')
def mark_cleared(id):
    if 'user' not in session or session['role'] != 'cleaner':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE waste_records
        SET status='Cleared',
            cleared_date=CURDATE()
        WHERE record_id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for('cleaner_dashboard'))

# ================= ADMIN DASHBOARD =================
@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users")
    users = cur.fetchall()

    cur.execute("""
        SELECT 
            wr.record_id,
            a.area_name AS area,
            wt.type_name AS waste_type,
            wr.quantity,
            DATE_FORMAT(wr.record_date,'%d-%m-%Y') AS date,
            wr.status,
            DATE_FORMAT(wr.cleared_date,'%d-%m-%Y') AS cleared_date
        FROM waste_records wr
        JOIN areas a ON wr.area_id = a.area_id
        JOIN waste_types wt ON wr.type_id = wt.type_id
        ORDER BY wr.record_date DESC
    """)

    wastes = cur.fetchall()
    conn.close()

    return render_template('admin.html', users=users, wastes=wastes)

# ================= APPROVE USER =================
@app.route('/approve/<int:user_id>')
def approve_user(user_id):
    if 'user' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved' WHERE user_id=%s", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))

# ================= ADD USER =================
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'user' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO users (username, password, role, status)
                VALUES (%s, %s, %s, 'pending')
            """, (username, password, role))
            conn.commit()
        except pymysql.err.IntegrityError:
            conn.close()
            return "Username already exists."

        conn.close()
        return redirect(url_for('admin_dashboard'))

    return render_template('add_user.html')

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True, port=5001)