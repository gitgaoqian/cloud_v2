# -*- coding: utf-8 -*-
"""
Created on Wed Apr 12 08:55:54 2017

@author: ros
"""

import flask
import os
import thread
import sys

services_list=['addition','stereo_proc','teleop','monitor']
app = flask.Flask(__name__)
if "CLOUD_IP" not in os.environ:
    print "Can't find environment variable ROS_IP."
    sys.exit(1)

cloud_ip = os.environ['CLOUD_IP']

def service_start(service):
    if service == 'addition':
        os.system('rosrun smartcar addtwointserver.py')
    elif service == 'stereo_proc':
        os.system('roslaunch mycamera stereo_proc.launch')
    elif service == 'teleop':
        os.system('rosrun turtlesim turtle_teleop_key')
    elif service == 'monitor':
        os.system('rosrun rqt_plot rqt_plot')

    else:
	return 'service not exsit!'

       
@app.route('/cloud_service/setparam', methods=['POST'])
def setparam():
     master_uri=flask.request.form['ros_master_uri']
     os.environ['ROS_MASTER_URI']=master_uri
     os.environ['ROS_IP']=cloud_ip
     return "setparam finished"
     
@app.route('/cloud_service/<service>/<action>', methods=['POST'])
def cloud_service(service,action):
    print flask.request.remote_addr
    if action == 'start':
        thread.start_new_thread(service_start,(service,))    
        return "service " + service + " starting"
    elif action == 'stop':
       os.system('sh ~/catkin_ws/src/cloud_v2/scripts/stop.sh '+service)
       return "service "+service+" closing"
    elif action == 'list':
        return str(services_list)
    elif action == 'startall':
        for service in services_list:
            thread.start_new_thread(service_start,(service,)) 
        return "all services starting"
    elif action == 'stopall':
        for service in services_list:
            os.system('sh ~/catkin_ws/src/cloud_v2/scripts/stop.sh '+service)
        return "all services stoping"
    else:
        return 'action error!'

if __name__ == '__main__':
    app.run(host=cloud_ip, port=5566, threaded=True)#开启app路由并发？


