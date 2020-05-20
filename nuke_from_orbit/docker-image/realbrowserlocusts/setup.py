from setuptools import setup

NAME = "realbrowserlocusts"
VERSION = "0.4.1"
REQUIRES = ["locust", "selenium"]

setup(
    name=NAME,
    packages=["realbrowserlocusts"],
    version=VERSION,
    description="Minimal set of real browser locusts to be used in conjuntion with locust.io",
    install_requires=REQUIRES,
    author="Nick Bocuart",
    author_email="nboucart@gmail.com",
    url="https://github.com/nickboucart/realbrowserlocusts",
    download_url="https://github.com/nickboucart/realbrowserlocusts/tarball/0.3",
    keywords=["testing", "locust"],
    classifiers=[],
)
