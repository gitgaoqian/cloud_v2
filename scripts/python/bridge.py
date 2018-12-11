#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
updated on 2018-4-23
'''
import rospy
from cloud_v2.srv import call
import clientlib as bridge_client
import localservicelib as localservice
import time
import thread
import os

#status:cloud service start:flag=1;local service start:flag=0;default flag=-1.
cloud_ip = os.environ['CLOUD_IP']
cloud_service_port = 'http://'+cloud_ip+':5566'
ros_ip = os.environ['ROS_IP']
ros_master_uri = 'http://'+ros_ip+':11311'
services=[] #store the request service
startaction=['start','startall']
stopaction=['stop','stopall','list']
exit_flag = 0 #each thread has a common exit flag:exit_flag
exit_flag_name = ' '  #each thread has a its own exit flag:exit_flag_name
dic = {} # dic:value;dic is exit_flag_name;vlaue is 0 or 1
qos_level = 1 # qos leve:1--4
def QosMonitor(cloud_ip):
	global qos_level
	while 1:#改为通过百分制评估qos等级 2018-3-25
		[netspeed, rtt, rdst, cur_quality, Qt, Qr, Qs, Q] = bridge_client.QosWeight(cloud_ip)
		qos_level = bridge_client.QosLevel(Q)
def Switch(service,action):
#if request service start or services startall,encouter to switch circle
	global exit_flag
	global dic
	global exit_flag_name
	global qos_level
	global cloud_ip
	exit_flag_name = service+'_exit_flag'
	dic[exit_flag_name]=0
	switch_flag = -1
	if service == "stereo_proc":#在计算服务是stereo_proc时，我们才启动qos监控,updated on 2018-11-20
		thread.start_new_thread(QosMonitor,(cloud_ip,))
	url = cloud_service_port + "/compute/" + service + "/" + action
	while 1:
		#initial the service
		if switch_flag == -1:
			if qos_level != 4: #initial cloud service
				switch_flag = 1  # cloud serice start status
				bridge_client.cloud_service_request(url) #start service or startall services firstly in cloud
			else:
				switch_flag = 0  # local servie start status
				localservice.local_service(service,action) #start service or startall services firstly in local
		#-------SWITCH MECHANISM--------#
		if switch_flag == 1:  # qos mechanism  work when cloud service start
			if qos_level == 4: #switch to local service
				print 'qos_level:4,switch to local service'
				switch_flag = 0  # local servie start status
				localservice.local_service(service,action) #start local service
				time.sleep(1)
		if switch_flag == 0:
			if qos_level != 4: #switch to cloud service
				print 'switch to cloud service'
				switch_flag = 1
				bridge_client.cloud_service_request(url)
		if exit_flag == 1:
			break
		if dic[exit_flag_name] == 1:
			break
def handle_request(data):
	global exit_flag
	global exit_flag_name
	global dic
	service=data.service_name
	action=data.action_name
	if action in startaction:
		thread.start_new_thread(Switch,(service,action))
		return 'received the service request '
	elif action in stopaction:
		if action == 'stopall':
			exit_flag = 1
		if action == 'stop':
			exit_flag_name = service+'_exit_flag'
			dic[exit_flag_name] = 1
		url=cloud_service_port+"/compute/"+service+"/"+action
		bridge_client.cloud_service_request(url)
	return 'received the service request'
def bridge_server():
	rospy.init_node('bridge_server')
	rospy.Service('bridge_service', call, handle_request)
	print "bridge_server ready for client."
	rospy.spin()
if __name__ == "__main__":
	bridge_server()





