# -*- coding: utf-8 -*-
"""
Created on Wed Apr 12 08:52:21 2017

@author: ros
"""
import requests
import os
import time
import math
import re

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
#---ping监控时延和丢包,RttMonitor和PackerLossMonitor是之前分别写的检测函数，现在把这两个因素都放在一个函数里：PingCheck
def RttMonitor(cloud_ip):
    file = os.popen('ping -c 10 -i 0.4' + ' ' + cloud_ip + ' ' + ' | grep "rtt" | cut -d " " -f 4')
    rtt = file.read().strip('\n')
    if rtt != '':
        list = rtt.split('/',3)
        time_list = []
        for x in range(len(list)):
            time_list.append(float(list[x]))
        adv_rtt = time_list[1]
    else:
        adv_rtt = 150 #用较大的值来表示网络断开
    return adv_rtt
def PacketLossMonitor(cloud_ip):
    count=os.popen('ping -c 10 -i 0.4'+' '+cloud_ip+' '+' | grep "received" | cut -d "," -f 2| cut -d " " -f 2')
    num=count.read()
    packet_loss=(20-int(num))*100/20
    return packet_loss
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

#---------------------------iperf监控带宽,netperf监控吞吐量,ifconig间接测网速------------------------#
#iperf测带宽必须在没有应用占据网络的前提下,测得是极限带宽,所以在此处不适合;netperf测得是吞吐量但是它在应用中时而能用时而不能;ifconfig测网速为目前所用
def BwMonitor(cloud_ip):
    file = os.popen('iperf -c '+cloud_ip+' '+'-f M -t 5'+' | grep "sec"') #仅对单线程
    list = file.read().split("  ")
    list_new = list[4].split(" ")
    bw = float(list_new[0])
    return bw
def ThroughputMonitor(cloud_ip):
    file = os.popen('netperf -H ' + cloud_ip + ' -l 2 | grep "2.00"')
    list = file.read().split()
    throughput = float(list[4])
    return throughput
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
    netspeed = delta / cycle / 1000
    return netspeed

#--------------------------计算qos等级----------------------------#
#QosRTT函数是通过rtt直接判断qos_level,现在使用QosScore函数是先通过rtt判断qos_score,然后通过qos_score去判断qos_level
def QosRTT(cloud_ip):
    [packet_loss,avg,mdev] = PingCheck(cloud_ip)
    sdev = math.sqrt(mdev)
    #bw = BwMonitor(cloud_ip)
    #throughput = ThrouthputMonitor(cloud_ip)
    thread_1 = 50
    thread_2 = 100
    thread_3 = 200
    qoslevel = 1
    #给一个初始值，否则申请云端服务会出现：UnboundLocalError: local variable “qoslevel” referenced before assignment？(变量赋值前没有定义)
    #按理说不会出现这种错误的啊？
    if packet_loss > 10:
        qoslevel = 4            # 切换服务到本地
    elif avg<= thread_1:
        qoslevel = 1
    elif thread_1 < avg <= thread_2:
        qoslevel = 2
    elif thread_2<avg<=thread_3:
        qoslevel = 3
    elif thread_3<avg:
        qoslevel = 4
    return qoslevel
def QosScore(interface,cloud_ip,lastscore):
    rtt_high = 100
    rtt_mid = 50
    rtt_low = 30
    netspeed_high = 240
    netspeed_mid = 200
    netspeed_low =150
    qos_score = lastscore
    last_score = lastscore
    [packetloss,advrtt,mdevrtt]=PingCheck(cloud_ip)
    netspeed = NetSpeedCheck(interface,direction = 'tx',cycle=2)
    if packetloss > 10:
        qos_score = 55
    else:
        qos_level = QosLevel(last_score)
        if qos_level == 1:
            if advrtt < rtt_low and netspeed > netspeed_high:
                qos_score = last_score + 2
            if rtt_low < advrtt < rtt_mid or netspeed_mid < netspeed < netspeed_high:
                qos_score = last_score - 1
            if rtt_mid < advrtt < rtt_high or netspeed_low < netspeed < netspeed_mid:
                qos_score = last_score - 2
            if advrtt > rtt_high or netspeed < netspeed_low:
                qos_score = last_score -3
        if qos_level == 2:
            if advrtt < rtt_low and netspeed > netspeed_high:
                qos_score = last_score + 1
            if rtt_low < advrtt < rtt_mid or netspeed_mid < netspeed < netspeed_high:
                qos_score = 78
            if rtt_mid < advrtt < rtt_high or netspeed_low < netspeed < netspeed_mid:
                qos_score = last_score - 1
            if advrtt > rtt_high or netspeed < netspeed_low:
                qos_score = last_score - 2
        if qos_level == 3:
            if advrtt < rtt_low and netspeed > netspeed_high:
                qos_score = last_score + 2
            if rtt_low < advrtt < rtt_mid or netspeed_mid < netspeed < netspeed_high:
                qos_score = last_score + 1
            if rtt_mid < advrtt < rtt_high or netspeed_low < netspeed < netspeed_mid:
                qos_score = 65
            if advrtt > rtt_high or netspeed < netspeed_low:
                qos_score = last_score - 1
        if qos_level == 4:
            if advrtt < rtt_low and netspeed > netspeed_high:
                qos_score = last_score + 3
            if rtt_low < advrtt < rtt_mid or netspeed_mid < netspeed < netspeed_high:
                qos_score = last_score +2
            if rtt_mid < advrtt < rtt_high or netspeed_low < netspeed < netspeed_mid:
                qos_score = last_score + 1
            if advrtt > rtt_high or netspeed < netspeed_low:
                qos_score = last_score -1
        if qos_score > 100:
            qos_score = 100
        if qos_score < 55:
            qos_score = 55
    result = [packetloss,advrtt,netspeed,qos_score]
    return result
def QosLevel(qos_score):
    qos_level = 1
    if 85 < qos_score < 100:
        qos_level = 1
    elif  70 < qos_score <= 85:
        qos_level = 2
    elif 60 < qos_score <= 70:
        qos_level = 3
    elif qos_score <= 60:
        qos_level = 4
    return qos_level

#另一种得到qos_level的方法,分别考虑rtt和netspeed,单一情况对应的level,然后进行加权得到新的level,包含了16种情况,这种方法简单,但是qos_level会有跳变.
def QosLevelInquire(interface,cloud_ip,a,b):# interface是检测网速的网络名称;cloud_ip是云主机的ip;a,b是rtt和netspeed的权值.
    [packetloss, advrtt, mdevrtt] = PingCheck(cloud_ip)
    rtt = advrtt
    netspeed = NetSpeedCheck(interface,direction = 'tx',cycle=2)
    if packetloss > 10:
        rtt_level = 4
        netspeed_level = 4
    else:
        if rtt <= 30:
            rtt_level = 1
        elif rtt <= 50:
            rtt_level = 2
        elif rtt <= 100:
            rtt_level = 3
        else:
            rtt_level = 4
        if netspeed >= 180:
            netspeed_level = 1
        elif netspeed >= 150:
            netspeed_level = 2
        elif netspeed >= 100:
            netspeed_level = 3
        else:
            netspeed_level = 4
    qos_level = round(a*rtt_level + b*netspeed_level) #a,b是权值
    return qos_level
#-----------测试主函数---------------#
# if __name__ == "__main__":
#     # cloud_ip = "192.168.1.102"
#     # #[packet_loss,adv_rtt] = PingCheck(cloud_ip)
#     # qos_level = Qos(cloud_ip)
#     # print packet_loss