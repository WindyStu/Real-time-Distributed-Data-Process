from kafka import KafkaConsumer
import json
import time
import mysql.connector
from mysql.connector import Error
from datetime import datetime

def create_connection():
    """创建MySQL连接"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root',
            database='kafka_db'
        )
        if connection.is_connected():
            print("成功连接到MySQL数据库")
            return connection
    except Error as e:
        print(f"连接数据库时出错: {e}")
        return None

def create_table(connection):
    """创建数据表"""
    try:
        cursor = connection.cursor()
        # 修改表结构，使用category作为唯一键
        create_table_query = """
        CREATE TABLE IF NOT EXISTS category_stats (
            category VARCHAR(255) NOT NULL PRIMARY KEY,
            count INT NOT NULL,
            timestamp DATETIME NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
        print("数据表已创建/确认存在")
    except Error as e:
        print(f"创建表时出错: {e}")
    finally:
        if cursor:
            cursor.close()

def upsert_data(connection, category, count, timestamp):
    """更新或插入数据到MySQL"""
    try:
        cursor = connection.cursor()
        # 使用REPLACE INTO来实现upsert操作
        upsert_query = """
        REPLACE INTO category_stats (category, count, timestamp)
        VALUES (%s, %s, %s)
        """
        cursor.execute(upsert_query, (category, count, timestamp))
        connection.commit()
    except Error as e:
        print(f"更新数据时出错: {e}")
    finally:
        if cursor:
            cursor.close()

def clear_table(connection):
    """清空表中的所有数据"""
    try:
        cursor = connection.cursor()
        cursor.execute("TRUNCATE TABLE category_stats")
        connection.commit()
        print("表已清空")
    except Error as e:
        print(f"清空表时出错: {e}")
    finally:
        if cursor:
            cursor.close()

def start_consumer():
    # 创建数据库连接
    connection = create_connection()
    if not connection:
        print("无法连接到数据库，程序退出")
        return
    
    # 创建数据表
    create_table(connection)
    
    # 配置消费者
    consumer = KafkaConsumer(
        'category_results',
        bootstrap_servers='localhost:9092',
        group_id='csv_group',
        auto_offset_reset='latest',  # 改为latest只接收最新数据
        api_version='0.8.2',
        consumer_timeout_ms=1000,
        fetch_max_wait_ms=500,
        fetch_min_bytes=1
    )

    print("开始监听category_results topic...")
    
    try:
        while True:
            try:
                message_batch = consumer.poll(timeout_ms=500)
                
                if not message_batch:
                    time.sleep(0.1)
                    continue
                    
                for tp, messages in message_batch.items():
                    for message in messages:
                        try:
                            if message.value is None:
                                continue
                                
                            data = json.loads(message.value.decode('utf-8'))
                            if isinstance(data, dict) and 'data' in data:
                                timestamp = datetime.fromtimestamp(data.get('timestamp'))
                                print("\n收到新的分类统计数据:")
                                print(f"时间戳: {timestamp}")
                                
                                # 清空表中的旧数据
                                clear_table(connection)
                                
                                # 插入新数据
                                for item in data['data']:
                                    category = item['Category']
                                    count = item['count']
                                    print(f"  分类: {category}, 数量: {count}")
                                    upsert_data(connection, category, count, timestamp)
                                    
                                print("数据库更新完成")
                            else:
                                print("收到的原始数据:", data)
                        except json.JSONDecodeError as e:
                            print(f"JSON解析错误: {e}, 原始消息: {message.value}")
                        except Exception as e:
                            print(f"处理消息时出错: {e}")
                            
            except Exception as e:
                print(f"消费者轮询出错: {e}")
                time.sleep(1)
                        
    except KeyboardInterrupt:
        print("\n正在关闭消费者...")
    finally:
        consumer.close()
        if connection:
            connection.close()
            print("数据库连接已关闭")

if __name__ == "__main__":
    while True:
        try:
            start_consumer()
        except Exception as e:
            print(f"消费者异常退出: {e}")
            print("5秒后尝试重新启动消费者...")
            time.sleep(5)

