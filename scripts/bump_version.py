#!/usr/bin/env python

import argparse
import hashlib
import subprocess
from pathlib import Path

from emergency_alerts_utils.version import __version__
from emergency_alerts_utils.version_tools import color

version_parts = ("major", "minor", "patch")

parser = argparse.ArgumentParser()
parser.add_argument("version_part", choices=version_parts)
version_part = parser.parse_args().version_part

current_major, current_minor, current_patch = map(int, __version__.split("."))

new_major, new_minor, new_patch = {
    "major": (current_major + 1, 0, 0),
    "minor": (current_major, current_minor + 1, 0),
    "patch": (current_major, current_minor, current_patch + 1),
}[version_part]

package_contents = subprocess.run(("tar", "cf", "-", "emergency_alerts_utils"), capture_output=True).stdout

# Putting a hash of the package contents on the same line as the version
# number will force a merge conflict if two people try to release
# different code under the same version
package_contents_hash = hashlib.md5(package_contents).hexdigest()

output = f"""
# This file is autogenerated.
#
# To update or resolve merge conflicts run one of:
# - `make version-major` for breaking changes
# - `make version-minor` for new features
# - `make version-patch` for bug fixes

__version__ = "{new_major}.{new_minor}.{new_patch}"  # {package_contents_hash}
""".lstrip()

with Path("emergency_alerts_utils/version.py").open("w") as version_file:
    version_file.write(output)

print("")
print(
    f"{color.BOLD}{color.GREEN}"
    f"Changed version from {__version__} to {new_major}.{new_minor}.{new_patch}"
    f"{color.END} ✅"
)
print("")
print("   Update requirements files in other apps with:")
print("")
print(
    f"   "
    f"emergency-alerts-utils @ git+https://github.com/alphagov/emergency-alerts-utils.git"
    f"@{new_major}.{new_minor}.{new_patch}"
)
print("")

if version_part == "minor":
    print(f"{color.YELLOW}{color.BOLD}Consider updating CHANGELOG.md, for example:{color.END}")
    print(
        f"""
    ## {new_major}.{new_minor}.{new_patch}

    * Details of change 1
    * Details of change 2
    """
    )

if version_part == "major":
    print(f"{color.YELLOW}{color.BOLD}Make sure to update CHANGELOG.md, for example:{color.END}")
    print(
        f"""
    ## {new_major}.{new_minor}.{new_patch}

    * Details of breaking change
    """
    )
