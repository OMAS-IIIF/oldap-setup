# Dedicated offline operator, never an application service or automatic scheduler.
FROM docker:29-cli@sha256:eccaacfeed644c7de222ff047483568cb988dde95476fbaaf10ea2d04921bb66 AS dockercli
FROM lrosenth/oldap-api:v0.2.23@sha256:658c2f4e994a347b33115fca556d390b7d8feec038dbe520923935ab9b708f5f
USER root
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
HEALTHCHECK NONE
ENTRYPOINT ["python", "-m", "oldaplib.src.writer_recovery_operator"]
CMD ["--help"]
