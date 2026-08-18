# Taken from IPython.terminal.pt_inputhooks.osx

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

import sys
if sys.platform == 'darwin':
    """Inputhook for OS X

    Calls NSApp / CoreFoundation APIs via ctypes.
    """

    # obj-c boilerplate from appnope, used under BSD 2-clause

    import ctypes
    import ctypes.util

    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))

    void_p = ctypes.c_void_p

    objc.objc_getClass.restype = void_p
    objc.sel_registerName.restype = void_p
    objc.objc_msgSend.restype = void_p
    # objc_msgSend is a variadic C function, so its argtypes must be set to
    # match each call's actual arguments right before the call. This matters
    # on arm64 (Apple Silicon), where variadic and fixed arguments use
    # different registers.
    objc.objc_msgSend.argtypes = [void_p, void_p]

    msg = objc.objc_msgSend

    def _utf8(s):
        """ensure utf8 bytes"""
        if not isinstance(s, bytes):
            s = s.encode('utf8')
        return s

    def n(name):
        """create a selector name (for ObjC methods)"""
        return objc.sel_registerName(_utf8(name))

    def C(classname):
        """get an ObjC Class by name"""
        return objc.objc_getClass(_utf8(classname))

    # end obj-c boilerplate from appnope

    # CoreFoundation C-API calls we will use:
    CoreFoundation = ctypes.cdll.LoadLibrary(ctypes.util.find_library('CoreFoundation'))

    CFFileDescriptorCreate = CoreFoundation.CFFileDescriptorCreate
    CFFileDescriptorCreate.restype = void_p
    CFFileDescriptorCreate.argtypes = [void_p, ctypes.c_int, ctypes.c_bool, void_p, void_p]

    CFFileDescriptorGetNativeDescriptor = CoreFoundation.CFFileDescriptorGetNativeDescriptor
    CFFileDescriptorGetNativeDescriptor.restype = ctypes.c_int
    CFFileDescriptorGetNativeDescriptor.argtypes = [void_p]

    CFFileDescriptorEnableCallBacks = CoreFoundation.CFFileDescriptorEnableCallBacks
    CFFileDescriptorEnableCallBacks.restype = None
    CFFileDescriptorEnableCallBacks.argtypes = [void_p, ctypes.c_ulong]

    CFFileDescriptorCreateRunLoopSource = CoreFoundation.CFFileDescriptorCreateRunLoopSource
    CFFileDescriptorCreateRunLoopSource.restype = void_p
    CFFileDescriptorCreateRunLoopSource.argtypes = [void_p, void_p, void_p]

    CFRunLoopGetCurrent = CoreFoundation.CFRunLoopGetCurrent
    CFRunLoopGetCurrent.restype = void_p

    CFRunLoopAddSource = CoreFoundation.CFRunLoopAddSource
    CFRunLoopAddSource.restype = None
    CFRunLoopAddSource.argtypes = [void_p, void_p, void_p]

    CFRelease = CoreFoundation.CFRelease
    CFRelease.restype = None
    CFRelease.argtypes = [void_p]

    CFFileDescriptorInvalidate = CoreFoundation.CFFileDescriptorInvalidate
    CFFileDescriptorInvalidate.restype = None
    CFFileDescriptorInvalidate.argtypes = [void_p]

    # From CFFileDescriptor.h
    kCFFileDescriptorReadCallBack = 1
    kCFRunLoopCommonModes = void_p.in_dll(CoreFoundation, 'kCFRunLoopCommonModes')


    def _NSApp():
        """Return the global NSApplication instance (NSApp)"""
        objc.objc_msgSend.argtypes = [void_p, void_p]
        return msg(C('NSApplication'), n('sharedApplication'))


    def _wake(NSApp):
        """Wake the Application"""
        objc.objc_msgSend.argtypes = [
            void_p,
            void_p,
            void_p,
            void_p,
            void_p,
            void_p,
            void_p,
            void_p,
            void_p,
            void_p,
            void_p,
        ]
        event = msg(
            C('NSEvent'),
            n('otherEventWithType:location:modifierFlags:'
              'timestamp:windowNumber:context:subtype:data1:data2:'),
            15, # Type
            0, # location
            0, # flags
            0, # timestamp
            0, # window
            None, # context
            0, # subtype
            0, # data1
            0, # data2
        )
        objc.objc_msgSend.argtypes = [void_p, void_p, void_p, void_p]
        msg(NSApp, n('postEvent:atStart:'), void_p(event), True)


    # Whether _input_callback has fired for the current inputhook call. The
    # callback runs on the main thread inside NSApp.run(), so a plain bool is
    # safe.
    _triggered = False

    def _input_callback(fdref, flags, info):
        """Callback to fire when there's input to be read"""
        global _triggered
        _triggered = True
        CFFileDescriptorInvalidate(fdref)
        CFRelease(fdref)
        NSApp = _NSApp()
        objc.objc_msgSend.argtypes = [void_p, void_p, void_p]
        msg(NSApp, n('stop:'), NSApp)
        _wake(NSApp)

    _c_callback_func_type = ctypes.CFUNCTYPE(None, void_p, void_p, void_p)
    _c_input_callback = _c_callback_func_type(_input_callback)


    def _stop_on_read(fd):
        """Register callback to stop eventloop when there's data on fd"""
        fdref = CFFileDescriptorCreate(None, fd, False, _c_input_callback, None)
        CFFileDescriptorEnableCallBacks(fdref, kCFFileDescriptorReadCallBack)
        source = CFFileDescriptorCreateRunLoopSource(None, fdref, 0)
        loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(loop, source, kCFRunLoopCommonModes)
        CFRelease(source)


    # Whether any window has ever existed. Once NSApp has run with a window,
    # the process is an activated Cocoa app and its event loop must be pumped
    # at every prompt from then on, even after all windows are closed.
    # Otherwise, when the last matplotlib window is closed (which makes
    # matplotlib call [NSApp stop:]), the app would be left frontmost but
    # unresponsive: beachballing and blocking clicks back to the terminal.
    # IPython runs the loop unconditionally for this reason (see
    # https://github.com/ipython/ipython/issues/10137), but it only installs
    # the inputhook after an explicit %gui/%matplotlib. mypython installs it
    # for every session, so skip the loop entirely until a window first
    # appears to avoid activating NSApp in sessions that never use a GUI.
    _activated = False

    def inputhook(context):
        """Inputhook for Cocoa (NSApp)"""
        global _activated, _triggered
        NSApp = _NSApp()
        if not _activated:
            # Returning early is safe: prompt_toolkit's InputHookSelector
            # does a blocking select() on the fd after the hook returns.
            objc.objc_msgSend.argtypes = [void_p, void_p]
            window_count = msg(
                msg(NSApp, n('windows')),
                n('count')
            )
            if not window_count:
                return
            _activated = True
        # Per prompt_toolkit's inputhook contract, this hook must not return
        # until input is ready. NSApp.run() can return early without input:
        # closing the last matplotlib window makes matplotlib call
        # [NSApp stop:]. If we returned then, prompt_toolkit would block in
        # select() without the event loop being pumped until the next
        # keypress, leaving an activated but unresponsive (beachballing)
        # Cocoa app. So re-enter run() until our fd callback has fired. This
        # deliberately diverges from modern IPython, which returns early in
        # this case (it removed the equivalent CFRunLoopRun() fallback for
        # ipython#9734 because a bare CFRunLoopRun can't be stopped by
        # [NSApp stop:] and hung; re-running NSApp.run() doesn't have that
        # defect). Exiting via the callback also means the fdref registered
        # by _stop_on_read is normally consumed rather than leaked.
        _triggered = False
        _stop_on_read(context.fileno())
        while not _triggered and not context.input_is_ready():
            objc.objc_msgSend.argtypes = [void_p, void_p]
            msg(NSApp, n('run'))
