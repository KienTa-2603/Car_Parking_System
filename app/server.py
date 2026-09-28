import threading
from flask import Flask, render_template_string, request, redirect, url_for
import serial
import json
import os

app = Flask(__name__)

# Serial connection placeholder – will be set by the main app
serial_conn = None

QR_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Parking Payment</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 400px; margin: 0 auto; padding: 20px; }
        .payment-box { border: 2px solid #4CAF50; border-radius: 10px; padding: 20px; text-align: center; }
        .amount { font-size: 24px; font-weight: bold; color: #4CAF50; margin: 20px 0; }
        button { background-color: #4CAF50; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        button:hover { background-color: #45a049; }
    </style>
</head>
<body>
    <div class="payment-box">
        <h2>Parking Payment</h2>
        <p>Slot: {{slot_id}}</p>
        <p class="amount">{{amount}} VND</p>
        <form method="post" action="{{url_for('confirm')}}">
            <input type="hidden" name="slot_id" value="{{slot_id}}">
            <input type="hidden" name="amount" value="{{amount}}">
            <button type="submit">Confirm Payment</button>
        </form>
    </div>
</body>
</html>
"""

@app.route('/pay/<int:slot_id>/<int:amount>')
def pay(slot_id, amount):
    return render_template_string(QR_TEMPLATE, slot_id=slot_id, amount=amount)

# Callback or function reference to notify main app upon payment
payment_callback = None

@app.route('/confirm', methods=['POST'])
def confirm():
    slot_id = request.form.get('slot_id')
    amount = request.form.get('amount')
    
    # Notify main app via callback if registered
    if payment_callback:
        payment_callback(slot_id, amount)

    # Send command to ESP32 to open barrier for this slot
    if serial_conn:
        try:
            cmd = {"action": "open_barrier", "slot_id": int(slot_id)}
            serial_conn.write((json.dumps(cmd) + "\n").encode())
        except Exception as e:
            print('Serial write error:', e)
    return redirect(url_for('paid'))

def set_payment_callback(cb):
    global payment_callback
    payment_callback = cb


@app.route('/paid')
def paid():
    return '<h3>Payment confirmed. Barrier opened.</h3>'

def run_server(port=5000):
    app.run(host='0.0.0.0', port=port, debug=False)

def start_flask_in_thread(serial_connection):
    global serial_conn
    serial_conn = serial_connection
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    return t
