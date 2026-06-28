cmake_minimum_required(VERSION 3.8)
project(my_bot)

find_package(ament_cmake REQUIRED)

install(
  PROGRAMS
    scripts/diff_drive_base.py
    scripts/wait_for_real_ready.py
    scripts/wait_for_slam_ready.py
    scripts/wait_for_sim_ready.py
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY
    launch
    config
    description
    rviz
    worlds
    maps
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
