import os
import thread
services_list = ['addition','keyboard_control']
def service_start(service):
    if service == 'addition':
	os.system('rosrun base_control addtwointserver.py')
    elif service == 'keyboard_control':
	os.system('rosrun turtlesim turtle_teleop_key')
def local_service(service,action):
     if service == 'services':
     	if action == 'startall':
	    for service in services_list:
	         thread.start_new_thread(service_start,(service,))
	    print "all local services starting"
 	elif action == 'stopall':
	    for service in services_list:
	         os.system('sh ~/cloud/stop.sh'+service)
	    print 'all local services closing '
	else:
	    print 'action not exist!'
     else:
	if action == 'start':
	   if service in services_list:
	         thread.start_new_thread(service_start,(service,))
	         print "service "+service+' starting in local'
	   else:
		 print "service "+service+' not exist in local!' 
	elif action == 'stop':
	    if service in services_list:
	         os.system('sh ~/cloud/stop.sh '+service)
	         print "service "+service+' stoping in local'
	    else:
		 print "service "+service+' not exist in local!' 
	else:
	    print 'action not exist'

