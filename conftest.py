# Enable the fixture
from mypython.tests.test_mypython import check_output; check_output

def pytest_cmdline_preparse(config, args):
    args[:] = ["--no-success-flaky-report", "--no-flaky-report"] + args
