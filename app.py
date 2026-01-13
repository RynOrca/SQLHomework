from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'sysu_netsec_2025_final'

# === 数据库配置 ===
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '0d000721',  # <--- 请修改为你的真实密码
    'database': 'GameKeyHub',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_db():
    return pymysql.connect(**DB_CONFIG)


# === 1. 认证模块 ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    data = request.json
    username = data.get('username')
    password = data.get('password')
    action = data.get('action')

    conn = get_db()
    cursor = conn.cursor()
    try:
        if action == 'register':
            # 注册初始余额为 0
            hashed_pw = generate_password_hash(password)
            try:
                cursor.execute(
                    "INSERT INTO Users (username, password_hash, role, balance) VALUES (%s, %s, 'user', 0.00)",
                    (username, hashed_pw))
                conn.commit()
                return jsonify({'status': 'success', 'msg': '注册成功！请登录后充值'})
            except pymysql.err.IntegrityError:
                return jsonify({'status': 'error', 'msg': '用户名已存在'})

        elif action == 'login':
            cursor.execute("SELECT * FROM Users WHERE username=%s", (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                session['role'] = user['role']
                return jsonify({'status': 'success', 'msg': '登录成功', 'role': user['role']})
            else:
                return jsonify({'status': 'error', 'msg': '用户名或密码错误'})
    finally:
        conn.close()


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# === 2. 商城主页 ===
@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    # 只显示未下架的游戏
    sql = """
          SELECT g.game_id, \
                 g.title, \
                 g.platform, \
                 g.historical_low,
                 MIN(pk.price)    as current_price, \
                 COUNT(pk.key_id) as stock
          FROM Games g
                   LEFT JOIN Product_Keys pk ON g.game_id = pk.game_id AND pk.status = 'available'
          WHERE g.is_active = 1
          GROUP BY g.game_id \
          """
    cursor.execute(sql)
    games = cursor.fetchall()

    # 价格建议算法
    for game in games:
        curr = game['current_price']
        low = game['historical_low']
        game['tag'] = '缺货'
        game['color'] = 'secondary'
        if curr:
            curr_val = float(curr)
            low_val = float(low)
            if curr_val <= low_val * 1.05:
                game['tag'] = '史低！买爆！';
                game['color'] = 'success'
            elif curr_val <= low_val * 1.2:
                game['tag'] = '好价可入';
                game['color'] = 'primary'
            else:
                game['tag'] = '建议再等等';
                game['color'] = 'warning'

    cursor.execute("SELECT balance, role FROM Users WHERE user_id=%s", (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    return render_template('index.html', games=games, user=user)


# === 3. 充值接口 ===
@app.route('/recharge', methods=['POST'])
def recharge():
    if 'user_id' not in session: return jsonify({'status': 'error', 'msg': '请先登录'})
    amount = request.form.get('amount')
    if not amount or float(amount) <= 0:
        return jsonify({'status': 'error', 'msg': '金额无效'})

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Users SET balance = balance + %s WHERE user_id = %s", (amount, session['user_id']))
        conn.commit()
        return jsonify({'status': 'success', 'msg': f'成功充值 ¥{amount}'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'msg': str(e)})
    finally:
        conn.close()


# === 4. 购买接口 (核心事务：买家扣款+卖家入账) ===
@app.route('/buy', methods=['POST'])
def buy_key():
    if 'user_id' not in session: return jsonify({'status': 'error', 'msg': '请先登录'})
    buyer_id = session['user_id']
    game_id = request.form.get('game_id')

    conn = get_db()
    cursor = conn.cursor()
    try:
        conn.begin()
        # A. 锁定库存行，获取卖家ID
        sql_find = "SELECT key_id, price, seller_id FROM Product_Keys WHERE game_id=%s AND status='available' LIMIT 1 FOR UPDATE"
        cursor.execute(sql_find, (game_id,))
        item = cursor.fetchone()

        if not item:
            conn.rollback();
            return jsonify({'status': 'error', 'msg': '手慢了，已售罄！'})

        price = item['price']
        seller_id = item['seller_id']
        key_id = item['key_id']

        if seller_id == buyer_id:
            conn.rollback();
            return jsonify({'status': 'error', 'msg': '不能购买自己的商品'})

        # B. 检查买家余额
        cursor.execute("SELECT balance FROM Users WHERE user_id=%s", (buyer_id,))
        if cursor.fetchone()['balance'] < price:
            conn.rollback();
            return jsonify({'status': 'error', 'msg': '余额不足，请充值'})

        # C. 执行转账 (原子性)
        cursor.execute("UPDATE Users SET balance = balance - %s WHERE user_id=%s", (price, buyer_id))  # 扣买家
        cursor.execute("UPDATE Users SET balance = balance + %s WHERE user_id=%s", (price, seller_id))  # 加卖家

        # D. 移交商品
        cursor.execute("UPDATE Product_Keys SET status='sold', buyer_id=%s WHERE key_id=%s", (buyer_id, key_id))

        # E. 记录订单
        cursor.execute("INSERT INTO Orders (buyer_id, key_id, deal_price) VALUES (%s, %s, %s)",
                       (buyer_id, key_id, price))

        conn.commit()
        return jsonify({'status': 'success', 'msg': '交易成功！资金已到账卖家'})
    except Exception as e:
        conn.rollback();
        return jsonify({'status': 'error', 'msg': str(e)})
    finally:
        conn.close()


# === 5. 上架接口 ===
@app.route('/sell', methods=['GET', 'POST'])
def sell_key():
    if 'user_id' not in session: return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        game_id = request.form.get('game_id')
        # 检查游戏是否允许上架
        cursor.execute("SELECT is_active FROM Games WHERE game_id=%s", (game_id,))
        game = cursor.fetchone()
        if not game or game['is_active'] == 0:
            conn.close();
            return jsonify({'status': 'error', 'msg': '该游戏已被禁止上架'})

        try:
            sql = "INSERT INTO Product_Keys (game_id, seller_id, cdk_code, price) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (game_id, session['user_id'], request.form.get('cdk_code'), request.form.get('price')))
            conn.commit()
            return jsonify({'status': 'success', 'msg': '上架成功'})
        except Exception as e:
            conn.rollback();
            return jsonify({'status': 'error', 'msg': str(e)})
        finally:
            conn.close()
    else:
        cursor.execute("SELECT game_id, title FROM Games WHERE is_active=1")
        games = cursor.fetchall()
        conn.close()
        return render_template('sell.html', games=games)


# === 6. 订单查询 ===
@app.route('/my_orders')
def my_orders():
    if 'user_id' not in session: return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    sql = """
          SELECT o.deal_time, g.title, k.cdk_code, o.deal_price
          FROM Orders o \
                   JOIN Product_Keys k ON o.key_id = k.key_id \
                   JOIN Games g ON k.game_id = g.game_id
          WHERE o.buyer_id = %s \
          ORDER BY o.deal_time DESC \
          """
    cursor.execute(sql, (session['user_id'],))
    orders = cursor.fetchall()
    conn.close()
    return render_template('my_orders.html', orders=orders)


# === 7. 管理员后台 ===
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin': return "Access Denied", 403
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Games")
    games = cursor.fetchall()
    cursor.execute("SELECT * FROM Users")
    users = cursor.fetchall()

    sql_orders = """
                 SELECT o.deal_time, g.title, ub.username as buyer, us.username as seller, o.deal_price
                 FROM Orders o
                          JOIN Users ub ON o.buyer_id = ub.user_id
                          JOIN Product_Keys k ON o.key_id = k.key_id
                          JOIN Users us ON k.seller_id = us.user_id
                          JOIN Games g ON k.game_id = g.game_id
                 ORDER BY o.deal_time DESC \
                 """
    cursor.execute(sql_orders)
    orders = cursor.fetchall()
    conn.close()
    return render_template('admin.html', games=games, users=users, orders=orders)


@app.route('/admin/add_game', methods=['POST'])
def add_game():
    if session.get('role') != 'admin': return jsonify({'status': 'error'})
    conn = get_db();
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Games (title, platform) VALUES (%s, %s)",
                   (request.form.get('title'), request.form.get('platform')))
    conn.commit();
    conn.close()
    return jsonify({'status': 'success'})


@app.route('/admin/toggle_game', methods=['POST'])
def toggle_game():
    if session.get('role') != 'admin': return jsonify({'status': 'error'})
    conn = get_db();
    cursor = conn.cursor()
    cursor.execute("UPDATE Games SET is_active = NOT is_active WHERE game_id=%s", (request.form.get('game_id'),))
    conn.commit();
    conn.close()
    return jsonify({'status': 'success'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)