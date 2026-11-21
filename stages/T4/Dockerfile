FROM ros:humble-ros-core-jammy

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-numpy \
        ros-humble-geometry-msgs ros-humble-nav-msgs ros-humble-rclpy \
        ros-humble-rmw-cyclonedds-cpp ros-humble-rosgraph-msgs \
        ros-humble-sensor-msgs ros-humble-tf2-ros-py \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --user-group --create-home participant

COPY stages/T4/ /opt/rh/T4/
COPY --chmod=0755 stages/T4/entrypoint.sh /entrypoint.sh
ENV HOME=/home/participant
WORKDIR /home/participant
USER 10001:10001
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ping"]
