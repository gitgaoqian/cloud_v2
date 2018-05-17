#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ping监控时延,
import rospy
import thread
import clientlib as client
import os

qos_level = 1
if "CLOUD_IP" not in os.environ:
    print "Can't find environment variable CLOUD_IP."
    sys.exit(1)
class QosAnalysis():
    def __init__(self):
        self.cloud_ip = os.environ['CLOUD_IP']
        self.pre_rate = 10.0
        self.pre_quality = 80
        self.initial_score = 100
        self.interface = 'wlan1'
        rospy.init_node('QoS', anonymous=True)
        self.Anjustment()
    def QosMonitor(self, cloud_ip):
        last_score = self.initial_score
        while 1:
            # 实时记录rtt,netspeed,qos_score 和 qos_level从而来绘制qos动态图
            [rtt, netspeed, qos_score] = client.QosScore(self.interface, cloud_ip, last_score)
            last_score = qos_score
            qos_level = client.QosLevel(qos_score)
            rtt_txt = open('/home/ros/catkin_ws/src/cloud_v2/scripts/python/rtt.txt', 'a+')
            netspeed_txt = open('/home/ros/catkin_ws/src/cloud_v2/scripts/python/netspeed.txt', 'a+')
            qos_level_txt = open('/home/ros/catkin_ws/src/cloud_v2/scripts/python/qos_level.txt', 'a+')
            qos_score_txt = open('/home/ros/catkin_ws/src/cloud_v2/scripts/python/qos_score.txt', 'a+')
            rtt_txt.write(str(rtt) + '\n')
            netspeed_txt.write(str(netspeed) + '\n')
            qos_score_txt.write(str(qos_score) + '\n')
            qos_level_txt.write(str(qos_level) + '\n')
            print "rtt:  " + str(rtt)
            print "netspeed:  " + str(netspeed)
            print "qos_score:  " + str(qos_score)
            print "qos_level:  " + str(qos_level)

    def ChangeQuality(self, quality):
        os.system("rosrun dynamic_reconfigure dynparam set /camera/left/image/compressed jpeg_quality " + str(quality))
        os.system("rosrun dynamic_reconfigure dynparam set /camera/right/image/compressed jpeg_quality " + str(quality))
    def ChangeRate(self, rate):
        rospy.set_param("img_pub_rate", rate)
    def Anjustment(self):
        thread.start_new_thread(self.QosMonitor(), (self.cloud_ip,))
        while not rospy.is_shutdown():
            if qos_level == 1:
                # print "qos_level:1"
                self.ChangeQuality(self.pre_quality)
                self.ChangeRate(self.pre_rate)
            elif qos_level == 2:  # change the rate of ros publisher with the qos mechanism
                # print "qos_level:2,change the rate"
                cur_rate = self.pre_rate / 2
                self.ChangeQuality(self.pre_quality)
                self.ChangeRate(cur_rate)
            elif qos_level == 3:  # 2 decrease the compressed rate
                # print "qos_level:3,stop some services"
                cur_quality = self.pre_quality / 2
                self.ChangeQuality(cur_quality)
if __name__ == '__main__':
    try:
        QosAnalysis()
    except rospy.ROSInterruptException:
        pass
