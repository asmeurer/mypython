import sys
import math
from io import BytesIO
import platform

try:
    from iterm2_tools.images import image_bytes
except ImportError:
    if platform.system() == 'Darwin':
        raise
    image_bytes = lambda x: ''

def autorange(timer, callback=None):
    """Return the number of loops so that total time >= 10.

    timer should be a timeit.Timer instance.

    Calls the timeit method with *number* set to successive powers of
    two (1, 2, 4, 8, ...) up to a maximum of 2**21, until
    the time taken is at least 10 seconds, or the maximum is reached.
    Returns ``(number, time_taken)``.

    If *callback* is given and is not None, it will be called after
    each trial with two arguments: ``callback(number, time_taken)``.
    """
    total_number = 0
    times = []
    # The overhead of the timer itself takes about 10 seconds for 2**22 runs
    # (%timeit pass) on a slow machine (Travis CI).
    for i in range(22):
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

def timeit_format(times, expr):
    number = len(times)
    time_taken = sum(times)
    avg = format_time(time_taken/number)
    s = 's' if number > 1 else ''
    minimum = format_time(min(times))
    maximum = format_time(max(times))
    if platform.system() == 'Darwin':
        hist = timeit_histogram(times, expr)
    else:
        hist=''
    return TIME_REPORT_TEMPLATE.format(number=number, avg=avg, s=s,
        minimum=minimum, maximum=maximum, hist=hist)

def timeit_histogram(times, expr):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return 'Could not import matplotlib'

    try:
        import seaborn as sns
    except ImportError:
        return 'Could not import seaborn'

    try:
        plt.interactive(False)
        ax = plt.gca()
        fig2, ax2 = plt.subplots()
        fontsize = 8
        plt.figure(figsize=(4, 3), dpi=300)

        # rug plots are too slow for large number of data points
        extra = dict(rug=True, rug_kws={"lw": .2}) if len(times) < 1024 else {}
        if len(times) == 1:
            # Workaround a bug in seaborn https://github.com/mwaskom/seaborn/issues/1256
            times = times*2
        # Workaround seaborn forcing normalization with kde=True
        # https://github.com/mwaskom/seaborn/issues/479
        sns.distplot(times, kde_kws={'lw': .5}, color='b', **extra)
        sns.distplot(times, ax=ax2, kde=False, norm_hist=False, color='b', **extra)
        ax.yaxis = ax2.yaxis
        b = BytesIO()
        ax.ticklabel_format(style='plain', axis='both', useOffset=False)
        plt.xlabel("Time", fontsize=fontsize)
        plt.ylabel("Runs", fontsize=fontsize)
        if '\n' in expr:
            plt.title("%%timeit\n{expr}".format(expr=expr), fontsize=fontsize, ha='left', loc='left',
            family='monospace')
        else:
            plt.title("%%timeit {expr}".format(expr=expr), fontsize=fontsize, family='monospace')
        x1,x2,y1,y2 = plt.axis()
        plt.xlim([0, x2])
        locs, labels = plt.xticks()
        plt.xticks(locs, [format_time(i) for i in locs], fontsize=fontsize)
        plt.yticks(fontsize=fontsize)
        # fig = plt.gcf()
        # fig.set_size_inches(2, 1.5)
        plt.savefig(b, dpi=300, bbox_inches='tight')
        image = image_bytes(b.getvalue())
        # Newer version of iterm2-tools return bytes
        if isinstance(image, bytes):
            image = image.decode('ascii')
        return image
    finally:
        plt.close()
        plt.interactive(True)

# format_time is modified from IPython.core.magics.execution._format_time

# =============================
#  The IPython licensing terms
# =============================
#
# IPython is licensed under the terms of the Modified BSD License (also known as
# New or Revised or 3-Clause BSD), as follows:
#
# - Copyright (c) 2008-2014, IPython Development Team
# - Copyright (c) 2001-2007, Fernando Perez <fernando.perez@colorado.edu>
# - Copyright (c) 2001, Janko Hauser <jhauser@zscout.de>
# - Copyright (c) 2001, Nathaniel Gray <n8gray@caltech.edu>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice, this
# list of conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.
#
# Neither the name of the IPython Development Team nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


def format_time(timespan, precision=3):
    """Formats the timespan in a human readable form"""

    if timespan >= 60.0:
        # we have more than a minute, format that in a human readable form
        # Idea from http://snipplr.com/view/5713/
        parts = [("d", 60*60*24),("h", 60*60),("min", 60), ("s", 1)]
        time = []
        leftover = timespan
        for suffix, length in parts:
            value = int(leftover / length)
            if value > 0:
                leftover = leftover % length
                time.append(u'%s %s' % (str(value), suffix))
            if leftover < 1:
                break
        return " ".join(time)


    # Unfortunately the unicode 'micro' symbol can cause problems in
    # certain terminals.
    # See bug: https://bugs.launchpad.net/ipython/+bug/348466
    # Try to prevent crashes by being more secure than it needs to
    # E.g. eclipse is able to print a µ, but has no sys.stdout.encoding set.
    units = [u"s", u"ms",u'us',"ns"] # the save value
    if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding:
        try:
            u'\xb5'.encode(sys.stdout.encoding)
            units = [u"s", u"ms",u'\xb5s',"ns"]
        except:
            pass
    scaling = [1, 1e3, 1e6, 1e9]

    if timespan > 0.0:
        order = min(-int(math.floor(math.log10(timespan)) // 3), 3)
    else:
        order = 0
    return u"%.*g %s" % (precision, timespan * scaling[order], units[order])
