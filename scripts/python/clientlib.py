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
    rtt_file = os.popen('ping -c 10 -i 0.4' + ' ' + cloud_ip + ' ' + ' | grep "rtt" | cut -d " " -f 4')
    rtt = rtt_file.read().strip('\n')
    if rtt != '':
        list = rtt.split('/',3)
        time_list = []
        for x in range(len(list)):
            time_list.append(float(list[x]))
        adv_rtt = time_list[1]
    else:
        adv_rtt = 100000 #用较大的值来表示网络断开
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
        advrtt = 100000 #赋给一个较大的值，表示通信质量差
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
#---------------------------iperf监控带宽------------------------#
def BwMonitor(cloud_ip):
    bw_file = os.popen('iperf -c '+cloud_ip+' '+'-f M -t 5'+' | grep "sec"') #仅对单线程
    bw = bw_file.read() #bw值
    list = bw.split("  ")
    list1 = list[4].split(" ")
    bw = float(list1[0])
    return bw
#--------------------------计算qos等级----------------------------#
def Qos(cloud_ip):
    [packet_loss,avg,mdev] = PingCheck(cloud_ip)
    sdev = math.sqrt(mdev)
    #bw = BwMonitor(cloud_ip)
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
#-----------测试主函数---------------#
if __name__ == "__main__":
    cloud_ip = "192.168.1.102"
    #[packet_loss,adv_rtt] = PingCheck(cloud_ip)
    qos_level = Qos(cloud_ip)
    print packet_loss

    


  
