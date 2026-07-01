"""
Python API client for GOV.UK Emergency Alerts
"""

from setuptools import find_packages, setup

setup(
    name="emergency-alerts-utils",
    # We don't use Python versions here, utils is grabbed via Git SHAs into a
    # parent Docker image:
    version="1.0.0",
    url="https://github.com/alphagov/emergency-alerts-utils",
    license="MIT",
    author="Government Digital Service",
    description="Shared python code for GOV.UK Emergency Alerts",
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "cachetools>=5.2.0",
        "requests>=2.25.0",
        "python-json-logger>=3.2.0",
        "Flask>=3.0.2",
        "Werkzeug>=3.1.3",
        "ordered-set>=4.1.0",
        "Jinja2>=2.11.3",
        "pyyaml>=6.0.1",
        "phonenumbers>=8.13.20",
        "pyproj>=3.4.1,<=3.7.2",
        "pytz>=2020.4",
        "smartypants>=2.0.1",
        "itsdangerous>=1.1.0",
        "geojson>=2.5.0",
        "Shapely>=2.1.1",
        "setuptools>=78.1.0",
        "boto3>=1.38.10",
        "lxml>=5.4.0",
        "signxml>=4.0.3",
        "dramatiq>=1.18.0",
        # README suggests breaking changes before v1.0.0 so we should pin:
        "dramatiq_sqs==0.3.1",
        "flask-dramatiq>=0.6.0",
        "periodiq>=0.13.0",
    ],
)
