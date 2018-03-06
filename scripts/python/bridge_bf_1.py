#!/usr/bin/env python
import rospy
from cloud_v2.srv import call
import clientlib as bridge_client
import localservicelib as localservice
import time
import thread
import os

# status:cloud service start:flag=1;local service start:flag=0;default flag=-1.
cloud_ip = os.environ['CLOUD_IP']
cloud_service_port = 'http://' + cloud_ip + ':5566'
ros_ip = os.environ['ROS_IP']
ros_master_uri = 'http://' + ros_ip + ':11311'
services = []  # store the request service
startaction = ['start', 'startall']
stopaction = ['stop', 'stopall', 'list']
exit_flag = 0  # each thread has a common exit flag:exit_flag
exit_flag_name = ' '  # each thread has a its own exit flag:exit_flag_name
dic = {}  # dic:value;dic is exit_flag_name;vlaue is 0 or 1
def switch(service, action):
    # if request service start or services startall,encouer to switch circle
    global exit_flag
    global dic
    global exit_flag_name
    exit_flag_name = service + '_exit_flag'
    dic[exit_flag_name] = 0
    flag = -1
    while 1:
        package_loss = bridge_client.net_check(cloud_ip)
        url = cloud_service_port + "/cloud_service/" + service + "/" + action
        if flag == -1:
            if package_loss <= 10:  # initial cloud service
                bridge_client.cloud_service_request(url)  # start service or startall services firstly in cloud
                flag = 1  # cloud serice start status
            else:
                localservice.local_service(service, action)  # start service or startall services firstly in local
                flag = 0  # local servie start status
        if flag == 1:
            if package_loss > 10:  # switch to local service
                print 'switch to local service'
                localservice.local_service(service, action)  # start local service
                flag = 0  # local servie start status
        if flag == 0:
            if package_loss <= 10:  # switch to cloud service
                print 'switch to cloud service'
                bridge_client.cloud_service_request(url)
                flag = 1
        if exit_flag == 1:
            break
        if dic[exit_flag_name] == 1:
            break
def handle_request(data):
    global exit_flag
    global exit_flag_name
    global dic
    service = data.service_name
    action = data.action_name
    if action in startaction:
        thread.start_new_thread(switch, (service, action))
        return 'received the service request '
    elif action in stopaction:
        if action == 'stopall':
            exit_flag = 1
        if action == 'stop':
            exit_flag_name = service + '_exit_flag'
            dic[exit_flag_name] = 1
        url = cloud_service_port + "/cloud_service/" + service + "/" + action
        bridge_client.cloud_service_request(url)
        return 'received the service request'
def bridge_server():
    rospy.init_node('bridge_server')
    rospy.Service('bridge_service', call, handle_request)
    # rospy.Service('service_find', request,handle_list)
    print "bridge_server ready for client."
    rospy.spin()
if __name__ == "__main__":
    bridge_server()





