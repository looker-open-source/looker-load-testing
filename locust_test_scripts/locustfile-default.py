import os
from realbrowserlocusts import HeadlessChromeLocust
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from locust import HttpUser, task, between


SITE = "https://backcountry.looker.com"
DASH_ID = "/2367"  # Change this!


class LocustUserBehavior(HttpUser):

    def on_start(self):
        self.login()

    def on_stop(self):
        self.logout()

    def login(self):
        self.client.get(SITE + "/login")

        user_entry = "ayan.das@backcountry.com" #os.getenv("USERNAME")
        pass_entry = "Backcountry321@" #os.getenv("PASS")
        username = self.client.find_element_by_id("login-email")
        pw = self.client.find_element_by_id("login-password")
        box = self.client.find_element_by_class_name("checkbox")
        username.clear()
        username.send_keys(user_entry.strip())
        pw.clear()
        pw.send_keys(pass_entry.strip())
        box.click()
        self.client.find_element_by_id("login-submit").click()

    def logout(self):
        print("stopping session")
        self.client.close()

    def open_dashboard(self):
        script = """
        window.awaitPerformanceObservation("rendered").then(function() {
            var dash_render = document.createElement("div");
            dash_render.id = "dash_listener";
            document.body.appendChild(dash_render);
        });"""

        try:
            self.client.get(f"{SITE}/embed/dashboards/{str(DASH_ID)}")
            self.client.execute_script(script)
            self.client.wait.until(
                EC.presence_of_element_located(
                    (By.ID, "dash_listener")
                )
            )
        except TimeoutException:
            print("hit timeout")

    @task(1)
    def simple_dashboard_loading(self):
        self.client.timed_event_for_locust(
            "Load", "dashboard-update",
            self.open_dashboard
        )


class LocustUser(HeadlessChromeLocust):

    host = "dashboard load test"
    timeout = 30  # in seconds in waitUntil thingies
    wait_time = between(2, 5)
    screen_width = 1200
    screen_height = 600
    task_set = LocustUserBehavior