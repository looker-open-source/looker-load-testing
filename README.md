Looker Load Testing
===========

Some general tools and techniques to aid in "Real Browser" load testing of Looker instances with LocustIO and
Selenium. An example file suitable for local testing is provided here and a scalable cloud-based solution can be
found in [nuke-from-orbit](/nuke-from-orbit).

This system makes use of [LocustIO](https://locust.io/) to coordinate and report on load testing. The key concept here is each test is
defined in a python script that defines the test itself as well as setup and teardown procedures (e.g. logging in,
logging out, etc.) Think of each script as a manifest for a specific test. The advantage of defining tests in code is
they are extremely flexible, meaning you can encapsulate just about any test scenario you need.

## Local Testing

The Pipfile and locustfile in this directory can be used for local testing. Install the python dependencies using
[Pipenv](https://pipenv.pypa.io/en/latest/) by invoking `pipenv install --ignore-pipfile`

Then, modify `locustfile.py` to match your testing criteria. Some things you will want to change are the `SITE` and
`DASH_ID` global variables and the `timeout` and `wait_time` arguments in the `LocustUser` class.

This local version expects two environment variables to be present:

1. USERNAME - this is the email you use to log into your Looker instance.
2. PASS - this is the password you use to log into your looker instance.

I recommend setting up a .env file that contains these values - pipenv will then automatically load them when you
execute a `pipenv run` or `pipenv shell` command. A sample .env file would look like this:

```
USERNAME=foo@company.com
PASS=abcxyz
```

When your `locustfile.py` and `looker.ini` files are in order, kick off the test by invoking `locust` from the command
line. Then, in a browser, navigate to `localhost:8089` and initiate the test.


## Caveats etc.

LocustIO is designed to work with simple `GET` requests and quite a few hoops need to be jumped through to allow it to
work with real browsers and selenium. We're making use of a package called `realbrowserlocusts` to do most of the heavy
lifting, but we've had to modify it to work in a distributed containerized format. Further improvements will be made
over time.

Additionally, to accurately time how long a Looker dashboard takes to load is not very straightforward. The best method
comes from listening for a Javascript event Looker emits once dashboards are loaded (`dashboard.rendered`) but Selenium
by default can't wait for JS events. We've solved the problem by executing an eventlistener in JS that then appends an
empty div to the DOM.

It all works but rarely the event fires before the JS script runs. In these cases the listener will time out. This will
appear as an outlier in the final load test report.
