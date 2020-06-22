# -*- coding: UTF-8 -*-
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
import json
import requests
import sys
import time


class LocustCollector(object):

    def __init__(self, ep):
        self._ep = ep

    def collect(self):
        # Fetch the JSON
        url = f"http://{self._ep}/stats/requests"
        try:
            response = requests.get(url).content.decode('Utf-8')
        except requests.exceptions.ConnectionError:
            print("Failed to connect to Locust:", url)
            exit(2)

        response = json.loads(response)

        stats_metrics = [
            'avg_content_length',
            'avg_response_time',
            'current_rps',
            'max_response_time',
            'median_response_time',
            'min_response_time',
            'num_failures',
            'num_requests'
        ]

        # locust users
        gmetric = GaugeMetricFamily("locust_user_count", "Swarmed users")
        gmetric.add_metric(["user_count"], value=response["user_count"])
        yield gmetric

        # locust errors
        gmetric = GaugeMetricFamily("locust_errors", "Locust Request Errors")

        for err in response["errors"]:
            gmetric.add_metric(
                [err["name"], err["method"]],
                value=err["occurences"]
            )

        yield gmetric

        # locust workers

        if "slaves" in response:
            gmetric = GaugeMetricFamily("locust_worker_count", "number of locust workers")
            gmetric.add_metric(["worker_count"], value=len(response["slaves"]))
            yield gmetric

        # locust failure ratio
        gmetric = GaugeMetricFamily("locust_failure_ratio", "Locust failure ratio")
        gmetric.add_metric(["failure_ratio"], value=response["fail_ratio"])
        yield gmetric

        # locust state
        gmetric = GaugeMetricFamily("locust_state", "State of the locust swarm")
        gmetric.add_metric([{"state": response["state"]}], value=1)
        yield gmetric

        for mtr in stats_metrics:
            if mtr in ['num_requests', 'num_failures']:
                gmetric = CounterMetricFamily(f"locust_requests_{mtr}", f"Locust requests {mtr}")
            else:
                gmetric = GaugeMetricFamily(f"locust_requests_{mtr}", f"Locust requests {mtr}")
            for stat in response['stats']:
                if 'Total' not in stat['name']:
                    gmetric.add_metric(
                        [{"path": stat["name"], "method": stat["method"]}],
                        value=stat[mtr],
                    )
            yield gmetric


if __name__ == '__main__':
    # Usage: locust_exporter.py <port> <locust_host:port>
    if len(sys.argv) != 3:
        print('Usage: locust_exporter.py <port> <locust_host:port>')
        exit(1)
    else:
        try:
            start_http_server(int(sys.argv[1]))
            REGISTRY.register(LocustCollector(str(sys.argv[2])))
            print("Connecting to locust on: " + sys.argv[2])
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            exit(0)
