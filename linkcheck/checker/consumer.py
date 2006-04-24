# -*- coding: iso-8859-1 -*-
# Copyright (C) 2000-2006 Bastian Kleineidam
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""
Url consumer class.
"""

import time
try:
    import thread
except ImportError:
    import dummy_thread as thread

import linkcheck.threader
import linkcheck.log
import linkcheck.lock
import linkcheck.strformat
import linkcheck.checker.geoip
import linkcheck.decorators
from linkcheck.checker import stderr

# global lock for synchronizing all the checker threads
_lock = thread.allocate_lock()


def print_tocheck (tocheck):
    """
    Print the number of queued URLs.
    """
    msg = _n("%5d URL queued,", "%5d URLs queued,", tocheck) % tocheck
    print >> stderr, msg,


def print_links (links):
    """
    Print the number of checked URLs.
    """
    msg = _n("%4d URL checked,", "%4d URLs checked,", links) % links
    print >> stderr, msg,


def print_active (active):
    """
    Print the number of active threads.
    """
    msg = _n("%2d active thread,", "%2d active threads,", active) % active
    print >> stderr, msg,


def print_duration (duration):
    """
    Print the run time.
    """
    msg = _("runtime %s") % linkcheck.strformat.strduration(duration)
    print >> stderr, msg,


class Consumer (object):
    """
    Consume URLs from the URL queue in a thread-safe manner.
    All public methods are synchronized, with the exception of
    abort() which calls locking methods itself, and check_url()
    which just spawns another checker thread.

    Additionally all public methods of the Cache() object
    are included as synchronized proxy functions via __getattr__().
    The synchronization uses a global variable _lock defined above.
    """

    def __init__ (self, config, cache):
        """
        Initialize consumer data and threads.
        """
        super(Consumer, self).__init__()
        # number of consumed URLs
        self._number = 0
        self._config = config
        self._cache = cache
        self._threader = linkcheck.threader.Threader(num=config['threads'])
        self.start_log_output()

    @linkcheck.decorators.synchronized(_lock)
    def config (self, key):
        """
        Get config value.
        """
        return self._config[key]

    @linkcheck.decorators.synchronized(_lock)
    def config_append (self, key, val):
        """
        Append config value.
        """
        self._config[key].append(val)

    def __getattr__ (self, name):
        """
        Delegate access to the internal cache if possible.
        """
        if hasattr(self._cache, name):
            func = getattr(self._cache, name)
            return linkcheck.decorators.synchronize(_lock, func)
        raise AttributeError(name)

    @linkcheck.decorators.synchronized(_lock)
    def append_url (self, url_data):
        """
        Append url to incoming check list.
        """
        if not self._cache.incoming_add(url_data):
            # can be logged
            self._log_url(url_data)

    def check_url (self, url_data, name):
        """
        Check given URL data, spawning a new thread with given name.
        This eventually calls either Consumer.checked() or
        Consumer.interrupted().
        This method is not thread safe (hence it should only be called
        from a single thread).
        """
        name = linkcheck.strformat.ascii_safe(name)
        self._threader.start_thread(url_data.check, (), name=name)

    @linkcheck.decorators.synchronized(_lock)
    def checked (self, url_data):
        """
        Put checked url in cache and log it.
        """
        # log before putting it in the cache (otherwise we would see
        # a "(cached)" after every url
        self._log_url(url_data)
        if url_data.caching and not url_data.cached:
            self._cache.checked_add(url_data)
        else:
            self._cache.in_progress_remove(url_data)

    @linkcheck.decorators.synchronized(_lock)
    def interrupted (self, url_data):
        """
        Remove url from active list.
        """
        self._cache.in_progress_remove(url_data, ignore_missing=True)

    @linkcheck.decorators.synchronized(_lock)
    def finished (self):
        """
        Return True if checking is finished.
        """
        # avoid deadlock by requesting cache data before locking
        return self._threader.finished() and \
               self._cache.incoming_len() == 0

    @linkcheck.decorators.synchronized(_lock)
    def finish (self):
        """
        Finish consuming URLs.
        """
        self._threader.finish()

    @linkcheck.decorators.synchronized(_lock)
    def no_more_threads (self):
        """
        Return True if no more active threads are running.
        """
        return self._threader.finished()

    def abort (self):
        """
        Abort checking and send end-of-output message to logger.
        """
        # While loop to disable keyboard interrupts and system exits
        # (triggered from internal errors while finishing up) during abort.
        self.num_waited = 0
        while True:
            try:
                self._abort()
                break
            except (KeyboardInterrupt, SystemExit):
                pass

    def _abort (self):
        """
        Abort checking and send end-of-output message to logger.
        Private method not disabling exceptions.
        """
        # wait for threads to finish
        while not self.no_more_threads():
            if self.num_waited > 30:
                linkcheck.log.error(linkcheck.LOG_CHECK,
                                    "Thread wait timeout")
                self.end_log_output()
                return
            num = self.active_threads()
            msg = \
            _n("keyboard interrupt; waiting for %d active thread to finish",
               "keyboard interrupt; waiting for %d active threads to finish",
               num)
            linkcheck.log.warn(linkcheck.LOG_CHECK, msg, num)
            self.finish()
            self.num_waited += 1
            time.sleep(2)
        self.end_log_output()

    @linkcheck.decorators.synchronized(_lock)
    def print_status (self, curtime, start_time):
        """
        Print check status looking at url queues.
        """
        # avoid deadlock by requesting cache data before locking
        print >> stderr, _("Status:"),
        print_active(self._threader.active_threads())
        print_links(self._number)
        print_tocheck(self._cache.incoming_len())
        print_duration(curtime - start_time)
        print >> stderr

    @linkcheck.decorators.synchronized(_lock)
    def start_log_output (self):
        """
        Start output of all configured loggers.
        """
        self._config['logger'].start_output()
        for logger in self._config['fileoutput']:
            logger.start_output()

    @linkcheck.decorators.synchronized(_lock)
    def log_url (self, url_data):
        """
        Log given URL.
        """
        self._log_url(url_data)

    def _log_url (self, url_data):
        """
        Send new url to all configured loggers.
        """
        self._number += 1
        has_warnings = False
        for tag, content in url_data.warnings:
            if tag not in self._config["ignorewarnings"]:
                has_warnings = True
                break
        do_print = self._config["verbose"] or not url_data.valid or \
            (has_warnings and self._config["warnings"])
        self._config['logger'].log_filter_url(url_data, do_print)
        for log in self._config['fileoutput']:
            log.log_filter_url(url_data, do_print)

    @linkcheck.decorators.synchronized(_lock)
    def end_log_output (self):
        """
        End output of all configured loggers.
        """
        self._config['logger'].end_output()
        for logger in self._config['fileoutput']:
            logger.end_output()

    @linkcheck.decorators.synchronized(_lock)
    def active_threads (self):
        """
        Return number of active threads.
        """
        return self._threader.active_threads()

    @linkcheck.decorators.synchronized(_lock)
    def get_country_name (self, host):
        """
        Return country code for host if found, else None.
        """
        gi = self._config["geoip"]
        if gi:
            return linkcheck.checker.geoip.get_country(gi, host)
        return None
