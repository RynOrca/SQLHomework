from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pymysql

app = Flask(__name__)
app.secret_key = 'sysu_netsec_2025'


DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '0d000721',
    'database': 'GameKeyHub',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_db():
    return pymysql.connect(**DB_CONFIG)


@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = 1
        session['username'] = 'RichPlayer'

    conn = get_db()
    cursor = conn.cursor()

    sql = """
          SELECT g.game_id, \
                 g.title, \
                 g.platform, \
                 g.historical_low, \
                 MIN(pk.price)    as current_price, \
                 COUNT(pk.key_id) as stock
          FROM Games g
                   LEFT JOIN Product_Keys pk ON g.game_id = pk.game_id AND pk.status = 'available'
          GROUP BY g.game_id \
          """
    cursor.execute(sql)
    games = cursor.fetchall()

    for game in games:
        curr = game['current_price']
        low = game['historical_low']

        game['tag'] = '缺货'
        game['color'] = 'secondary'

        if curr:
            curr_val = float(curr)
            low_val = float(low)

            if curr_val <= low_val * 1.05:
                game['tag'] = '史低！买爆！'
                game['color'] = 'success'
            elif curr_val <= low_val * 1.2:
                game['tag'] = '好价可入'
                game['color'] = 'primary'
            else:
                game['tag'] = '建议再等等'
                game['color'] = 'warning'

    cursor.execute("SELECT balance FROM Users WHERE user_id=%s", (session['user_id'],))
    user = cursor.fetchone()
    conn.close()

    return render_template('index.html', games=games, user=user)


@app.route('/buy', methods=['POST'])
def buy_key():
    user_id = session['user_id']
    game_id = request.form.get('game_id')

    conn = get_db()
    cursor = conn.cursor()

    try:
        conn.begin()

        cursor.execute(
            "SELECT price FROM Product_Keys WHERE game_id=%s AND status='available' ORDER BY price ASC LIMIT 1",
            (game_id,))
        item = cursor.fetchone()

        if not item:
            conn.rollback()
            return jsonify({'status': 'error', 'msg': '手慢了，已售罄！'})

        price = item['price']

        cursor.execute("SELECT balance FROM Users WHERE user_id=%s", (user_id,))
        balance = cursor.fetchone()['balance']

        if balance < price:
            conn.rollback()
            return jsonify({'status': 'error', 'msg': '余额不足'})

        sql_kill = """
                   UPDATE Product_Keys
                   SET status='sold', \
                       buyer_id=%s
                   WHERE game_id = %s \
                     AND status = 'available' \
                     AND price = %s LIMIT 1 \
                   """
        cursor.execute(sql_kill, (user_id, game_id, price))

        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({'status': 'error', 'msg': '抢购失败，请重试'})

        cursor.execute("UPDATE Users SET balance = balance - %s WHERE user_id=%s", (price, user_id))

        cursor.execute("SELECT key_id FROM Product_Keys WHERE game_id=%s AND buyer_id=%s ORDER BY key_id DESC LIMIT 1",
                       (game_id, user_id))
        sold_key_id = cursor.fetchone()['key_id']

        cursor.execute("INSERT INTO Orders (buyer_id, key_id, deal_price) VALUES (%s, %s, %s)",
                       (user_id, sold_key_id, price))

        conn.commit()
        return jsonify({'status': 'success', 'msg': '抢购成功！'})

    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'msg': str(e)})
    finally:
        conn.close()


@app.route('/my_orders')
def my_orders():
    conn = get_db()
    cursor = conn.cursor()
    sql = """
          SELECT o.deal_time, g.title, k.cdk_code, o.deal_price
          FROM Orders o
                   JOIN Product_Keys k ON o.key_id = k.key_id
                   JOIN Games g ON k.game_id = g.game_id
          WHERE o.buyer_id = %s
          ORDER BY o.deal_time DESC \
          """
    cursor.execute(sql, (session['user_id'],))
    orders = cursor.fetchall()
    conn.close()
    return render_template('my_orders.html', orders=orders)




@app.route('/sell', methods=['GET', 'POST'])
def sell_key():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        game_id = request.form.get('game_id')
        cdk_code = request.form.get('cdk_code')
        price = request.form.get('price')
        seller_id = session.get('user_id')

        try:
            sql = """
                  INSERT INTO Product_Keys (game_id, seller_id, cdk_code, price, status)
                  VALUES (%s, %s, %s, %s, 'available') \
                  """
            cursor.execute(sql, (game_id, seller_id, cdk_code, price))
            conn.commit()

            return jsonify({'status': 'success', 'msg': '上架成功！如果是史低价，首页标签会自动更新哦！'})
        except Exception as e:
            conn.rollback()
            return jsonify({'status': 'error', 'msg': str(e)})
        finally:
            conn.close()

    else:
        cursor.execute("SELECT game_id, title FROM Games")
        games = cursor.fetchall()
        conn.close()
        return render_template('sell.html', games=games)

if __name__ == '__main__':
    app.run(debug=True)