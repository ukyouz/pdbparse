from collections import deque

from construct import BitsSwapped
from construct import BitStruct
from construct import Bytes
from construct import CString
from construct import Enum
from construct import Flag
from construct import GreedyBytes
from construct import GreedyRange
from construct import Int8ul
from construct import Int16ul
from construct import Int32ul
from construct import ListContainer
from construct import Padding
from construct import PascalString
from construct import RestreamData
from construct import Struct
from construct import Switch
from construct import Union

from .tpi import flatten_leaf_data
from .tpi import insert_field_of_raw
from .tpi import sRaw

sLeafKind = Enum(
    Int16ul,
    S_PUB32_ST = 0x1009,  # a public symbol (CV internal reserved)

    S_CONSTANT = 0x1107,  # constant symbol
    S_UDT = 0x1108,  # User defined type
    S_LDATA32 = 0x110C,  # Module-local symbol
    S_GDATA32 = 0x110D,  # Global data symbol
    S_PUB32 = 0x110E,  # global thread storage
    S_GTHREAD32 = 0x1113,  # a public symbol (CV internal reserved)
    S_PROCREF = 0x1125,  # Reference to a procedure
    S_LPROCREF = 0x1127,  # Local Reference to a procedure
)

_pubSymFlags =  BitsSwapped(
    BitStruct(
        "Code" / Flag,
        "Function" / Flag,
        "Managed" / Flag,
        "MSIL" / Flag,
        Padding(28),
    ),
)

PUBSYM32 = Struct(
    # to speed up a little bit, reduce the fields need to be parsed
    "pubsymflags" / Int32ul,
    # "pubsymflags" / Union(
    #     0,
    #     "u32" / Int32ul,
    #     "f" / _pubSymFlags,
    # ),
    "offset" / Int32ul,
    "section" / Int16ul,
    "name" / CString("utf8"),
)


DATASYM32 = Struct(
    "typind" / Int32ul,
    "offset" / Int32ul,
    "section" / Int16ul,
    "name" / CString("utf8"),
)


REFSYM2 = Struct(
    "sumName" / Int32ul,
    "ibSym" / Int32ul,  # offset of actual symbol in $$Symbols
    "ximod" / Int16ul,  # module containing actual symbol, 1 based (check imodForXimod)
    "name" / CString("utf8"),
)


UDT = Struct(
    "typind" / Int32ul,
    "name" / CString("utf8"),
)


# ref: microsoft-pdb/include/cvinfo.h
GSYMBOL = Struct(
    "leafKind" / sLeafKind,
    "data" / Switch(
        lambda ctx: ctx.leafKind,
        {
            "S_CONSTANT": Struct(
                "typind" / Int32ul,
                "_raw" / sRaw("value"),
            ),
            "S_UDT": UDT,
            "S_PUB32_ST": PUBSYM32,
            "S_LDATA32": DATASYM32,
            "S_GDATA32": DATASYM32,
            "S_PUB32": PUBSYM32,
            "S_GTHREAD32" : Struct(
                "typind" / Int32ul,
                "offset" / Int32ul,
                "section" / Int16ul,
                "name" / CString("utf8"),
            ),
            "S_PROCREF": REFSYM2,
            "S_LPROCREF": REFSYM2,
        },
        default = Struct(
            "raw" / GreedyBytes
        ),
    )
)

GlobalsData = GreedyRange(
    Struct(
        "length" / Int16ul,
        "symbol" / RestreamData(Bytes(lambda ctx: ctx.length), GSYMBOL),
    )
)


def parse(data):
    cons = GlobalsData.parse(data)
    return _merge_structures(cons)


def parse_stream(stream):
    cons = GlobalsData.parse_stream(stream)
    return _merge_structures(cons)


def _merge_structures(con):
    new_cons = deque()
    for sym in con:
        lf = flatten_leaf_data(sym.symbol)
        insert_field_of_raw(lf)
        new_cons.append(lf)
    result = ListContainer(new_cons)
    return result
