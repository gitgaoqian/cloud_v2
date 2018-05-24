# -*- coding: utf-8 -*-
"""
created on 2018-5-24
CloudROSServer.py目的将计算服务和存储服务合二为一，统一到一个服务器下，各自维护相应的URI.计算服务和存储服务的程序还各自放在原来的包。
@author: ros
"""
import flask
import os
from threading import Thread
import MySQLdb as mdb
import sys
import time
import IPy

services_list=['addition','stereo_proc','teleop','monitor']
app = flask.Flask(__name__)
if "CLOUD_IP" not in os.environ:
    print "Can't find environment variable CLOUD_IP."
    sys.exit(1)
#设置服务端口
cloud_ip = os.environ['CLOUD_IP']
port = 5566

class CloudROS():
    def __init__(self):
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
                    return self.ServiceOperation(usr_ip=usr_ip,service=service,action=action)
        #路由存储服务URI
        @app.route('/storage/<robotID>/<action>', methods=['POST'])
        def StoreServiceHandler(robotID,action):
            token = flask.request.remote_addr
            store_is_auth = self.StoreIsAuth(token)  # 首先进行身份验证
            if not store_is_auth:  # 验证失败
                return "Auth failed,the exo/monitor has no access to the cloud"
            self.ROSNetworkConfig()
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
    #计算服务相关函数
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
    def ServiceOperation(self,usr_ip,service,action):
        return_info = None
        container = usr_ip +'_'+service  # 容器命名规则:该服务对应唯一的docker的标识名字
        image = self.GetImageByService(service) # 在数据库中根据service找到对应的镜像
        is_usr = self.IsUsrinUsrInfo(usr_ip, service)  # 判断表usr_info中是否有该usr的数据
        if not is_usr:  # 没有,则在表usr_info插入新的数据
            self.InsertUsrInfo(usr_ip, service, container, image)
        status = self.GetServiceStatus(container) # 获取当前服务状态,即对应服务的容器是否处于运行状态
        if action != "start" and action != "stop":
            return_info =  action + " not permitted! action should be 'start' or 'stop' "
        if status == 'running' and action == 'start':
            return_info =  "The service is running, start the service repeatly"
        if status == 'running' and action == 'stop':#停止服务,关闭容器
            os.system("sudo docker stop "+container)#应该判断是否停止成功?4.23
            status = self.GetServiceStatus(container)
            self.UpdateUsrInfo(usr_ip,service,status)
            return_info =  "the service:" + service + " stop sucessfully"
        if status == 'stopped' and action == 'start':#开启容器服务
            #thread.start_new_thread(self.StartContainer,(container,image,usr_ip))
            Thd = Thread(target=self.StartContainer,args=(container,image,usr_ip))
            Thd.start()#应该添加判断服务是否开始成功?4.23
            time.sleep(1)
            status = self.GetServiceStatus(container)
            self.UpdateUsrInfo(usr_ip,service,status)
            return_info = "the service:" + service + " run sucessfully"
        if status == 'stopped' and action == 'stop':
            return_info = "The service is stopped,stop the same service repeatly"
        #每次成功的服务请求后,都要更新数据库:usr_info和docker
        return return_info
    def GetServiceStatus(self,container):
        #判断服务的状态其实就是判断系统中是否有运行服务的docker容器
        pipfile = os.popen("sudo docker ps -a -f name=" + container + ' | grep ' + container)
        docker_ps = pipfile.read()
        if not docker_ps:#如果为空
            status = "stopped"
        else:
            if 'Exited' in docker_ps:
                # 如果容器处于启动后又关闭的状态,先将其删除
                os.system('sudo docker rm ' + container)
                status = "stopped"
            if 'Up' in docker_ps:
                status = "running"
        return status
    def StartContainer(self,container,image,usr_ip):
        ros_master_uri = 'http://'+usr_ip+':11311'
        os.system("sudo docker run --name " + container + " " + image+" "+ros_master_uri)
    def GetImageByService(self, service):
        self.cur.execute("select * from image where service=%s", service)
        result = self.cur.fetchall()#获取限制条件下的结果,默认返回数组,在链接函数中加上参数cursorclass = MySQLdb.cursors.DictCursor,返回字典形式
        image = str(result[0][1])
        return image
    def InsertUsrInfo(self,usr_ip,service,container,image):
        self.cur.execute("insert into usr_info values (%s,%s,%s,%s,%s)",(usr_ip,service,None,container,image))
        self.conn.commit()
    def UpdateUsrInfo(self,usr_ip,service,status):
        self.cur.execute("update usr_info set status=%s  where usr_ip=%s and service=%s",(status,usr_ip,service))
        self.conn.commit()
    #存储服务相关函数
    def StoreIsAuth(self,token):
        # 此处设置token为ip,判断ip处于的子网段是否在数据库NeuExo的token表中
        subnet = str((IPy.IP(token).make_net('255.255.255.0')))#找到ip在的网段ex:192.168.1.0/24
        rows = self.storecur.execute("select * from token where token=%s", subnet)
        if rows == 0:
            return False
        else:
            return True
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
    def ROSNetworkConfig(self):
        ros_master_ip = flask.request.remote_addr
        ros_master_uri = 'http://' + ros_master_ip + ':11311'
        os.environ['ROS_MASTER_URI'] = ros_master_uri
        os.environ['ROS_IP'] = cloud_ip
    def StoreData(self, robotID):
        os.system('rosrun neu_wgg store_service.py '+robotID+" __name:=StoreService"+robotID)
    def FetchData(self, robotID):
        os.system('rosrun neu_wgg fetch_service.py ' + robotID+" __name:=FetchService"+robotID)
if __name__ == '__main__':
    cloudros = CloudROS()