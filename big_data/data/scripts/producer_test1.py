# coding: utf-8
import csv
from datetime import datetime
import json
from kafka import KafkaProducer
import time
# 实例化 KafkaProducer
producer = KafkaProducer(bootstrap_servers='localhost:9092',
                         value_serializer=lambda v: json.dumps(v).encode('utf-8'))

# 读取 CSV 文件并发送数据
with open('/tmp_data/data/output.csv', mode='r', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)  # 使用字典读取器
    for row in reader:
        time.sleep(0.1)  # 每隔0.1秒发送一行数据
        # 发送每行数据到 Kafka 主题 'category'
        producer.send('category', {
            'item_id': int(row['item_id']),
            'Category': str(row['Category']).strip()  # 确保Category不为空且已去除空白
        })

# 关闭生产者
producer.close()

