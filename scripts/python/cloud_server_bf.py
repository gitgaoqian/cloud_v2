# -*- coding: utf-8 -*-
"""
Created on Wed Apr 12 08:55:54 2017

@author: ros
"""

import flask
from flask import render_template
import os
import thread
import sys
import time


services_list=['addition','stereo_proc','teleop','monitor']
app = flask.Flask(__name__)
if "CLOUD_IP" not in os.environ:
    print "Can't find environment variable CLOUD_IP."
    sys.exit(1)

cloud_ip = "192.168.1.102"

def service_start(service):
    if service == 'addition':
        os.system('rosrun base_control addtwointserver.py')
    elif service == 'stereo_proc':
        os.system('roslaunch mycamera stereo_proc.launch')
    elif service == 'teleop':
        os.system('docker run --name mydocker ros:turtle')
    elif service == 'monitor':
        os.system('rosrun rqt_plot rqt_plot')
    elif service == "move_base":
        os.system('roslaunch rbx1_nav fake_move_base_blank_map.launch')
    else:
	return 'service not exsit!'
@app.route('/cloud_service/<service>/<action>', methods=['POST'])
def cloud_service(service,action):
    ros_master_ip = flask.request.remote_addr
    ros_master_uri = 'http://'+ros_master_ip+':11311'
    os.environ['ROS_MASTER_URI']=ros_master_uri
    os.environ['ROS_IP']=cloud_ip
    if action == 'start':
        thread.start_new_thread(service_start,(service,))
        time.sleep(5)
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
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")

if __name__ == '__main__':
    app.run(host=cloud_ip, port=5566, threaded=True)

    #threaded = True:开启app路由多线程并发,可以同时处理多个http请求，即路由函数可以同时执行
    #threaded = False:开启app路由单线程，一次只能处理一个http请求


