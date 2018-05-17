# -*- coding: utf-8 -*-
import subprocess
import rospy
import shlex
import time
cmdstr = "rosparam get /img_pub_rate"
cmdlist = shlex.split(cmdstr)
a = subprocess.Popen(cmdlist,stdout=subprocess.PIPE)
print a.stdout.read()
a = rospy.get_param("/img_pub_rate")
print a

