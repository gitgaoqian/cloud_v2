#!/usr/bin/env python
import sys
import rospy
from cloud_v2.srv import call


def local_client(service,action):
    rospy.wait_for_service('bridge_service')
    try:
        client = rospy.ServiceProxy('bridge_service', call)
        resp1 = client(service,action)
        return resp1
    except rospy.ServiceException, e:
        print "Service call failed: %s"%e

if __name__ == "__main__":
    service = str(sys.argv[1])
    action = str(sys.argv[2])
    print "request "+service+' '+action
    print " %s"%(local_client(service,action))
    