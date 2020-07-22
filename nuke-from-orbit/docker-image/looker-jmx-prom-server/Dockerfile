FROM openjdk:11-jre-slim

WORKDIR /jmx_prometheus_exporter
ADD . /jmx_prometheus_exporter

EXPOSE 9505

ENTRYPOINT ["java", "-jar", "jmx_prometheus_httpserver.jar", "9505"]
CMD ["/etc/config/looker_jmx.yml"]
