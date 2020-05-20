import os
from realbrowserlocusts import HeadlessChromeLocust
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from locust import TaskSet, task, between


SITE = "https://jcp-dev.lookersandbox.com"


class LocustUserBehavior(TaskSet):

    def on_start(self):
        self.login()

    def on_stop(self):
        self.logout()

    def login(self):
        self.client.get(SITE + "/login")

        user_entry = os.getenv("USERNAME")
        pass_entry = os.getenv("PASS")
        username = self.client.find_element_by_id("login-email")
        pw = self.client.find_element_by_id("login-password")
        username.clear()
        username.send_keys(user_entry)
        pw.clear()
        pw.send_keys(pass_entry)
        self.client.find_element_by_id("login-submit").click()

    def logout(self):
        print("stopping session")

    def open_dashboard(self):
        self.client.get("https://jcp-dev.lookersandbox.com/embed/dashboards/8")
        self.client.wait.until(
            EC.visibility_of_element_located(
                (By.ID, "lk-dashboard-container")
            )
        )

    @task(1)
    def simple_dashboard_loading(self):
        self.client.timed_event_for_locust(
            "Load", "dashboard",
            self.open_dashboard
        )


class LocustUser(HeadlessChromeLocust):

    host = "dashboard load test"
    timeout = 30  # in seconds in waitUntil thingies
    wait_time = between(2, 5)
    screen_width = 1200
    screen_height = 600
    task_set = LocustUserBehavior
