# -*- coding: utf-8 -*-
"""
Created on Wed Apr 12 08:52:21 2017

@author: ros
"""
import requests
import os
import thread

startaction=['start','startall']
stopaction=['stop','stopall','list']

   
#检测网络的质量    
def net_check(ipaddress):
    count=os.popen('ping -c 20 -i 0.2'+' '+ipaddress+' '+' | grep "received" | cut -d "," -f 2| cut -d " " -f 2')
    num=count.read()
    packet_loss=(20-int(num))*100/20
    return packet_loss
#云端节点的注册    
def cloud_param_set(url,master_uri):
    value={'ros_master_uri':master_uri}
    r = requests.post( url, data=value)
    return r.text
#根据不同表示服务的ｕrl实现不同云端服务的请求    
def cloud_service_request(url):
    r = requests.post( url)
    url_split = url.split('/')
    if url_split[5] in startaction:
        print r.text
    elif url_split[5] in stopaction:
	print r.text
	return r.text

    


  
