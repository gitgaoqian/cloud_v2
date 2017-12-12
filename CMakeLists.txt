cmake_minimum_required(VERSION 2.8.3)
project(cloud_v2)

find_package(catkin REQUIRED COMPONENTS
  message_generation
  roscpp
  rospy
  std_msgs
)

## Generate services in the 'srv' folder
 add_service_files(
  FILES
  call.srv
)

## Generate added messages and services with any dependencies listed here
generate_messages(
   DEPENDENCIES
   std_msgs
 )

catkin_package(
#  INCLUDE_DIRS include
#  LIBRARIES cloud
  CATKIN_DEPENDS roscpp rospy std_msgs message_runtime
#  DEPENDS system_lib
)

include_directories(
  ${catkin_INCLUDE_DIRS}
)
