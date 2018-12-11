#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
与CloudROSServer.py相比唯一不同之处就是计算节点没有运行在容器中。该程序是在CLoudROSServer.py基础上稍加修改的。所以包含了身份验证、服务查询、状态查询等预处理
计算服务中涉及到的数据库还是用的CLoudROSServer.py中的，虽然也会涉及到获取容器镜像等操作，但是我们最终启动服务的操作是直接启动节点，不再是启动对应的容器。
@author: ros
"""
import flask
import os
from threading import Thread
import MySQLdb as mdb
import sys
import time
import IPy
import signal

# services_list=['addition','stereo_proc','teleop','monitor']
app = flask.Flask(__name__)
if "CLOUD_IP" not in os.environ:
    print "Can't find environment variable CLOUD_IP."
    sys.exit(1)
#设置服务端口
cloud_ip = os.environ['CLOUD_IP']
port = 5566
cloudros = None

class CloudROS():
    def __init__(self):
        signal.signal(signal.SIGINT, self.ExitFunction)#用于处理计算服务的中断异常
        #连接计算服务数据库,并创建游标
        self.conn = mdb.connect(host="127.0.0.1", user="root", db="CloudROS", passwd="ubuntu", charset="utf8")
        self.cur = self.conn.cursor()
        #连接存储服务数据库
        self.storeconn = mdb.connect(host="127.0.0.1", user="root", db="NeuExo", passwd="ubuntu", charset="utf8")
        self.storecur = self.storeconn.cursor()
        #路由计算服务URI
        @app.route('/compute/<service>/<action>', methods=['POST'])
        def ComputeServiceHandler(service,action):#负责具体的服务流程以及返回提示信息到用户
            usr_ip = flask.request.remote_addr
            token = usr_ip
            is_auth = self.IsAuth(token)#首先进行身份验证
            if not is_auth:#返回验证失败
                return "Auth failed"
            else:
                # 服务查询:通过image数据库判断云端是否有该服务
                is_service = self.IsService(service)
                if not is_service:#返回客户端服务不存在
                    return "service not exit!"
                else:#对该用户申请的服务进行具体操作
                    return self.ComputeServiceOperation(usr_ip=usr_ip,service=service,action=action)
        #路由存储服务URI
        @app.route('/storage/<robotID>/<action>', methods=['POST'])
        def StoreServiceHandler(robotID,action):
            usr_ip = flask.request.remote_addr
            token = usr_ip
            store_is_auth = self.IsAuth(token)  # 首先进行身份验证
            if not store_is_auth:  # 验证失败
                return "Auth failed,the exo/monitor has no access to the cloud"
            self.ROSNetworkConfig(usr_ip)
            if action == "store":
                is_exo = self.IsExoInExoSum(robotID)  # 查看ExoSum中有没有请求的Exo
                if not is_exo:  # 如果没有,创建表,并将该Exo信息插入到ExoSum中
                    self.CreateExoID(robotID)
                    self.InsertExoSum(robotID)
                else:  # 如果ExoSum中有Exo信息,首先清空ExoID的旧的历史数据,然后进行新的数据存储
                    self.ClearExoID(robotID)
                StoreThd = Thread(target=self.StoreData, args=(robotID,))
                StoreThd.start()
                return "Store Exo_" + robotID + " data"
            elif action == "fetch":
                is_exo = self.IsExoInExoSum(robotID)
                if not is_exo:
                    return "No table exo" + str(robotID) + " for fetch"
                else:
                    FetchThd = Thread(target=self.FetchData, args=(robotID,))
                    FetchThd.start()
                    return "Fetch Exo_" + robotID + " data"
            else:
                return action + " not permitted! for monitor,action=fetch;for exo,action=store"
        # 运行云端服务器
        app.run(host=cloud_ip, port=port, threaded=True)
        # threaded = True:开启app路由多线程并发,可以同时处理多个http请求，即路由函数可以同时执行
        # threaded = False:开启app路由单线程，一次只能处理一个http请求

    #计算服务相关函数（计算服务不在容器）
    def IsAuth(self,token):
        # 此处设置token为ip,判断ip处于的子网段是否在数据库CloudROS的token表中
        subnet = str((IPy.IP(token).make_net('255.255.255.0')))#找到ip在的网段ex:192.168.1.0/24
        rows = self.cur.execute("select * from token where token=%s", subnet)
        if rows == 0:
            return False
        else:
            return True
    def IsService(self,service):
        rows = self.cur.execute("select * from image where service=%s", service)
        if rows == 0:  # 说明服务不存在
            return False
        else:
            return True
    def IsUsrinUsrInfo(self,usr_ip,service):
        rows = self.cur.execute("select * from usr_info where usr_ip=%s and service=%s",(usr_ip,service))
        if rows == 0:
            return False
        else:
            return True
    def ComputeServiceOperation(self,usr_ip,service,action):
        container = usr_ip +'_'+service  # 容器命名规则:该服务对应唯一的docker的标识名字
        image = self.GetImageByService(service) # 在数据库中根据service找到对应的镜像
        is_usr = self.IsUsrinUsrInfo(usr_ip, service)  # usr_info是动态表，判断表usr_info中是否有该usr的数据,如果新请求者，添加该请求者的信息。
        # usr_info包括了请求者，服务名称、服务状态等信息。
        if not is_usr:  # 没有,则在表usr_info插入新的数据
            self.InsertUsrInfo(usr_ip, service, container, image)
        status = self.GetServiceStatus(usr_ip,service) # 获取当前服务状态
        if action != 'start' and action != 'stop':
            return action + " not permitted! action should be 'start' or 'stop' "
        if status == 'running' and action == 'start':
            return "The service is running, start the service repeatly"
        if status == 'running' and action == 'stop':#停止服务
            os.system('sh ~/catkin_ws/src/cloud_v2/scripts/stop.sh ' + service)#应该判断是否停止成功?4.23
            status = "stopped"
            self.UpdateUsrInfo(usr_ip,service,status)
            return "the service:" + service + " stop sucessfully"
        if status == 'stopped' and action == 'start':#开启容器服务；开启节点服务
            #thread.start_new_thread(self.StartContainer,(container,image,usr_ip))
            Thd = Thread(target=self.StartService,args=(usr_ip,service))
            Thd.start()#应该添加判断服务是否开始成功?4.23
            time.sleep(1)
            status = "running"
            self.UpdateUsrInfo(usr_ip,service,status)
            return "the service:" + service + " run sucessfully"
        if status == 'stopped' and action == 'stop':
            return "The service is stopped,stop the same service repeatly"
        #每次成功的服务请求后,都要更新数据库:usr_info和docker

    def GetServiceStatus(self,usr_ip,service):
        #从usr_info中获取状态信息
        self.cur.execute("select * from usr_info where usr_ip=%s and service=%s", (usr_ip, service))
        result = self.cur.fetchall()  # 获取限制条件下的结果,默认返回数组
        status = str(result[0][2])
        return status
    def StartService(self,usr_ip,service):
        self.ROSNetworkConfig(usr_ip)
        if service == 'addition':
            os.system('rosrun base_control addtwointserver.py')
        elif service == 'stereo_proc':
            os.system('roslaunch mycamera stereo_proc.launch')
        elif service == 'teleop':
            os.system("rosrun turtlesim turtle_teleop_key")
        elif service == 'monitor':
            os.system('rosrun rqt_plot rqt_plot')
        elif service == "image_detect":  # updataed on 2018-11-14:添加第三方服务--图像识别归为计算服务
            os.system('roslaunch mycamera image_detect.launch')
        elif service == "object_track":
            os.system('roslaunch mycamera object_tracker.launch')
    def GetImageByService(self, service):
        self.cur.execute("select * from image where service=%s", service)
        result = self.cur.fetchall()#获取限制条件下的结果,默认返回数组,在链接函数中加上参数cursorclass = MySQLdb.cursors.DictCursor,返回字典形式
        image = str(result[0][1])
        return image
    def InsertUsrInfo(self,usr_ip,service,container,image):
        self.cur.execute("insert into usr_info values (%s,%s,%s,%s,%s)",(usr_ip,service,"stopped",container,image))#默认状态是停止
        self.conn.commit()
    def UpdateUsrInfo(self,usr_ip,service,status):
        self.cur.execute("update usr_info set status=%s  where usr_ip=%s and service=%s",(status,usr_ip,service))
        self.conn.commit()
    #存储服务相关函数
    def IsExoInExoSum(self, robotID):
        rows = self.storecur.execute("select * from exo_sum where id=%s", (robotID))
        if rows == 0:
            return False
        else:
            return True
    def InsertExoSum(self, robotID):
        self.storecur.execute("insert into exo_sum values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (robotID,None,None,None,None,
                                                                                        None,None,None,None,None))
        self.storeconn.commit()
    def CreateExoID(self,robotID):
        self.storecur.execute("create table exo_"+str(robotID)+" (count int,leftk float,lefth float,"
                                                         "rightk float,righth float,temp float,hum float,"
                                                         "atmo float,longitude float,latitude float)")
    def ClearExoID(self,robotID):
        self.storecur.execute("truncate table exo_"+robotID)
        self.storeconn.commit()
    def StoreAndFetch(self,robotID,action):
        if action == "store":
            is_exo = self.IsExoInExoSum(robotID)  # 查看ExoSum中有没有请求的Exo
            if not is_exo:  # 如果没有,创建表,并将该Exo信息插入到ExoSum中
                self.CreateExoID(robotID)
                self.InsertExoSum(robotID)
            else:  # 如果ExoSum中有Exo信息,首先清空ExoID的旧的历史数据,然后进行新的数据存储
                self.ClearExoID(robotID)
            StoreThd = Thread(target=self.StoreData,args=(robotID,))
            StoreThd.start()
            return "Store Exo_" + robotID + " data"
        elif action == "fetch":
            is_exo = self.IsExoInExoSum(robotID)
            if not is_exo:
                return "No table exo" + str(robotID) + " for fetch"
            else:
                FetchThd = Thread(target=self.FetchData,args = (robotID,))
                FetchThd.start()
                return "Fetch Exo_" + robotID + " data"
        else:
            return action + " not permitted! for monitor,action=fetch;for exo,action=store"
    def ROSNetworkConfig(self,usr_ip):
        ros_master_uri = 'http://' + usr_ip + ':11311'
        os.environ['ROS_MASTER_URI'] = ros_master_uri
        os.environ['ROS_IP'] = cloud_ip
    def StoreData(self, robotID):
        os.system('rosrun neu_wgg store_service.py '+robotID+" __name:=StoreService_"+robotID)
    def FetchData(self, robotID):
        os.system('rosrun neu_wgg fetch_service.py ' + robotID+" __name:=FetchService_"+robotID)
    def ExitFunction(self,signalnum, frame):
        self.cur.execute("truncate table usr_info")#发生中断异常，清楚服务端的用户信息
        sys.exit(0)
if __name__ == '__main__':
    cloudros = CloudROS()
