#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
updated on 2018-4-23
'''
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
cloud_ip = "192.168.1.101"
def QosMonitor(cloud_ip):
    global  qos_level
    #interface = 'wlan1'
    while 1:
        #qos_level = client.Qos(cloud_ip)
        # 实时记录rtt,rdst,qos_score 和 qos_level从而来绘制qos动态图
        #[rdst,qos_score] = client.QosScoreHz()
        [netspeed,rtt,rdst,cur_quality,Qt,Qr,Qs,Q] = client.QosWeight(cloud_ip)
        qos_level = client.QosLevel(Q)
        netspeed_txt = open('/home/ros/qos/netspeed.txt', 'a+')
        rtt_txt = open('/home/ros/qos/rtt.txt','a+')
        rdst_txt = open('/home/ros/qos/rdst.txt','a+')
        compress_txt = open('/home/ros/qos/compress.txt','a+')
        qos_level_txt = open('/home/ros/qos/qos_level.txt','a+')
        qos_score_txt = open('/home/ros/qos/qos_score.txt', 'a+')
        netspeed_txt.write(str(netspeed)+'\n')
        rtt_txt.write(str(rtt)+'\n')
        rdst_txt.write(str(rdst)+'\n')
        compress_txt.write(str(cur_quality)+'\n')
        qos_score_txt.write(str(Q)+'\n')
        qos_level_txt.write(str(qos_level)+'\n')
        print "netspeed: "+str(netspeed)
        print "rtt:  "+str(rtt)
        print "rdst:  "+str(rdst)
        print "Qt: " + str(Qt)
        print "Qr: " + str(Qr)
        print "Qs: " + str(Qs)
        print "Q:  "+ str(Q)
        print "qos_level:  "+str(qos_level)
        print "\n"
def Andjust():
    global cloud_ip
    rospy.init_node('QOS', anonymous=True)
    pre_rate = 10.0
    pre_quality = 80
    thread.start_new_thread(QosMonitor, (cloud_ip,))
    while not rospy.is_shutdown():
        if qos_level == 1:
            # print "qos_level:1"
            time.sleep(1)
            ChangeQuality(pre_quality)
            ChangeRate(pre_rate)
        elif qos_level == 2:  # 2 decrease the compressed rate

            #print "qos_level:2,change the compressed rate"
            cur_quality = pre_quality / 2
            ChangeRate(pre_rate)
            ChangeQuality(cur_quality)
        elif qos_level == 3:  # change the rate of ros publisher with the qos mechanism
            # print "qos_level:3,change the published rate"
            cur_rate = 6
            cur_quality = pre_quality/2
            ChangeQuality(cur_quality)
            ChangeRate(cur_rate)
        elif qos_level == 4:
            os.system('sh ~/catkin_ws/src/cloud_v2/scripts/stop.sh stereo_proc')
def ChangeQuality(quality):
    os.system("rosrun dynamic_reconfigure dynparam set /camera/left/image/compressed jpeg_quality "+str(quality))
    os.system("rosrun dynamic_reconfigure dynparam set /camera/right/image/compressed jpeg_quality "+str(quality))
def ChangeRate(rate):
    rospy.set_param("/camera/camera_splite/src_rate",rate)
if __name__ == '__main__':
    try:
        Andjust()
    except rospy.ROSInterruptException:
        pass


