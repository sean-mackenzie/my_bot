cmake_minimum_required(VERSION 3.8)
project(my_bot)

find_package(ament_cmake REQUIRED)

install(
  PROGRAMS
    scripts/diff_drive_base.py
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY
    launch
    config
    description
    rviz
    worlds
  DESTINATION share/${PROJECT_NAME}
)

ament_package()