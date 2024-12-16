import json
from kafka import KafkaConsumer
import pymysql
import pandas as pd

# 连接 Kafka
consumer = KafkaConsumer(
    'category_results',
    bootstrap_servers='localhost:9092',
    group_id='csv_group',
    auto_offset_reset='earliest',
)

# 连接 MySQL 数据库
connect = pymysql.connect(
    host='localhost',
    port=3306,
    user='root',
    passwd='tengyue',
    db='big_data',
    charset='utf8'
)

# 获取游标
cursor = connect.cursor()

# 处理消费的数据
try:
    for msg in consumer:
        msg_value = msg.value.decode('utf-8')
        data = json.loads(msg_value)

        # 打印接收到的数据
        print(f"Received data: {data}")

        # 构建插入数据的 SQL 语句
        sql = """INSERT INTO category (Category,count)VALUES (%s, %s)"""

        # 插入数据
        try:
            cursor.execute(sql, (data['Category'], data['count']))
            connect.commit()  # 提交数据
        except Exception as e:
            print(f"Error inserting data: {e}")
            print(f"Data: {data}")
finally:
    cursor.close()
    connect.close()
    consumer.close()
