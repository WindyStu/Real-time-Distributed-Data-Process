from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, expr, struct, to_json
from kafka import KafkaProducer
import json
import os
import tempfile

def send_to_kafka(df, epoch_id):
    """发送数据到Kafka的函数"""
    # 收集当前批次的数据
    rows = df.collect()
    
    if not rows:  # 如果没有数据，直接返回
        print("没有数据需要发送")
        return
    
    # 创建Kafka生产者
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda x: json.dumps(x).encode('utf-8')  # 只使用value序列化器
    )
    
    try:
        # 将数据转换为列表格式，添加数据验证
        data = []
        for row in rows:
            category = row["key"]
            count = row["value"]
            if category and count:  # 确保数据不为空
                data.append({
                    "Category": category,
                    "count": int(count)
                })
        
        if data:  # 只在有数据时发送
            # 发送到Kafka
            producer.send('category_results', value=data)
            producer.flush()
            print(f"发送数据到Kafka: {data}")
        else:
            print("没有有效数据需要发送")
            
    except Exception as e:
        print(f"发送数据时出错: {e}")
        print(f"错误的数据: {rows}")  # 打印导致错��的数据
    finally:
        producer.close()

def KafkaItemCategoryCount():
    # 创建本地checkpoint目录
    checkpoint_dir = "file:///tmp/spark_checkpoints"
    local_dir = "/tmp/spark_checkpoints"
    os.makedirs(local_dir, exist_ok=True)
    os.chmod(local_dir, 0o777)
    
    spark = SparkSession \
        .builder \
        .appName("KafkaItemCategoryCount") \
        .config("spark.sql.streaming.checkpointLocation", checkpoint_dir) \
        .config("spark.local.dir", local_dir) \
        .getOrCreate()

    # 设置日志级别
    spark.sparkContext.setLogLevel("ERROR")

    # 从Kafka读取流数据
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "category") \
        .load()

    # 解析JSON数据
    parsed_df = df.selectExpr(
        "CAST(value AS STRING) as json_str"
    ).selectExpr(
        "get_json_object(json_str, '$.item_id') as item_id",
        "get_json_object(json_str, '$.Category') as Category"
    )

    # 过滤无效数据
    cleaned_df = parsed_df.filter(
        col("Category").isNotNull() & 
        col("Category") != ""
    )

    # 按Category统计
    category_counts = cleaned_df \
        .groupBy("Category") \
        .count()

    # 准备输出数据
    output_df = category_counts \
        .selectExpr(
            "Category as key",
            "CAST(count AS STRING) as value"
        )

    # 输出到控制台
    console_query = output_df \
        .writeStream \
        .outputMode("complete") \
        .format("console") \
        .option("truncate", False) \
        .option("checkpointLocation", os.path.join(checkpoint_dir, "console")) \
        .trigger(processingTime='5 seconds') \
        .start()

    # 使用foreachBatch发送到Kafka
    kafka_query = output_df \
        .writeStream \
        .outputMode("complete") \
        .foreachBatch(send_to_kafka) \
        .option("checkpointLocation", os.path.join(checkpoint_dir, "kafka")) \
        .trigger(processingTime='5 seconds') \
        .start()

    print(f"开始处理数据流... (checkpoint目录: {checkpoint_dir})")
    
    try:
        # 等待所有查询终止
        spark.streams.awaitAnyTermination()
    except KeyboardInterrupt:
        print("\n正在优雅地关闭...")
        console_query.stop()
        kafka_query.stop()
        spark.stop()

if __name__ == '__main__':
    KafkaItemCategoryCount()
