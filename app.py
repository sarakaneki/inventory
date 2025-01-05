from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate 
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stocks.db' # https://flask-sqlalchemy.palletsprojects.com/en/2.x/config/
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#https://docs.sqlalchemy.org/en/20/orm/quickstart.html#orm-quickstart　https://www.youtube.com/watch?v=AKQ3XEDI9Mw
class Stock(db.Model): #　https://github.com/shraite7/flask-inventory-app/tree/main,  https://devlog.mescius.jp/python-flask-web-api/, https://www.youtube.com/watch?v=ZDa-Z5JzLYM を参考
    id = db.Column(db.Integer, primary_key=True) 
    name = db.Column(db.String(24), unique=True, nullable=False) 
    amount = db.Column(db.Integer, nullable=False, server_default='0') # amount. integer. default 0　https://stackoverflow.com/questions/26185687/you-are-trying-to-add-a-non-nullable-field-new-field-to-userprofile-without-a）
    price = db.Column(db.Float, nullable=False, server_default='0.0') # price. float. 

    def __repr__(self): # create object https://stackoverflow.com/questions/1984162/purpose-of-repr-method
        return {"name": self.name, "amount": self.amount}

class Sale(db.Model): #sales
    id = db.Column(db.Integer, primary_key=True) # id
    item_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    amount_sold = db.Column(db.Integer, nullable=False, server_default='0') 
    total_price = db.Column(db.Float, nullable=False, server_default='0.0') 

    def __repr__(self): # create object https://stackoverflow.com/questions/1984162/purpose-of-repr-method
        return {"sales": self.total_price} #return price 

# instead of before first request
# https://stackoverflow.com/questions/73570041/flask-deprecated-before-first-request-how-to-update
with app.app_context():
    db.create_all()

#/v1/stocks. strict_slashes  /v1/stocks/ and /v1/stocks. https://stackoverflow.com/questions/33241050/trailing-slash-triggers-404-in-flask-path-rule
# https://qiita.com/tokotoko33ok/items/4184c5e713742d88ad8a　や　https://qiita.com/Yu_unI1/items/316e03d94f276695ff13　を参考に　
@app.route('/stocks', strict_slashes=False, methods=['GET', 'POST', 'DELETE'])
def manage_stocks():
    if request.method == 'GET':
        stocks = Stock.query.filter(Stock.amount > 0).order_by(Stock.name).all() #filter by name: https://zenn.dev/youichiro/articles/68650c203f7c15 参照
        stock_dict = {stock.name: stock.amount for stock in stocks} #object → dictionary
        # nameofdictionary = {key: value for ITEMS in YOURLIST}
        return jsonify(stock_dict), 200
    
# use dictionary because you can't pass objects directly to convert with jsonify. if they're not serialized. so use dictionaries, lists or Marshmallow
# https://stackoverflow.com/questions/5022066/how-to-serialize-sqlalchemy-result-to-json

    if request.method == 'POST':
        data = request.get_json() 
        if 'name' in data and 'amount' in data: # 
            if len(data['name']) <= 8 and isinstance(data['amount'], int) and data['amount'] > 0: #data validation. https://www.w3schools.com/python/ref_func_isinstance.asp
                existing_stock = Stock.query.filter_by(name=data['name']).first() #see if it already exists. if name=inputted data name, and the first entry. first() returns None or the data. So None will make it go to the next else.
                if existing_stock:
                # update
                    existing_stock.amount += data['amount'] # the amount of the variable existing_stock 
                    db.session.commit()
                    # https://stackoverflow.com/questions/10844064/items-in-json-object-are-out-of-order-using-json-dumps
                    # not using json dumps oddly makes the json pair out of order. maybe because of flask internal ordering?
                    # python 3.7 and up is supposed to keep the order of dictionaries but i don't know why it isn't and why json.dumps is working
                    response = json.dumps({"name": existing_stock.name,"amount": existing_stock.amount})
                    return response, 201 

                else: # no stock
                    new_stock = Stock(name=data['name'], amount=data['amount'])
                    db.session.add(new_stock)
                    db.session.commit()
                    response = json.dumps({"name": new_stock.name,"amount": new_stock.amount})
                    return response, 201
            else:
                return jsonify({"message": "ERROR"}), 400 # no need for response

    if request.method == 'DELETE':
        db.session.query(Stock).delete()  #delete all
        db.session.commit()
        return '', 204

@app.route('/stocks/<string:name>', methods=['GET']) # getting one entry
def stock_by_name(name):
    stock = Stock.query.filter_by(name=name).first()
    if request.method == 'GET': 
        amount = stock.amount if stock else 0 # show stock if existing, if not 0
        return jsonify({name: amount}), 200

@app.route('/sales', methods=['POST', 'GET']) # sales
def manage_sales():
    if request.method == 'POST': 
        data = request.get_json() 

        
        stock = Stock.query.filter_by(name=data['name']).first() #check if name exists
        if stock is None: 
            stock = Stock(name=data['name'], amount=0) 
            db.session.add(stock) 

        sold_amount = data.get('amount', 1) #１default

        if stock.amount < sold_amount: # error handling
            return jsonify({"message": "ERROR"}), 400

        stock.amount -= sold_amount 

        sale_price = data.get('price', 0) # 0 default
        total_price = round(sold_amount * sale_price, 1) 
        sale = Sale(item_id=stock.id, amount_sold=sold_amount, total_price=total_price) 
        db.session.add(sale) 

        db.session.commit() 

        response_data = {
            "name": data['name'],
        }

        # if user adds amount, show this
        if 'amount' in data:
            response_data['amount'] = sold_amount

        # if user only inputs price 
        if 'price' in data:
            response_data['price'] = sale_price

        response = json.dumps(response_data)
        return jsonify(response), 200  

    elif request.method == 'GET': 
        sales = Sale.query.all() 
        total_sales = sum(sale.total_price for sale in sales) # query over list of sales and add all total prices
        return jsonify({"sales": total_sales}), 200 

@app.route('/sales', methods=['DELETE'])
def delete_all_sales():
    # delete all sales
    Sale.query.delete()
    db.session.commit()
    return '', 204 # HTTP code no content