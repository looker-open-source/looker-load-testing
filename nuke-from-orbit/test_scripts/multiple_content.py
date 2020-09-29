import os
from realbrowserlocusts import HeadlessChromeLocust
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from locust import TaskSet, task, between

# Change this
SITE = "https://your.looker.com"


class LocustUserBehavior(TaskSet):

    def on_start(self):
        self.login()

    def on_stop(self):
        self.logout()

    def login(self):
        self.client.get(SITE + "/login/email")
        WebDriverWait(self.client, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@name='remember']"))
        )
        box = self.client.find_element_by_xpath("//input[@name='remember']")
        box.click()
        # These environment variables are provided by Kubernetes secrets
        user_entry = os.getenv("USERNAME")
        pass_entry = os.getenv("PASS")
        username = self.client.find_element_by_id("login-email")
        pw = self.client.find_element_by_id("login-password")
        username.clear()
        username.send_keys(user_entry.strip())
        pw.clear()
        pw.send_keys(pass_entry.strip())
        self.client.find_element_by_id("login-submit").click()

    def logout(self):
        print("stopping session")

    def open(self, content_id, stem='dashboards'):
        """
        The script below is the appropriate way to detect when content has
        finished rendering in Looker. The injected Javascript makes Looker
        create a DOM element when finished, which Locust uses Selenium to
        detect and wait for.
        """
        script = """
        window.awaitPerformanceObservation("rendered").then(function() {
            var render = document.createElement("div");
            render.id = "finished";
            document.body.appendChild(render);
        });"""

        try:
            self.client.get(f"{SITE}/embed/{stem}/{content_id}")
            self.client.execute_script(script)
            self.client.wait.until(
                EC.presence_of_element_located(
                    (By.ID, "finished")
                )
            )
        except TimeoutException:
            print("hit timeout")

    """
    Each of these methods defines a load testing task to run randomly.
    The decorator @task(n) indicates the relative weight of the task
    versus all other tasks. If you decorate a method with @task(5)
    it will be five times more likely to run than a method decorated
    with @task(1).

    The name of the methods don't matter, but they do need to be unique.
    This is why there's a sequential ID appended to each method name.

    The tasks below result in one of about 27 different pieces of content
    being randomly loaded each time a Locust user executes this TaskSet.

    """

    # Operations
    @task(1)
    def dashboard_1(self):
        id = "683"
        self.client.timed_event_for_locust(
            # The first and second parameters are
            # used to tag and identify tasks
            "Operations", f"dashboard {id}",
            self.open, content_id=id
        )

    @task(1)
    def dashboard_2(self):
        id = "729"
        self.client.timed_event_for_locust(
            "Operations", f"dashboard {id}",
            # stem can be used to override the default
            # 'dashboards' route in the self.open method
            self.open, content_id=id, stem='dashboards-next'
        )

    @task(1)
    def dashboard_3(self):
        id = "927"
        self.client.timed_event_for_locust(
            "Operations", f"dashboard {id}",
            self.open, content_id=id, stem='dashboards-next'
        )

    @task(1)
    def dashboard_4(self):
        id = "623"
        self.client.timed_event_for_locust(
            "Operations", f"dashboard {id}",
            self.open, content_id=id
        )

    @task(1)
    def dashboard_5(self):
        id = "797"
        self.client.timed_event_for_locust(
            "Operations", f"dashboard {id}",
            self.open, content_id=id, stem='dashboards-next'
        )

    @task(1)
    def dashboard_6(self):
        id = "858"
        self.client.timed_event_for_locust(
            "Operations", f"dashboard {id}",
            self.open, content_id=id, stem='dashboards-next'
        )

    @task(1)
    def dashboard_7(self):
        id = "944"
        self.client.timed_event_for_locust(
            "Operations", f"dashboard {id}",
            self.open, content_id=id
        )

    @task(1)
    def dashboard_8(self):
        id = "156"
        self.client.timed_event_for_locust(
            "Operations", f"dashboard {id}",
            self.open, content_id=id
        )

    @task(1)
    def dashboard_9(self):
        id = "943"
        self.client.timed_event_for_locust(
            "Operations", f"dashboard {id}",
            self.open, content_id=id, stem='dashboards-next'
        )

    @task(1)
    def dashboard_10(self):
        id = "1014"
        self.client.timed_event_for_locust(
            "Operations", f"dashboard {id}",
            self.open, content_id=id, stem='dashboards-next'
        )

    @task(1)
    def dashboard_11(self):
        id = "702"
        self.client.timed_event_for_locust(
            "Operations", f"dashboard {id}",
            self.open, content_id=id
        )

    @task(1)
    def dashboard_12(self):
        id = "517"
        self.client.timed_event_for_locust(
            "Operations", f"dashboard {id}",
            self.open, content_id=id
        )

    @task(1)
    def dashboard_13(self):
        id = "693"
        self.client.timed_event_for_locust(
            "Operations", f"dashboard {id}",
            self.open, content_id=id
        )

    # Finance
    @task(1)
    def dashboard_14(self):
        id = "1180"
        self.client.timed_event_for_locust(
            "Finance", f"dashboard {id}",
            self.open, content_id=id
        )

    @task(1)
    def look_1(self):
        id = "5818"
        self.client.timed_event_for_locust(
            "Finance", f"look {id}",
            self.open, content_id=id, stem='looks'
        )

    @task(1)
    def look_2(self):
        id = "6448"
        self.client.timed_event_for_locust(
            "Finance", f"look {id}",
            self.open, content_id=id, stem='looks'
        )

    @task(1)
    def look_3(self):
        id = "6592"
        self.client.timed_event_for_locust(
            "Finance", f"look {id}",
            self.open, content_id=id, stem='looks'
        )

    @task(1)
    def look_4(self):
        id = "5817"
        self.client.timed_event_for_locust(
            "Finance", f"look {id}",
            self.open, content_id=id, stem='looks'
        )

    @task(1)
    def look_5(self):
        id = "4488"
        self.client.timed_event_for_locust(
            "Finance", f"look {id}",
            self.open, content_id=id, stem='looks'
        )

    @task(1)
    def look_6(self):
        id = "2857"
        self.client.timed_event_for_locust(
            "Finance", f"look {id}",
            self.open, content_id=id, stem='looks'
        )

    # Marketing
    @task(1)
    def dashboard_15(self):
        id = "1114"
        self.client.timed_event_for_locust(
            "Marketing", f"dashboard {id}",
            self.open, content_id=id
        )

    @task(1)
    def dashboard_16(self):
        id = "1115"
        self.client.timed_event_for_locust(
            "Marketing", f"dashboard {id}",
            self.open, content_id=id
        )

    @task(1)
    def dashboard_17(self):
        id = "1126"
        self.client.timed_event_for_locust(
            "Marketing", f"dashboard {id}",
            self.open, content_id=id
        )

    @task(1)
    def dashboard_18(self):
        id = "1119"
        self.client.timed_event_for_locust(
            "Marketing", f"dashboard {id}",
            self.open, content_id=id
        )

    @task(1)
    def dashboard_19(self):
        id = "975"
        self.client.timed_event_for_locust(
            "Marketing", f"dashboard {id}",
            self.open, content_id=id
        )

    # HR
    @task(1)
    def dashboard_20(self):
        id = "1087"
        self.client.timed_event_for_locust(
            "HR", f"dashboard {id}",
            self.open, content_id=id
        )

    @task(1)
    def dashboard_21(self):
        id = "1176"
        self.client.timed_event_for_locust(
            "HR", f"dashboard {id}",
            self.open, content_id=id
        )


class LocustUser(HeadlessChromeLocust):
    host = "dashboard load test"
    timeout = 30  # in seconds in waitUntil thingies
    wait_time = between(2, 5)
    screen_width = 1200
    screen_height = 600
    task_set = LocustUserBehavior

