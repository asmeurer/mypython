# autorange code based on Python's builtin timeit module

# Changes:

# - Changed the default in autorange to 10 seconds
# - Changed the time intervals to use powers of 2

# 1. This LICENSE AGREEMENT is between the Python Software Foundation ("PSF"), and
#    the Individual or Organization ("Licensee") accessing and otherwise using Python
#    3.6.0 software in source or binary form and its associated documentation.
#
# 2. Subject to the terms and conditions of this License Agreement, PSF hereby
#    grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce,
#    analyze, test, perform and/or display publicly, prepare derivative works,
#    distribute, and otherwise use Python 3.6.0 alone or in any derivative
#    version, provided, however, that PSF's License Agreement and PSF's notice of
#    copyright, i.e., "Copyright © 2001-2017 Python Software Foundation; All Rights
#    Reserved" are retained in Python 3.6.0 alone or in any derivative version
#    prepared by Licensee.
#
# 3. In the event Licensee prepares a derivative work that is based on or
#    incorporates Python 3.6.0 or any part thereof, and wants to make the
#    derivative work available to others as provided herein, then Licensee hereby
#    agrees to include in any such work a brief summary of the changes made to Python
#    3.6.0.
#
# 4. PSF is making Python 3.6.0 available to Licensee on an "AS IS" basis.
#    PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED.  BY WAY OF
#    EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND DISCLAIMS ANY REPRESENTATION OR
#    WARRANTY OF MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE
#    USE OF PYTHON 3.6.0 WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.
#
# 5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON 3.6.0
#    FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF
#    MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON 3.6.0, OR ANY DERIVATIVE
#    THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.
#
# 6. This License Agreement will automatically terminate upon a material breach of
#    its terms and conditions.
#
# 7. Nothing in this License Agreement shall be deemed to create any relationship
#    of agency, partnership, or joint venture between PSF and Licensee.  This License
#    Agreement does not grant permission to use PSF trademarks or trade name in a
#    trademark sense to endorse or promote products or services of Licensee, or any
#    third party.
#
# 8. By copying, installing or otherwise using Python 3.6.0, Licensee agrees
#    to be bound by the terms and conditions of this License Agreement.


from timeit import Timer

class MyTimer(Timer):
    """
    Timer subclass with autorange

    Timer only has autorange in Python 3.6. Also, its defaults (0.2 seconds)
    aren't great.
    """

    def autorange(self, callback=None):
         """Return the number of loops so that total time >= 10.

         Calls the timeit method with *number* set to successive powers of
         two (1, 2, 4, 8, ...) up to a maximum of 2**30, until
         the time taken is at least 10 seconds, or the maximum is reached.
         Returns ``(number, time_taken)``.

         If *callback* is given and is not None, it will be called after
         each trial with two arguments: ``callback(number, time_taken)``.
         """
         for i in range(31):
             number = 2**i
             time_taken = self.timeit(number)
             if callback:
                 callback(number, time_taken)
             if time_taken >= 10:
                 break
         return (number, time_taken)
