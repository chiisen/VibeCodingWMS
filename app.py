from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# 資料儲存路徑
DATA_DIR = 'data'
PRODUCTS_FILE = os.path.join(DATA_DIR, 'products.json')
LOCATIONS_FILE = os.path.join(DATA_DIR, 'locations.json')
STOCKS_FILE = os.path.join(DATA_DIR, 'stocks.json')
TRANSACTIONS_FILE = os.path.join(DATA_DIR, 'transactions.json')

# 記憶體資料結構
products = {}  # {"P001": {"name": "商品A", "barcode": "1234567890", "unit": "箱", "category": "食品"}}
locations = {}  # {"L001": {"desc": "一樓A區"}}
stocks = {}  # {("P001", "L001"): 50} 商品 P001 在儲位 L001 庫存 50
transactions = []  # 交易歷史記錄

def load_data():
    """從 JSON 檔案載入資料"""
    global products, locations, stocks, transactions
    
    try:
        if os.path.exists(PRODUCTS_FILE):
            with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
                products = json.load(f)
        
        if os.path.exists(LOCATIONS_FILE):
            with open(LOCATIONS_FILE, 'r', encoding='utf-8') as f:
                locations = json.load(f)
        
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r', encoding='utf-8') as f:
                # 將字串 key 轉換回 tuple
                stocks_data = json.load(f)
                stocks = {tuple(k.split(',')): v for k, v in stocks_data.items()}
        
        if os.path.exists(TRANSACTIONS_FILE):
            with open(TRANSACTIONS_FILE, 'r', encoding='utf-8') as f:
                transactions = json.load(f)
    except Exception as e:
        print(f"載入資料時發生錯誤: {e}")
        # 如果載入失敗，使用預設資料
        init_default_data()

def save_data():
    """儲存資料到 JSON 檔案"""
    try:
        # 確保資料目錄存在
        os.makedirs(DATA_DIR, exist_ok=True)
        
        with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        with open(LOCATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(locations, f, ensure_ascii=False, indent=2)
        
        # stocks 的 key 是 tuple，需要轉換為字串
        stocks_data = {','.join(k): v for k, v in stocks.items()}
        with open(STOCKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stocks_data, f, ensure_ascii=False, indent=2)
        
        with open(TRANSACTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"儲存資料時發生錯誤: {e}")

def init_default_data():
    """初始化預設資料"""
    global products, locations, stocks
    
    # 預設商品
    products = {
        "P001": {"name": "可口可樂", "barcode": "1234567890", "unit": "箱", "category": "飲料"},
        "P002": {"name": "蘋果", "barcode": "1234567891", "unit": "公斤", "category": "水果"},
        "P003": {"name": "麵包", "barcode": "1234567892", "unit": "個", "category": "食品"}
    }
    
    # 預設儲位
    locations = {
        "L001": {"desc": "一樓A區"},
        "L002": {"desc": "一樓B區"},
        "L003": {"desc": "二樓A區"}
    }
    
    # 預設庫存
    stocks = {
        ("P001", "L001"): 100,
        ("P002", "L002"): 50,
        ("P003", "L003"): 200
    }
    
    # 預設交易記錄
    transactions = [
        {
            "id": "T001",
            "type": "入庫",
            "product_id": "P001",
            "location_id": "L001",
            "quantity": 100,
            "timestamp": "2024-01-01 10:00:00"
        }
    ]

def get_next_id(prefix, data_dict):
    """產生下一個 ID"""
    max_num = 0
    for key in data_dict.keys():
        if key.startswith(prefix):
            try:
                num = int(key[len(prefix):])
                max_num = max(max_num, num)
            except ValueError:
                continue
    return f"{prefix}{max_num + 1:03d}"

def add_transaction(trans_type, product_id, location_id, quantity):
    """新增交易記錄"""
    transaction = {
        "id": str(uuid.uuid4())[:8],
        "type": trans_type,
        "product_id": product_id,
        "location_id": location_id,
        "quantity": quantity,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    transactions.append(transaction)
    save_data()

# 路由定義
@app.route('/')
def dashboard():
    """儀表板首頁"""
    # 統計資料
    total_products = len(products)
    total_locations = len(locations)
    total_stock_quantity = sum(stocks.values())
    
    # 今日交易統計
    today = datetime.now().strftime("%Y-%m-%d")
    today_inbound = len([t for t in transactions if t['type'] == '入庫' and t['timestamp'].startswith(today)])
    today_outbound = len([t for t in transactions if t['type'] == '出庫' and t['timestamp'].startswith(today)])
    
    stats = {
        'total_products': total_products,
        'total_locations': total_locations,
        'total_stock_quantity': total_stock_quantity,
        'today_inbound': today_inbound,
        'today_outbound': today_outbound
    }
    
    return render_template('dashboard.html', stats=stats)

# 商品管理路由
@app.route('/products')
def products_list():
    """商品列表"""
    return render_template('products.html', products=products)

@app.route('/products/add', methods=['GET', 'POST'])
def products_add():
    """新增商品"""
    if request.method == 'POST':
        name = request.form['name']
        barcode = request.form['barcode']
        unit = request.form['unit']
        category = request.form['category']
        
        # 檢查條碼是否重複
        for product_id, product_data in products.items():
            if product_data['barcode'] == barcode:
                flash('條碼已存在！', 'error')
                return render_template('product_form.html', action='add')
        
        product_id = get_next_id('P', products)
        products[product_id] = {
            'name': name,
            'barcode': barcode,
            'unit': unit,
            'category': category
        }
        save_data()
        flash('商品新增成功！', 'success')
        return redirect(url_for('products_list'))
    
    return render_template('product_form.html', action='add')

@app.route('/products/edit/<product_id>', methods=['GET', 'POST'])
def products_edit(product_id):
    """編輯商品"""
    if product_id not in products:
        flash('商品不存在！', 'error')
        return redirect(url_for('products_list'))
    
    if request.method == 'POST':
        name = request.form['name']
        barcode = request.form['barcode']
        unit = request.form['unit']
        category = request.form['category']
        
        # 檢查條碼是否重複（排除自己）
        for pid, product_data in products.items():
            if pid != product_id and product_data['barcode'] == barcode:
                flash('條碼已存在！', 'error')
                return render_template('product_form.html', action='edit', product_id=product_id, product=products[product_id])
        
        products[product_id] = {
            'name': name,
            'barcode': barcode,
            'unit': unit,
            'category': category
        }
        save_data()
        flash('商品更新成功！', 'success')
        return redirect(url_for('products_list'))
    
    return render_template('product_form.html', action='edit', product_id=product_id, product=products[product_id])

@app.route('/products/delete/<product_id>')
def products_delete(product_id):
    """刪除商品"""
    if product_id not in products:
        flash('商品不存在！', 'error')
        return redirect(url_for('products_list'))
    
    # 檢查是否有庫存或交易記錄
    has_stock = any(product_id in key for key in stocks.keys())
    has_transactions = any(t['product_id'] == product_id for t in transactions)
    
    if has_stock or has_transactions:
        flash('該商品已有庫存或交易記錄，無法刪除！', 'error')
    else:
        del products[product_id]
        save_data()
        flash('商品刪除成功！', 'success')
    
    return redirect(url_for('products_list'))

# 儲位管理路由
@app.route('/locations')
def locations_list():
    """儲位列表"""
    return render_template('locations.html', locations=locations)

@app.route('/locations/add', methods=['GET', 'POST'])
def locations_add():
    """新增儲位"""
    if request.method == 'POST':
        desc = request.form['desc']
        
        location_id = get_next_id('L', locations)
        locations[location_id] = {'desc': desc}
        save_data()
        flash('儲位新增成功！', 'success')
        return redirect(url_for('locations_list'))
    
    return render_template('location_form.html', action='add')

@app.route('/locations/edit/<location_id>', methods=['GET', 'POST'])
def locations_edit(location_id):
    """編輯儲位"""
    if location_id not in locations:
        flash('儲位不存在！', 'error')
        return redirect(url_for('locations_list'))
    
    if request.method == 'POST':
        desc = request.form['desc']
        locations[location_id] = {'desc': desc}
        save_data()
        flash('儲位更新成功！', 'success')
        return redirect(url_for('locations_list'))
    
    return render_template('location_form.html', action='edit', location_id=location_id, location=locations[location_id])

@app.route('/locations/delete/<location_id>')
def locations_delete(location_id):
    """刪除儲位"""
    if location_id not in locations:
        flash('儲位不存在！', 'error')
        return redirect(url_for('locations_list'))
    
    # 檢查是否有庫存或交易記錄
    has_stock = any(location_id in key for key in stocks.keys())
    has_transactions = any(t['location_id'] == location_id for t in transactions)
    
    if has_stock or has_transactions:
        flash('該儲位已有庫存或交易記錄，無法刪除！', 'error')
    else:
        del locations[location_id]
        save_data()
        flash('儲位刪除成功！', 'success')
    
    return redirect(url_for('locations_list'))

# 入庫作業路由
@app.route('/inbound')
def inbound():
    """入庫頁面"""
    return render_template('inbound.html', products=products, locations=locations)

@app.route('/inbound/submit', methods=['POST'])
def inbound_submit():
    """提交入庫"""
    product_id = request.form['product_id']
    location_id = request.form['location_id']
    quantity = int(request.form['quantity'])
    
    if product_id not in products:
        flash('商品不存在！', 'error')
        return redirect(url_for('inbound'))
    
    if location_id not in locations:
        flash('儲位不存在！', 'error')
        return redirect(url_for('inbound'))
    
    # 更新庫存
    stock_key = (product_id, location_id)
    if stock_key in stocks:
        stocks[stock_key] += quantity
    else:
        stocks[stock_key] = quantity
    
    # 新增交易記錄
    add_transaction('入庫', product_id, location_id, quantity)
    
    flash(f'入庫成功！{products[product_id]["name"]} 在 {locations[location_id]["desc"]} 增加 {quantity} {products[product_id]["unit"]}', 'success')
    return redirect(url_for('inbound'))

# 出庫作業路由
@app.route('/outbound')
def outbound():
    """出庫頁面"""
    return render_template('outbound.html', products=products, locations=locations, stocks=stocks)

@app.route('/outbound/submit', methods=['POST'])
def outbound_submit():
    """提交出庫"""
    product_id = request.form['product_id']
    location_id = request.form['location_id']
    quantity = int(request.form['quantity'])
    
    if product_id not in products:
        flash('商品不存在！', 'error')
        return redirect(url_for('outbound'))
    
    if location_id not in locations:
        flash('儲位不存在！', 'error')
        return redirect(url_for('outbound'))
    
    # 檢查庫存是否足夠
    stock_key = (product_id, location_id)
    current_stock = stocks.get(stock_key, 0)
    
    if current_stock < quantity:
        flash(f'庫存不足！目前庫存：{current_stock} {products[product_id]["unit"]}', 'error')
        return redirect(url_for('outbound'))
    
    # 更新庫存
    stocks[stock_key] -= quantity
    
    # 新增交易記錄
    add_transaction('出庫', product_id, location_id, quantity)
    
    flash(f'出庫成功！{products[product_id]["name"]} 從 {locations[location_id]["desc"]} 減少 {quantity} {products[product_id]["unit"]}', 'success')
    return redirect(url_for('outbound'))

# 庫存查詢路由
@app.route('/inventory')
def inventory():
    """庫存查詢"""
    query = request.args.get('query', '')
    filter_type = request.args.get('filter', 'all')
    
    # 建立庫存清單
    inventory_list = []
    for (product_id, location_id), quantity in stocks.items():
        if product_id in products and location_id in locations:
            inventory_item = {
                'product_id': product_id,
                'product_name': products[product_id]['name'],
                'barcode': products[product_id]['barcode'],
                'location_id': location_id,
                'location_desc': locations[location_id]['desc'],
                'quantity': quantity,
                'unit': products[product_id]['unit'],
                'category': products[product_id]['category']
            }
            
            # 搜尋過濾
            if query:
                if (query.lower() not in inventory_item['product_name'].lower() and 
                    query.lower() not in inventory_item['barcode'] and
                    query.lower() not in inventory_item['location_desc'].lower()):
                    continue
            
            # 庫存過濾
            if filter_type == 'low_stock' and quantity > 0:
                continue
            elif filter_type == 'zero_stock' and quantity != 0:
                continue
            elif filter_type == 'has_stock' and quantity == 0:
                continue
            
            inventory_list.append(inventory_item)
    
    return render_template('inventory.html', inventory_list=inventory_list, query=query, filter_type=filter_type)

# 盤點作業路由
@app.route('/stocktaking')
def stocktaking():
    """盤點頁面"""
    return render_template('stocktaking.html', products=products, locations=locations, stocks=stocks)

@app.route('/stocktaking/submit', methods=['POST'])
def stocktaking_submit():
    """提交盤點"""
    product_id = request.form['product_id']
    location_id = request.form['location_id']
    actual_quantity = int(request.form['actual_quantity'])
    
    if product_id not in products:
        flash('商品不存在！', 'error')
        return redirect(url_for('stocktaking'))
    
    if location_id not in locations:
        flash('儲位不存在！', 'error')
        return redirect(url_for('stocktaking'))
    
    stock_key = (product_id, location_id)
    system_quantity = stocks.get(stock_key, 0)
    difference = actual_quantity - system_quantity
    
    # 更新庫存
    stocks[stock_key] = actual_quantity
    
    # 新增交易記錄
    add_transaction('盤點', product_id, location_id, difference)
    
    flash(f'盤點完成！{products[product_id]["name"]} 在 {locations[location_id]["desc"]}：系統數量 {system_quantity}，實際數量 {actual_quantity}，差異 {difference:+d}', 'success')
    return redirect(url_for('stocktaking'))

# API 路由
@app.route('/api/products')
def api_products():
    """商品 API"""
    return jsonify(products)

@app.route('/api/locations')
def api_locations():
    """儲位 API"""
    return jsonify(locations)

@app.route('/api/stock/<product_id>/<location_id>')
def api_stock(product_id, location_id):
    """庫存 API"""
    stock_key = (product_id, location_id)
    quantity = stocks.get(stock_key, 0)
    return jsonify({'quantity': quantity})

if __name__ == '__main__':
    # 載入資料
    load_data()
    
    # 如果沒有資料，初始化預設資料
    if not products:
        init_default_data()
        save_data()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
