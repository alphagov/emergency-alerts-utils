# emergency-alerts-utils

Shared Python code for GOV.UK Emergency Alerts applications. Standardises how to do logging, rendering message templates, parsing spreadsheets, talking to external services and more.

## Setting up

### Local Development Environment Setup
Ensure that you have first followed all of the steps, that can be found [here](https://gds-ea.atlassian.net/wiki/spaces/EA/pages/221216772/Local+Development+Environment+Setup+-+Updated+instructions).

### Python version
You can find instructions on specifying the correct Python version [here](https://gds-ea.atlassian.net/wiki/spaces/EA/pages/192217089/Setting+up+Local+Development+Environment#Setting-Python-Version).

### Pre-commit

We use [pre-commit](https://pre-commit.com/) to ensure that committed code meets basic standards for formatting, and will make basic fixes for you to save time and aggravation.

Install pre-commit system-wide with, eg `brew install pre-commit`. Then, install the hooks in this repository with `pre-commit install --install-hooks`.

## To test the library

```
# install dependencies, etc.
make bootstrap

# run the tests
make test
```
