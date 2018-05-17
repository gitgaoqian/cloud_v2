# -*- coding: utf-8 -*-
"""
updated on Wed Apr 12 08:52:21 2018

@author: ros
"""
import requests
import os
import time
import math
import re
import rospy
from threading import Thread

startaction=['start','startall']
stopaction=['stop','stopall','list']

#-----------------云端节点的注册-----------------#
def cloud_param_set(url,master_uri):
    value={'ros_master_uri':master_uri}
    r = requests.post( url, data=value)
    return r.text
#-------------根据不同表示服务的ｕrl实现不同云端服务的请求------#
def cloud_service_request(url):
    r = requests.post( url)
    url_split = url.split('/')
    if url_split[5] in startaction:
        print r.text
    elif url_split[5] in stopaction:
        print r.text
    return r.text
                                    #--------------QOS Fuction---------------------#

#------------------------------QOS---------------------------------------------
#5-14:QoS程序分为两部分:1 因素的检测 2 qos的计算
#
def get_total_tx_bytes(interface):
    r = os.popen('ifconfig ' + interface + ' | grep "TX bytes"').read()
    total_bytes = re.sub('(.+:)| \(.+', '', r)
    return int(total_bytes)
def get_total_rx_bytes(interface):
    r = os.popen('ifconfig ' + interface + ' | grep "RX bytes"').read()
    total_bytes = re.sub(' \(.+', '', r)
    total_bytes = re.sub('.+?:', '', total_bytes)
    return int(total_bytes)
def NetSpeedCheck(interface,direction,cycle):
    get_total_bytes = get_total_tx_bytes if direction == 'tx' else get_total_rx_bytes
    last = get_total_bytes(interface)
    time.sleep(cycle)
    delta = get_total_bytes(interface) - last
    netspeed = delta /cycle / 1000
    return netspeed
def PingCheck(cloud_ip):
    popen_file = os.popen('ping -c 10 -i 0.4' + ' ' + cloud_ip )
    result= popen_file.read()
    #计算丢包率：
    packet_pattern = ".* packet loss"
    re_packet = re.findall(packet_pattern, result)
    packet_list = re_packet[0].split(' ')
    packet_send = float(packet_list[0])
    packet_receive = float(packet_list[3])
    packetloss = (packet_send - packet_receive) / packet_send * 100
    if packetloss > 10:#丢包率是前提，当其很大时，即使此时测得的rtt小也无济于事
        adv_rtt = 120 #赋给一个较大的值，表示通信质量差
        mdev_rtt = 120
    else:   #丢包率满足的前提下，计算rtt
        rtt_pattern = "rtt .*"
        re_rtt = re.findall(rtt_pattern,result)
        rtt_list = re_rtt[0].split(' ')
        rtt_time = rtt_list[3].split('/')
        time_list = []
        for x in range(len(rtt_time)):
            time_list.append(float(rtt_time[x]))
        adv_rtt = time_list[1]
        mdev_rtt = time_list[2]
    loss_and_rtt = [packetloss,adv_rtt,mdev_rtt]
    return loss_and_rtt
def TopicHzCheck():
    # hz = os.popen("python rostopic.py | grep average")
    # list = hz.read().strip("\n").split(" ")
    # rdst = float(list[2])
    # return rdst
    file = os.popen("python rostopic.py")
    while 1:
        hz = file.readline()
        # print hz
        if "rate" in hz:#确保能够读到第一个出现的rate数据
            file.read()  # 把剩余的内容读完,不然会报错
            list = hz.strip("\n").split(" ")
            rdst = float(list[2])
            break
        if not hz: #如果读完了,还没有rate信息
            rdst = 0
            break
    return rdst
def CompressRateCheck():
    param = rospy.get_param("camera/left/image/compressed")
    cur_quality = param["jpeg_quality"]
    return cur_quality
#--------------------------计算qos等级----------------------------#
def QosRTT(cloud_ip):#单考虑rtt的qos_score;暂定tg:10ms,tb:150ms.设tg=0.1*tc;tc可以近似用最大rdst的倒数表示,比如云端最快处理能力是10hz,
    # 也就是说完成一次任务最少用时是0.1s,我们就用这个值评估我们的tc,那么tg近似设为10ms.tb的设置应该综合考虑,既要从云端比本地用时少考虑,又得保持
    #基本的处理能力,比如我们允许最低的频率为6hz,也就是处理一次任务的时间是0.15s,但是如果rtt就超过这个值,即使它用时比本地少,我们也认为是差的.]
    [packet_loss,adv,mdev] = PingCheck(cloud_ip)
    Tg = 10
    Tb = 100
    if adv <= Tg:
        Qt = 100
    elif adv<=Tb:
        Qt = (Tb-adv)/(Tb-Tg)*100
    else:
        Qt = 0
    if Qt < 0:
        Qt = 0
    return [packet_loss,adv,Qt]
def QosHz():#单考虑hz的qos score
    rsrc = rospy.get_param("/camera/camera_splite/src_rate") #获取源图像发布频率
    #print "rsrc:"+str(rsrc)
    rdst = TopicHzCheck()
    Qr = float(rdst)/rsrc*100
    if Qr > 100:
        Qr = 100
    return [rdst,Qr]
def QosCompressed():
    pre_quality = 80
    cur_quality = CompressRateCheck()
    Qs = float(cur_quality)/pre_quality*100
    return [cur_quality,Qs]
def QosWeight(cloud_ip): #计算最终的加权Qos,并且求3次平均值
    #设置权重
    Wt = 0.6
    Wr = 0.3
    Ws = 0.1
    Qt = 0
    Qr = 0
    Qs = 0
    Q = 0
    packet_loss =0
    rtt =0
    rdst = 0
    cur_quality = 0
    netspeed = 0
    for i in range(5):
        speed = NetSpeedCheck("wlan0","rx",2)
        netspeed = netspeed + speed
        [r,Qrr] = QosHz()
        [loss,adv,Qtt] = QosRTT(cloud_ip)
        [compress,Qss] = QosCompressed()
        packet_loss = packet_loss + loss  # 求5次packet_loss平均值
        rtt = rtt + adv #求5次rtt平均值
        rdst = rdst + r #求5次rdst平均值
        cur_quality = cur_quality + compress
        Qt = Qt + Qtt
        Qr = Qr + Qrr
        Qs = Qs + Qss
        Q = Q + Wt*Qtt + Wr*Qrr + Ws*Qss#求5次Q平均值
    result = [netspeed/5,rtt/5,rdst/5,cur_quality/5,Qt/5,Qr/5,Qs/5,Q/5]
    return result
    #给一个初始值，否则申请云端服务会出现：UnboundLocalError: local variable “qoslevel” referenced before assignment？(变量赋值前没有定义)
    #按理说不会出现这种错误的啊？
def QosLevel(qos_score):#5-15:每个等级只占15, 每个Q等级占据的太小了,所以更改方案,Q=1,占据20;Q=2占据20,Q=3占据20
    qos_level = 1
    if 80 < qos_score < 100:
        qos_level = 1
    elif  60 < qos_score <= 80:
        qos_level = 2
    elif 40 < qos_score <= 60:
        qos_level = 3
    elif qos_score <= 40:
        qos_level = 4
    return qos_level

#-----------测试主函数---------------#
if __name__ == "__main__":
    # rdst= TopicHzCheck()
    # print rdst
    QosCompressed()
    #[packet_loss,adv_rtt] = PingCheck(cloud_ip)
    #qos_level = Qos(cloud_ip)
    #print packet_loss