#!/usr/bin/env python
# -*- coding: utf-8 -*-
#ping监控时延,
import rospy
import thread
import clientlib as client
import time
import os
qos_level = 1
if "CLOUD_IP" not in os.environ:
    print "Can't find environment variable CLOUD_IP."
    sys.exit(1)
cloud_ip = os.environ['CLOUD_IP']
def QosMonitor(cloud_ip):
    global  qos_level
    last_score = 100 #初始qos_score
    interface = 'wlan1'
    while 1:
        #qos_level = client.Qos(cloud_ip)
        # 实时记录rtt,netspeed,qos_score 和 qos_level从而来绘制qos动态图
        [packetloss,rtt,netspeed,qos_score] = client.QosScore(interface,cloud_ip,last_score)
        last_score = qos_score
        qos_level = client.QosLevel(qos_score)
        rtt_txt = open('/home/ubuntu/qos/rtt.txt','a+')
        netspeed_txt = open('/home/ubuntu/qos/netspeed.txt','a+')
        qos_level_txt = open('/home/ubuntu/qos/qos_level.txt','a+')
        qos_score_txt = open('/home/ubuntu/qos/qos_score.txt', 'a+')
        packetloss_txt = open('/home/ubuntu/qos/packetloss.txt','a+')
        rtt_txt.write(str(rtt)+'\n')
        netspeed_txt.write(str(netspeed)+'\n')
        qos_score_txt.write(str(qos_score)+'\n')
        qos_level_txt.write(str(qos_level)+'\n')
        packetloss_txt.write(str(packetloss)+'\n')
        print "packetloss: "+str(packetloss)
        print "rtt:  "+str(rtt)
        print "netspeed:  "+str(netspeed)
        print "qos_score:  "+str(qos_score)
        print "qos_level:  "+str(qos_level)
def Andjust():
    global cloud_ip
    rospy.init_node('QOS', anonymous=True)
    pre_rate = 10.0
    pre_quality = 80
    thread.start_new_thread(QosMonitor, (cloud_ip,))
    while not rospy.is_shutdown():
        if qos_level == 1:
            #print "qos_level:1"
            ChangeQuality(pre_quality)
            ChangeRate(pre_rate)
        elif qos_level == 2:  # change the rate of ros publisher with the qos mechanism
            # print "qos_level:2,change the rate"
            cur_rate = pre_rate / 2
            ChangeQuality(pre_quality)
            ChangeRate(cur_rate)
        elif qos_level == 3:  # 2 decrease the compressed rate
            # print "qos_level:3,stop some services"
            cur_quality = pre_quality / 2
            ChangeQuality(cur_quality)
def ChangeQuality(quality):
    os.system("rosrun dynamic_reconfigure dynparam set /camera/left/image/compressed jpeg_quality "+str(quality))
    os.system("rosrun dynamic_reconfigure dynparam set /camera/right/image/compressed jpeg_quality "+str(quality))
def ChangeRate(rate):
    rospy.set_param("img_pub_rate",rate)
if __name__ == '__main__':
    try:
        Andjust()
    except rospy.ROSInterruptException:
        pass


