from kafka import KafkaConsumer

consumer = KafkaConsumer('res::wq'
                         ':wq:wqult')
for msg in consumer:
    print((msg.value).decode('utf8'))