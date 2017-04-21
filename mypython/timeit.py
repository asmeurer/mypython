from io import BytesIO

from IPython.core.magics.execution import _format_time
from iterm2_tools.images import display_image_bytes

def autorange(timer, callback=None):
    """Return the number of loops so that total time >= 10.

    Calls the timeit method with *number* set to successive powers of
    two (1, 2, 4, 8, ...) up to a maximum of 2**30, until
    the time taken is at least 10 seconds, or the maximum is reached.
    Returns ``(number, time_taken)``.

    If *callback* is given and is not None, it will be called after
    each trial with two arguments: ``callback(number, time_taken)``.
    """
    total_number = 0
    times = []
    for i in range(31):
        number = 2**i
        times += timer.repeat(number, 1)
        time_taken = sum(times)
        if callback:
            callback(number, time_taken)
        total_number += number
        if time_taken >= 10:
            break

    return times

TIME_REPORT_TEMPLATE = """
{number} loop{s}, {avg} average
Minimum time: {minimum}
Maximum time: {maximum}
{hist}
""".strip()

def time_format(times):
    number = len(times)
    time_taken = sum(times)
    avg = _format_time(time_taken/number)
    s = 's' if number > 1 else ''
    minimum = _format_time(min(times))
    maximum = _format_time(max(times))
    hist = histogram(times)
    return TIME_REPORT_TEMPLATE.format(number=number, avg=avg, s=s,
        minimum=minimum, maximum=maximum, hist=hist)

def histogram(times):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return 'Could not import matplotlib'

    try:
        plt.interactive(False)
        plt.figure(figsize=(2, 1.5), dpi=300)
        plt.hist(times)
        b = BytesIO()
        plt.xlabel("Time", fontsize=6)
        plt.ylabel("Runs", fontsize=6)
        locs, labels = plt.xticks()
        plt.xticks(locs, [_format_time(i) for i in locs], fontsize=6)
        plt.yticks(fontsize=6)
        # fig = plt.gcf()
        # fig.set_size_inches(2, 1.5)
        plt.savefig(b, dpi=300, bbox_inches='tight')
        return display_image_bytes(b.getvalue())
    finally:
        plt.close()
        plt.interactive(True)
