cloud_v2包包含了云端服务程序和本地运行程序

云端服务程序cloud_server.py基于python的flask框架编写，向外开启了rest api接口

服务以节点集的形式存放在云端，现有服务包括处理双目的stereo_proc以及加法实验的addition

本地主要运行两个程序：brideg.py和client.py．两者都以节点形式运行．bridge.py是通信节点，利用requests向云端发送请求

桥梁通信节点和客户端节点之间以ros service形式通信，客户端节点申请服务时需要发送两个字符串，一个代表云服务名称，一个代表

云服务请求动作．以下是服务的对应关系：

services : list startall stopall

service(stereo_proc addition ...)：start stop

更新在2018-4-23:
1 cloudserver.py中增加了验证,服务查询等功能,并且实现的是在docker容器启动服务节点.整个程序包装成了一个类
2 clientclib.py程序,更改了QoS部分,包括权重计算算法,因子检测程序<包括rtt,rdst,netspeed>.

之前的程序标记为xx_bf.py

2018-5-24：更改存储服务的URI形式
@app.route('/cloud_service/(service)/(action)',methods=['POST'])
改为：
@app.route('/compute/(service)/(action)',methods=['POST'])
