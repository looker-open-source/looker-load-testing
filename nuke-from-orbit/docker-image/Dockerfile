# Start with a base Python 3.7 image that has chromedriver installed
FROM joyzoursky/python-chromedriver:3.7

# Add the external tasks directory into /tasks
ADD locust-tasks /locust-tasks
ADD realbrowserlocusts /realbrowserlocusts

# Install the modified realbrowserlocusts package
RUN pip install realbrowserlocusts/.

# Expose the required Locust ports
EXPOSE 5557 5558 8089

# Set script to be executable
RUN chmod 755 /locust-tasks/run.sh

# Start Locust using LOCUS_OPTS environment variable
ENTRYPOINT ["/locust-tasks/run.sh"]
