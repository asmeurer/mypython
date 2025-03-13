# Enable the fixture
from mypython.tests.test_mypython import check_output; check_output

def pytest_load_initial_conftests(args):
    args[:] = ["--no-success-flaky-report", "--no-flaky-report"] + args

def pytest_report_header(config):
    import prompt_toolkit
    return f"project deps: prompt_toolkit-{prompt_toolkit.__version__}"
