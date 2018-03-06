#!/usr/bin/env python
# -*- coding: utf-8 -*-
#ping监控时延,iperf监控带宽
import rospy
import thread
import clientlib as client
import time
qos_level = 1
def QosMonitor(cloud_ip):
    global  qos_level
    while 1:
        qos_level = client.Qos(cloud_ip)
def QOS():
    rospy.init_node('QOS', anonymous=True)
    pre_rate = 10.0
    thread.start_new_thread(QosMonitor, (cloud_ip,))
    while not rospy.is_shutdown():
        if qos_level == 1:
            print "qos_level:1"
            time.sleep(1)
        elif qos_level == 2:  # 1 change the rate of ros publisher with the qos mechanism
            print "qos_level:2,change the rate"
            time.sleep(1)
            cur_rate = pre_rate / 2
            rospy.set_param("img_pub_rate",cur_rate)
        elif qos_level == 3:  # 2 stop some services that are not important
            print "qos_level:3,stop some services"
            os.system("rosrun dynamic_reconfigure dynparam set /camera/left/image/compressed jpeg_quality 30")
            os.system(" rosrun dynamic_reconfigure dynparam set /camera/right/image/compressed jpeg_quality 30")
            time.sleep(1)
if __name__ == '__main__':
    try:
        QOS()
    except rospy.ROSInterruptException:
        pass


