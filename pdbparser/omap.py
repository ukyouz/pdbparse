#!/usr/bin/env python

from bisect import bisect

from construct import GreedyRange
from construct import Int32ul
from construct import Struct

OMAP_ENTRY = "OmapFromSrc" / Struct(
    "From" / Int32ul,
    "To" / Int32ul,
)

OMAP_ENTRIES = GreedyRange(OMAP_ENTRY)


class Omap(object):

    def __init__(self, omapstream):
        self.omap = OMAP_ENTRIES.parse(omapstream)

        self._froms = None

    def remap(self, address):
        if not self._froms:
            self._froms = [o.From for o in self.omap]

        pos = bisect(self._froms, address)
        if self._froms[pos] != address:
            pos = pos - 1

        if self.omap[pos].To == 0:
            return self.omap[pos].To
        else:
            return self.omap[pos].To + (address - self.omap[pos].From)
