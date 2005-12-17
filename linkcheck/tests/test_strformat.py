# -*- coding: iso-8859-1 -*-
# Copyright (C) 2004-2005  Bastian Kleineidam
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
Test string formatting operations.
"""

import unittest
import os
import tests
import linkcheck.strformat


class TestStrFormat (tests.StandardTest):
    """
    Test string formatting routines.
    """

    def test_unquote (self):
        """
        Test quote stripping.
        """
        u = linkcheck.strformat.unquote
        self.assertEquals(u(""), "")
        self.assertEquals(u(None), None)
        self.assertEquals(u("'"), "'")
        self.assertEquals(u("\""), "\"")
        self.assertEquals(u("\"\""), "")
        self.assertEquals(u("''"), "")
        self.assertEquals(u("'a'"), "a")
        self.assertEquals(u("'a\"'"), "a\"")
        self.assertEquals(u("'\"a'"), "\"a")
        self.assertEquals(u('"a\'"'), 'a\'')
        self.assertEquals(u('"\'a"'), '\'a')
        # even mis-matching quotes should be removed...
        self.assertEquals(u("'a\""), "a")
        self.assertEquals(u("\"a'"), "a")
        # ...but not when matching is True
        self.assertEquals(u("'a\"", matching=True), "'a\"")
        self.assertEquals(u("\"a'", matching=True), "\"a'")

    def test_wrap (self):
        """
        Test line wrapping.
        """
        s = "11%(sep)s22%(sep)s33%(sep)s44%(sep)s55" % {'sep': os.linesep}
        # testing width <= 0
        self.assertEquals(linkcheck.strformat.wrap(s, -1), s)
        self.assertEquals(linkcheck.strformat.wrap(s, 0), s)
        l = len(os.linesep)
        gap = " "*l
        s2 = "11%(gap)s22%(sep)s33%(gap)s44%(sep)s55" % \
             {'sep': os.linesep, 'gap': gap}
        # splitting lines
        self.assertEquals(linkcheck.strformat.wrap(s2, 2), s)
        # combining lines
        self.assertEquals(linkcheck.strformat.wrap(s, 4+l), s2)

    def test_remove_markup (self):
        """
        Test markup removing.
        """
        self.assertEquals(linkcheck.strformat.remove_markup("<a>"), "")
        self.assertEquals(linkcheck.strformat.remove_markup("<>"), "")
        self.assertEquals(linkcheck.strformat.remove_markup("<<>"), "")
        self.assertEquals(linkcheck.strformat.remove_markup("a < b"), "a < b")

    def test_strsize (self):
        """
        Test byte size strings.
        """
        self.assertRaises(ValueError, linkcheck.strformat.strsize, -1)
        self.assertEquals(linkcheck.strformat.strsize(0), "0 Bytes")
        self.assertEquals(linkcheck.strformat.strsize(1), "1 Byte")
        self.assertEquals(linkcheck.strformat.strsize(2), "2 Bytes")
        self.assertEquals(linkcheck.strformat.strsize(1023), "1023 Bytes")
        self.assertEquals(linkcheck.strformat.strsize(1024), "1.00 kB")

    def test_is_ascii (self):
        self.assert_(linkcheck.strformat.is_ascii("abcd./"))
        self.assert_(not linkcheck.strformat.is_ascii("�"))
        self.assert_(not linkcheck.strformat.is_ascii(u"�"))

    def test_indent (self):
        s = "bla"
        self.assertEquals(linkcheck.strformat.indent(s, ""), s)
        self.assertEquals(linkcheck.strformat.indent(s, " "), " "+s)

    def test_stripall (self):
        self.assertEquals(linkcheck.strformat.stripall("a\tb"), "ab")
        self.assertEquals(linkcheck.strformat.stripall(" a\t b"), "ab")
        self.assertEquals(linkcheck.strformat.stripall(" \r\na\t \nb\r"), "ab")

    def test_limit (self):
        self.assertEquals(linkcheck.strformat.limit("", 0), "")
        self.assertEquals(linkcheck.strformat.limit("a", 0), "")
        self.assertEquals(linkcheck.strformat.limit("1", 1), "1")
        self.assertEquals(linkcheck.strformat.limit("11", 1), "1...")


def test_suite ():
    """
    Build and return a TestSuite.
    """
    return unittest.makeSuite(TestStrFormat)


if __name__ == '__main__':
    unittest.main()
