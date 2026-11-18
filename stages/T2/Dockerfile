# Experimental participant image. The released public simulator image provides
# ROS Humble, CycloneDDS, MuJoCo 3.3.7 and built Unitree messages; no simulator
# process is started by this image. Replace this large base once a minimal,
# independently built runtime has been validated.
ARG BASE_IMAGE=registry.cookcloud.ru/go1-hackathon-remote-stage/go1-sim:v1.0@sha256:c79ddbece6cc7d00f114a9a9a09be0bae061ebb35ca722bcbe51bf75fce1b2e3
FROM ${BASE_IMAGE}

COPY --chown=1000:1000 stages/T2/ /opt/rh/T2/
COPY --chmod=0755 stages/T2/entrypoint.sh /entrypoint.sh
ENV HOME=/home/ros
WORKDIR /home/ros
USER 1000:1000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ping"]
