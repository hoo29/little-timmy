FROM python:3.12-alpine

LABEL com.github.actions.name="little-timmy-action" \
    com.github.actions.description="Little Timmy will try their best to find those unused Ansible variables." \
    com.github.actions.icon="delete" \
    com.github.actions.color="blue" \
    maintainer="@hoo29" \
    org.opencontainers.image.url="https://github.com/hoo29/little-timmy" \
    org.opencontainers.image.source="https://github.com/hoo29/little-timmy" \
    org.opencontainers.image.documentation="https://github.com/hoo29/little-timmy" \
    org.opencontainers.image.vendor="@hoo29" \
    org.opencontainers.image.description="GHA for Little Timmy, an unused Ansible variable finder."

RUN pip3 install little-timmy==3.5.0

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
