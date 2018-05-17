#!/usr/bin/env python
# -*- coding: utf-8 -*-
import rospy
from turtlesim.msg import Pose
import thread
import clientlib as client
import time
import os
r = 0
class QoS():
    def __init__(self):
        #订阅需要计算频率的话题:/camera/points2
        rospy.Subscriber('/camera/points2', Pose, self.QoSCallback)
    def QosRTT(self):
        [packet_loss, avg, mdev] = self.QosRTT()
        Tb = 10  # rtt基线设定为5ms
        if avg <= Tb:
            Qt = 100
        else:
            Qt = 100 - 0.75 * (avg - Tb)
            if Qt < 0:
                Qt = 0
        return [packet_loss, avg, Qt]

    def QosHz(self,rdst):
        rsrc = 10
        Qr = rdst / rsrc * 100
        return Qr

    def RTTMonitor(self):
        cloud_ip = "192.168.1.102"
        popen_file = os.popen('ping -c 10 -i 0.4' + ' ' + cloud_ip)
        result = popen_file.read()
        # 计算丢包率：
        packet_pattern = ".* packet loss"
        re_packet = re.findall(packet_pattern, result)
        packet_list = re_packet[0].split(' ')
        packet_send = float(packet_list[0])
        packet_receive = float(packet_list[3])
        packetloss = (packet_send - packet_receive) / packet_send * 100
        if packetloss > 10:  # 丢包率是前提，当其很大时，即使此时测得的rtt小也无济于事
            adv_rtt = 120  # 赋给一个较大的值，表示通信质量差
            mdev_rtt = 120
        else:  # 丢包率满足的前提下，计算rtt
            rtt_pattern = "rtt .*"
            re_rtt = re.findall(rtt_pattern, result)
            rtt_list = re_rtt[0].split(' ')
            rtt_time = rtt_list[3].split('/')
            time_list = []
            for x in range(len(rtt_time)):
                time_list.append(float(rtt_time[x]))
            adv_rtt = time_list[1]
            mdev_rtt = time_list[2]
        loss_and_rtt = [packetloss, adv_rtt, mdev_rtt]
        return loss_and_rtt
    def HzMonitor(self,data):
        global r
        rdst = None
        if data != " ":
            r = r+1

    def QoSCallback(self,data):
        #计算话题帧率
        rdst = self.HzMonitor(data)
        # if rdst != None:
        #     Qr = self.QosHz(rdst)
        #     Qt = self.QosRTT()
        # if data != ' ':
        #     rate = 10
        # if time == 2:#求一次Qr
        #     Qr = self.QosHz((time,rate))
        #     Qt = self.QosRTT()
        #     Q = Q + 0.6*Qt + 0.4*Qr
        #     print Q
            # thread.start_new_thread(self.QosHz(),(time,rate))

if __name__ == "__main__":
    rospy.init_node('QoS-Monitor', anonymous=True)
