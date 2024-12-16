# ReadMe

## 项目链接



## 项目介绍

本项目目的是实时统计网购消费信息进行秒级数据处理，前端动态可视化展示.

技术栈：`kafka`、`spark`消息队列及数据处理，获取并处理实时数据；基于`flask`框架进行前端展示；`mysql`实现重要数据持久化。具体详见`introduce.pdf`.

## 环境依赖

需要由局域网下主机或容器组成分布式集群，本项目环境由docker container搭建分布式环境：

| hostname     | ip         | role   |
| ------------ | ---------- | ------ |
| 22ee4827f146 | 172.17.0.2 | master |
| 44972a59b1a3 | 172.17.0.4 | slave1 |
| 046db9cfbbab | 172.17.0.5 | slave2 |

实际开发过程中可以通过修改hostname更直观感受每个容器的role。

## 项目结构

pythonProject
├─ data
│  ├─ output.csv
│  ├─ test.py
│  ├─ web
│  │  ├─ app.py	# 主应用程序文件，包含Flask应用的设置和路由定义
│  │  ├─ gulpfile.js
│  │  ├─ output.csv
│  │  ├─ templates	 # 存放HTML模板文件的目录
│  │  │  ├─ index.html	# 主页面模板，展示数据可视化和统计信息
│  │  │  ├─ partials
│  │  │  ├─ pages	# 存放子页面模板的目录
│  │  │  │  ├─ ui-features
│  │  │  │  ├─ tables	# 存放表格相关页面的目录
│  │  │  │  ├─ samples
│  │  │  │  └─ charts	 # 存放图表相关页面的目录
│  │  │  │     └─ datacharts.html	 # 数据可视化页面模板
│  │  │  └─ documentation
│  │  │     └─ documentation.html
│  │  └─ static	# 存放静态文件
│  │     ├─ vendors	# 存放第三方库
│  │     ├─ scss
│  │     │  ├─ mixins
│  │     │  ├─ landing-screens
│  │     │  │  └─ _auth.scss
│  │     │  └─ components
│  │     │        └─ _data-tables.scss
│  │     ├─ js
│  │     ├─ images
│  │     └─ css
│  │        └─ style.css
│  └─ scripts
│     ├─ consumer.py	//消费topic为catrgory的数据，将数据进行统计处理后发送topic为category_results
│     ├─ consumer_mysql.py	//消费topic为category_results的数据，将数据存储到本地mysql持久化存储	
│     ├─ consumer_test1.py	//测试代码
│     ├─ kafka_test1.py	//测试代码
│     ├─ producer.py	//读取数据源，本项目是从本地读取csv模拟实时数据，将数据发送到topic为category中
│     └─ producer_test1.py	//测试代码
└─ .idea
   └─ pythonProject.iml

## 命令行

根据`introduce.pdf`搭建分布式集群及启动`zookeeper`、`kafka`服务后

* 读取数据源，创建主题`category`，生产者生产消息

```bash
python producer.py
```

* 消费者消费topic为`catrgory`的数据，`spark`数据统计处理后创建topic`category_results`,生产者生产消息

```bash
python consumer.py
```

* 消费者消费topic为`category_results`的数据，将数据存储到本地`mysql`持久化存储

```bash
python consumer_mysql.py
```

* 基于`flask`框架进行大屏动态展示消费实时数据统计结果

```bash
python app.py
```

