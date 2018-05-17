#!/usr/bin/env python
# coding: utf-8
'''
created at 2018-4-12
'''
# import os
# import thread
# import time
# def hz():
#     os.system("rostopic hz /camera/left/image_raw __name:=topichz")
# def main():
#     thread.start_new_thread(hz,())
#     time.sleep(2)
#     os.system("rosnode kill topichz")
#     time.sleep(1)
#
# if __name__ == '__main__':
#     main()
#
#-----updated at 2018-4-14-------运行中时而出现错误:Unhandled exception in thread started by sys.excepthook is missing lost sys.stderr
# 搜索得到的分析是:子线程还没有退出,主线程就退出了,改为下面的这种守护线程形式---------------#
# import os
# from threading import Thread
# import sys
# import time
# def hzcheck():
#     os.system("rostopic hz /turtle1/pose __name:=topichz")
# if __name__ == '__main__':
#     t = Thread(target=hzcheck, name="topichz")
#     t.setDaemon(True)
#     t.start()
#     time.sleep(2)
#     os.system("rosnode kill topichz")
#     time.sleep(2)

#-------------------updated at 2018-4-15 改用subprocss模块
import subprocess
import shlex
import time
cmdstr = "rostopic hz /camera/points2 __name:=topichz"
cmdlist = shlex.split(cmdstr)#将命令字符串转换成列表
child = subprocess.Popen(cmdlist,stdout=subprocess.PIPE)
# print (child.pid)
time.sleep(2)
child.terminate()
child.kill
while 1:
    if child.poll() != None:
        print (child.poll())
        print("child process end")
        break
#当子进程退出后,读取子进程管道输出
file = child.stdout.read()
print (file)
print ("parent process end")

