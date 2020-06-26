## Docker Assets

This directory contains the Dockerfile for the modified LocustIO version we use in Kubernetes. Specify your own tests by
modifying `locust-tasks/tasks.py` and alter startup options by modifying `locust-tasks/run.sh`.


## docker-compose Assets

This directory also contains assets used to test the containerized load testing tool. These are suitable for use with docker-compose. An i
example docker-compose.yaml is included below:

```
version: '3'
services:
  master:
    build: .
    ports:
      - "8089:8089"
    environment:
      - TARGET_HOST=dashboard
      - LOCUST_MODE=master
      - LOCUST_STEP=false
      - USERNAME=<your looker username>
      - PASS=<your looker password>
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8089/stats/requests"]
      interval: 30s
      timeout: 10s
      retries: 5
  worker:
    build: .
    environment:
      - TARGET_HOST=dashboard
      - LOCUST_MODE=worker
      - LOCUST_STEP=false
      - LOCUST_MASTER_HOST=master
      - USERNAME=<your looker username>
      - PASS=<your looker password>
  monitor:
    image: containersol/locust_exporter
    ports:
      - "9646:9646"
    environment:
      - LOCUST_EXPORTER_URI=http://master:8089
    depends_on:
      - master
      - worker
  prom:
    image: "prom/prometheus"
    ports:
      - "9090:9090"
    volumes: 
      - ${PWD}/prom/prometheus.yml:/etc/prometheus/prometheus.yml:z
    command: --config.file=/etc/prometheus/prometheus.yml
  grafana:
    image: "grafana/grafana"
    ports:
      - "3000:3000"
```

Once you've modified it appropriately, you can fire it up via a `docker-compose up -d`.
