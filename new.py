from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates
from sqlalchemy.exc import IntegrityError
import datetime
import threading

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banking.db'
db = SQLAlchemy(app)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    phones = db.Column(db.PickleType, nullable=False)
    emails = db.Column(db.PickleType, nullable=False)
    account = db.relationship('Account', backref='client', uselist=False)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    initial_balance = db.Column(db.Float, nullable=False)
    current_balance = db.Column(db.Float, nullable=False)

    def __init__(self, initial_balance):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance

@app.route('/clients', methods=['POST'])
def create_client():
    data = request.json
    try:
        client = Client(
            username=data['username'],
            password=data['password'],
            name=data['name'],
            dob=datetime.datetime.strptime(data['dob'], '%Y-%m-%d').date(),
            phones=data['phones'],
            emails=data['emails']
        )
        account = Account(initial_balance=data['initial_balance'])
        client.account = account
        db.session.add(client)
        db.session.commit()
        return jsonify({"message": "Client created"}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Username already exists"}), 400

@app.route('/clients/<int:id>', methods=['PUT'])
def update_client(id):
    data = request.json
    client = Client.query.get(id)
    if not client:
        abort(404)
    if 'phones' in data:
        client.phones = data['phones']
    if 'emails' in data:
        client.emails = data['emails']
    db.session.commit()
    return jsonify({"message": "Client updated"}), 200

@app.route('/transfer', methods=['POST'])
def transfer():
    data = request.json
    from_client = Client.query.get(data['from_client_id'])
    to_client = Client.query.get(data['to_client_id'])
    amount = data['amount']
    
    if not from_client or not to_client:
        abort(404)

    if from_client.account.current_balance < amount:
        return jsonify({"message": "Insufficient balance"}), 400
    
    try:
        from_client.account.current_balance -= amount
        to_client.account.current_balance += amount
        db.session.commit()
        return jsonify({"message": "Transfer successful"}), 200
    except:
        db.session.rollback()
        return jsonify({"message": "Transfer failed"}), 500

def calculate_interest():
    while True:
        with app.app_context():
            accounts = Account.query.all()
            for account in accounts:
                interest = account.current_balance * 0.05
                max_balance = account.initial_balance * 2.07
                new_balance = min(account.current_balance + interest, max_balance)
                account.current_balance = new_balance
            db.session.commit()
        time.sleep(60)

if __name__ == '__main__':
    db.create_all()
    interest_thread = threading.Thread(target=calculate_interest)
    interest_thread.start()
    app.run(debug=True)
