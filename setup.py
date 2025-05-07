"""
Python API client for GOV.UK Notify
"""

import ast
import re

from setuptools import find_packages, setup

_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("emergency_alerts_utils/version.py", "rb") as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1)))

setup(
    name="emergency-alerts-utils",
    version=version,
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
        "ordered-set>=4.1.0",
        "Jinja2>=2.11.3",
        "pyyaml>=6.0.1",
        "phonenumbers>=8.13.20",
        "pyproj>=3.4.1,<=3.6.1",
        "pytz>=2020.4",
        "smartypants>=2.0.1",
        "itsdangerous>=1.1.0",
        "geojson>=2.5.0",
        "Shapely>=1.8.0",
        "setuptools>=78.1.0",
        "boto3>=1.19.4",
        "lxml>=5.4.0",
        "signxml>=4.0.3",  # "signxml>=3.2.2",
        "pyOpenSSL>=25.0.0",  # "pyOpenSSL<=24.2.1",  # v24.3 removes OpenSSL.crypto.verify, but signxml needs it
    ],
)
