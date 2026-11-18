# Experimental CPU participant image. The public simulator base supplies ROS,
# CycloneDDS, MuJoCo 3.3.7 and Unitree messages. No simulator is launched here.
ARG BASE_IMAGE=registry.cookcloud.ru/go1-hackathon-remote-stage/go1-sim:v1.0@sha256:c79ddbece6cc7d00f114a9a9a09be0bae061ebb35ca722bcbe51bf75fce1b2e3
FROM ${BASE_IMAGE}

COPY --chown=1000:1000 stages/T2/ /opt/rh/T2/
COPY --chown=1000:1000 stages/T3/ /opt/rh/T3/
COPY --chown=1000:1000 actor.npz /opt/rh/actor.npz
RUN echo '7a0e0d2f83017c881e2590079c01b7b6dd7ccd27d66d7e522a81d61c1ce9e0cd  /opt/rh/actor.npz' | sha256sum -c -
COPY --chmod=0755 stages/T3/entrypoint.sh /entrypoint.sh
ENV HOME=/home/ros GO1_POLICY_NPZ=/opt/rh/actor.npz
WORKDIR /home/ros
USER 1000:1000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ping"]
