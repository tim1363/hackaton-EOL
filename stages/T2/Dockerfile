FROM ros:humble-ros-core-jammy AS messages

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake \
        python3-colcon-common-extensions ros-humble-ament-cmake \
        ros-humble-geometry-msgs ros-humble-rosidl-default-generators \
        ros-humble-rosidl-generator-dds-idl \
    && rm -rf /var/lib/apt/lists/*

COPY stages/T2/vendor/unitree_go /tmp/unitree_ws/src/unitree_go
WORKDIR /tmp/unitree_ws
RUN bash -c 'source /opt/ros/humble/setup.bash && colcon build --merge-install --install-base /opt/unitree --cmake-args -DBUILD_TESTING=OFF'

FROM ros:humble-ros-core-jammy

RUN apt-get update \
    && apt-get install -y --no-install-recommends libegl1 libgl1 libglfw3 libx11-6 \
        python3-pip ros-humble-geometry-msgs ros-humble-rmw-cyclonedds-cpp \
        ros-humble-rosgraph-msgs ros-humble-rosidl-default-runtime \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --no-cache-dir 'numpy==1.26.4' 'mujoco==3.3.7' \
    && useradd --uid 10001 --user-group --create-home participant

COPY --from=messages /opt/unitree /opt/unitree
COPY stages/T2/ /opt/rh/T2/
COPY --chmod=0755 stages/T2/entrypoint.sh /entrypoint.sh
ENV HOME=/home/participant
WORKDIR /home/participant
USER 10001:10001
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ping"]
