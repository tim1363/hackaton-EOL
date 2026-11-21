ARG T2_IMAGE=registry.cookcloud.ru/end-of-line/end-of-line@sha256:28054e380fd4071215a3d9b0c61b25f18ea6886b9e66727d96424cbc83d8b4d9
FROM ${T2_IMAGE}
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ros-humble-nav-msgs \
    && rm -rf /var/lib/apt/lists/*
COPY stages/T3/*.py /opt/rh/T3/
COPY stages/T3/weights/ /opt/rh/T3/weights/
COPY --chmod=0755 stages/T3/entrypoint.sh /entrypoint.sh
ENV GO1_POLICY_DIR=/opt/rh/T3/weights
USER 10001:10001
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ping"]
