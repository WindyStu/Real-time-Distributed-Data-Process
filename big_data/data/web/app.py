import csv
import math
import os
import threading
from urllib import request
import json

import pandas as pd
from flask_login import login_user
from io import StringIO
from flask import render_template, redirect, url_for, session, send_from_directory
from flask import Flask, request, make_response, jsonify, url_for
from flask_cors import CORS
from flask_socketio import SocketIO
# from kafka import KafkaConsumer
from  kafka import *

import sqlite3
import time
from dbutils.pooled_db import PooledDB
import pymysql  # 替换 sqlite3

app = Flask(__name__)
socketio = SocketIO(app)

# 创建MySQL数据库连接池
pool = PooledDB(
    creator=pymysql,  # 使用pymysql驱动
    maxconnections=6,  # 连接池最大连接数
    mincached=2,      # 初始化时创建的连接数
    maxcached=5,      # 连接池最大空闲连接数
    maxshared=3,      # 连接池最大共享连接数
    blocking=True,    # 连接池中如果没有可用连接后是否阻塞等待
    maxusage=None,    # 一个连接最多被重复使用的次数
    setsession=[],    # 开始会话前执行的命令列表
    ping=0,          # ping MySQL服务端确保连接的存活
    host='localhost',
    port=3306,
    user='root',
    password='123456',
    database='mysql',
    charset='utf8mb4'
)

def get_db():
    return pool.connection()

# 修改后台数据更新线程
def background_thread():
    while True:
        try:
            # 从数据库获取最新数据
            conn = get_db()
            cursor = conn.cursor()
            
            # 计算最新统计数据
            new_data = {
                'avg_order_value': get_avg_order_value(),
                'total_sales': get_total_sales(), 
                'total_orders': get_total_orders(),
                'complete_rate': get_complete_rate(),
                'daily_orders': get_daily_orders(),
                'top_categories': get_top_categories()
            }
            
            # 通过WebSocket推送更新
            socketio.emit('data_update', new_data)
            
            cursor.close()
            conn.close()
            
            time.sleep(5)
            
        except Exception as e:
            print(f"数据更新错误: {str(e)}")
            time.sleep(5)

@socketio.on('connect')
def handle_connect():
    while True:
        # 获取最新数据
        new_data = {
            'avg_order_value': get_avg_order_value(),
            'total_sales': get_total_sales(),
            'total_orders': get_total_orders(),
            'complete_rate': get_complete_rate(),
            'daily_orders': get_daily_orders(),
            'top_categories': get_top_categories()
        }
        
        # 发送更新
        socketio.emit('data_update', new_data)
        
        # 等待一定时间后再次更新
        time.sleep(2)

@app.route('/')
@app.route('/index')
def index():
    df = pd.read_csv('data.csv')
    
    # 统计数据
    total_orders = len(df)
    total_sales = df['grand_total'].sum()
    avg_order_value = total_sales / total_orders
    complete_rate = len(df[df['status']=='complete']) / total_orders * 100
    
    # 类别销售额TOP5
    top_categories = df.groupby('Category')['grand_total'].sum().sort_values(ascending=False).head(5).to_dict()
    
    # 每日订单趋势
    daily_orders = df.groupby('Working_Date').size().to_dict()
    
    return render_template('index.html',
                         total_orders=total_orders,
                         total_sales=total_sales,
                         avg_order_value=avg_order_value,
                         complete_rate=complete_rate,
                         top_categories=top_categories,
                         daily_orders=daily_orders)

@app.route('/pages/tables/dataview')
def dataview():
    # 获取当前页码和每页的数量
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get('per_page', 25))

    # 计算分页的起始位置
    start = (page - 1) * per_page

    # 从 CSV 文件中读取数据
    with open('data.csv', mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        header = next(reader)  # 读取表头
        datalist = list(reader)  # 将数据读取为列表

    # 获取总记录数
    total = len(datalist)  # 总记录数为数据列表的长度

    # 查询当前页的数据
    paginated_data = datalist[start:start + per_page]  # 根据起始位置和每页数量进行分页

    # 计算总页数
    total_pages = math.ceil(total / per_page)  # 向上取整

    # 计算显示的页码范围
    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)

    # 返回渲染模板
    return render_template('pages/tables/dataview.html', items=paginated_data, page=page, total_pages=total_pages, total=total, start_page=start_page, end_page=end_page)

@app.route('/pages/charts/datacharts')
def datacharts():
    return render_template('pages/charts/datacharts.html')

def get_avg_order_value():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT AVG(grand_total) 
        FROM category_stats
    """)
    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return float(result or 0)

def get_total_sales():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SUM(grand_total) 
        FROM category_stats
    """)
    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return float(result or 0)

def get_total_orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM category_stats
    """)
    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return int(result or 0)

def get_complete_rate():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM category_stats WHERE status='complete') * 100.0 / COUNT(*)
        FROM category_stats
    """)
    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return float(result or 0)

def get_daily_orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Working_Date, COUNT(*) 
        FROM category_stats 
        GROUP BY Working_Date 
        ORDER BY Working_Date
    """)
    result = dict(cursor.fetchall())
    cursor.close()
    conn.close()
    return result

def get_top_categories():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Category, SUM(grand_total) as total
        FROM category_stats
        GROUP BY Category
        ORDER BY total DESC
        LIMIT 5
    """)
    result = dict(cursor.fetchall())
    cursor.close()
    conn.close()
    return result

if __name__ == '__main__':
    # 启动后台更新线程
    thread = threading.Thread(target=background_thread)
    thread.daemon = True
    thread.start()
    
    # 启动Flask应用
    socketio.run(app, debug=True)