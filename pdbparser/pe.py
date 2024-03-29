#!/usr/bin/env python

from construct import GreedyRange
from construct import Int16ul
from construct import Int32ul
from construct import PaddedString
from construct import Struct
from construct import Union

IMAGE_SECTION_HEADER = Struct(
    "Name" / PaddedString(8, encoding = "utf8"),
    "Misc" / Union(
        0,
        "PhysicalAddress" / Int32ul,
        "VirtualSize" / Int32ul,
    ),
    "VirtualAddress" / Int32ul,
    "SizeOfRawData" / Int32ul,
    "PointerToRawData" / Int32ul,
    "PointerToRelocations" / Int32ul,
    "PointerToLinenumbers" / Int32ul,
    "NumberOfRelocations" / Int16ul,
    "NumberOfLinenumbers" / Int16ul,
    "Characteristics" / Int32ul,
)

Sections = GreedyRange(IMAGE_SECTION_HEADER)
