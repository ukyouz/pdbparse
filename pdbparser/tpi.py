from typing import NamedTuple

from construct import BitsInteger
from construct import BitStruct
from construct import Bytes
from construct import Computed
from construct import Container
from construct import CString
from construct import Debugger
from construct import Enum
from construct import Flag
from construct import GreedyBytes
from construct import GreedyRange
from construct import If
from construct import IfThenElse
from construct import Int8sl
from construct import Int8ub
from construct import Int8ul
from construct import Int16sl
from construct import Int16ul
from construct import Int32sl
from construct import Int32ul
from construct import Int64sl
from construct import Int64ul
from construct import Optional
from construct import Padding
from construct import PascalString
from construct import Pass
from construct import Peek
from construct import RestreamData
from construct import Struct
from construct import Switch
from construct import Union

TypRefAttrs = {
    # "LF_ARGLIST": ["arg_type"],
    "LF_ARRAY": ["elemType", "idxType"],
    "LF_ARRAY_ST": ["elemType", "idxType"],
    "LF_BITFIELD": ["baseType"],
    # "LF_CLASS": ["fields", "derived", "vshape"],
    "LF_ENUM": ["utype", "fields"],
    "LF_FIELDLIST": [],
    # "LF_MFUNCTION": ["return_type", "class_type", "this_type", "arglist"],
    "LF_MODIFIER": ["modifiedType"],
    "LF_POINTER": ["utype"],
    # "LF_PROCEDURE": ["return_type", "arglist"],
    "LF_STRUCTURE": ["fields", "derived", "vshape"],
    "LF_STRUCTURE_ST": ["fields", "derived", "vshape"],
    "LF_UNION": ["fields"],
    "LF_UNION_ST": ["fields"],
    # "LF_VTSHAPE": [],

    # TODO: Unparsed
    # "LF_METHODLIST": [],
}


FieldsRefAttrs = {
    # FIELDLIST substructures
    "LF_BCLASS": ["index"],
    "LF_ENUMERATE": [],
    "LF_MEMBER": ["type"],
    "LF_MEMBER_ST": ["index"],
    "LF_METHOD": ["mlist"],
    "LF_NESTTYPE": ["type"],
    "LF_ONEMETHOD": ["index"],
    "LF_VFUNCTAB": ["type"],
}


### Enums for base and leaf types
# Exported from https://github.com/Microsoft/microsoft-pdb/cvinfo.h#L335
# Note: python only supports a max of 255 arguments to
# a function, so we have to put it into a dict and then
# call the function with the ** operator
class BasicType(NamedTuple):
    name: str
    size: int = 0
    has_sign: bool = False
    is_ptr: bool = False
    # fields: list = []

    def __str__(self) -> str:
        return self.name


eBaseTypes = {
    0x0000: BasicType("T_NOTYPE"),
    0x0003: BasicType("T_VOID", 4),
    0x0008: BasicType("T_HRESULT", 4), #?
    0x0010: BasicType("T_CHAR", 1, has_sign=True),
    0x0011: BasicType("T_SHORT", 2, has_sign=True),
    0x0012: BasicType("T_LONG", 4, has_sign=True),
    0x0013: BasicType("T_QUAD", 8, has_sign=True),
    0x0020: BasicType("T_UCHAR", 1),
    0x0021: BasicType("T_USHORT", 2),
    0x0022: BasicType("T_ULONG", 4),
    0x0023: BasicType("T_UQUAD", 8),
    0x0030: BasicType("T_BOOL08", 1),
    0x0040: BasicType("T_REAL32", 4, has_sign=True),
    0x0041: BasicType("T_REAL64", 8, has_sign=True),
    0x0042: BasicType("T_REAL80", 10, has_sign=True),
    0x0070: BasicType("T_RCHAR", 1),
    0x0071: BasicType("T_WCHAR", 2),
    0x0074: BasicType("T_INT4", 4, has_sign=True),
    0x0075: BasicType("T_UINT4", 4),
    0x0077: BasicType("T_UINT8", 8),
    0x007A: BasicType("T_CHAR16", 2),
    0x007B: BasicType("T_CHAR32", 4),

    0x0103: BasicType("T_PVOID", 4, is_ptr=True),

    0x0403: BasicType("T_32PVOID", 4, is_ptr=True),
    0x0411: BasicType("T_32PSHORT", 4, is_ptr=True),
    0x0412: BasicType("T_32PLONG", 4, is_ptr=True),
    0x0413: BasicType("T_32PQUAD", 4, is_ptr=True),
    0x0420: BasicType("T_32PUCHAR", 4, is_ptr=True),
    0x0421: BasicType("T_32PUSHORT", 4, is_ptr=True),
    0x0422: BasicType("T_32PULONG", 4, is_ptr=True),
    0x0423: BasicType("T_32PUQUAD", 4, is_ptr=True),
    0x0430: BasicType("T_32PBOOL08", 4, is_ptr=True),
    0x0440: BasicType("T_32PREAL32", 4, is_ptr=True),
    0x0441: BasicType("T_32PREAL64", 4, is_ptr=True),
    0x0470: BasicType("T_32PRCHAR", 4, is_ptr=True),
    0x0471: BasicType("T_32PWCHAR", 4, is_ptr=True),
    0x0474: BasicType("T_32PINT4", 4, is_ptr=True),
    0x0475: BasicType("T_32PUINT4", 4, is_ptr=True),
    0x047A: BasicType("T_32PCHAR16", 4, is_ptr=True),
    0x047B: BasicType("T_32PCHAR32", 4, is_ptr=True),

    0x0603: BasicType("T_64PVOID", 8, is_ptr=True),
}


# Fewer than 255 values so we're ok here
# Exported from https:#github.com/Microsoft/microsoft-pdb/cvinfo.h#L772
eLeafKind = Enum(
    Int16ul,
    # leaf indices starting records but referenced from symbol records
    LF_MODIFIER_16t = 0x0001,
    LF_POINTER_16t = 0x0002,
    LF_ARRAY_16t = 0x0003,
    LF_CLASS_16t = 0x0004,
    LF_STRUCTURE_16t = 0x0005,
    LF_UNION_16t = 0x0006,
    LF_ENUM_16t = 0x0007,
    LF_PROCEDURE_16t = 0x0008,
    LF_MFUNCTION_16t = 0x0009,
    LF_VTSHAPE = 0x000a,
    LF_COBOL0_16t = 0x000b,
    LF_COBOL1 = 0x000c,
    LF_BARRAY_16t = 0x000d,
    LF_LABEL = 0x000e,
    LF_NULL = 0x000f,
    LF_NOTTRAN = 0x0010,
    LF_DIMARRAY_16t = 0x0011,
    LF_VFTPATH_16t = 0x0012,
    LF_PRECOMP_16t = 0x0013,  # not referenced from symbol
    LF_ENDPRECOMP = 0x0014,  # not referenced from symbol
    LF_OEM_16t = 0x0015,  # oem definable type string
    LF_TYPESERVER_ST = 0x0016,  # not referenced from symbol

    # leaf indices starting records but referenced only from type records
    LF_SKIP_16t = 0x0200,
    LF_ARGLIST_16t = 0x0201,
    LF_DEFARG_16t = 0x0202,
    LF_LIST = 0x0203,
    LF_FIELDLIST_16t = 0x0204,
    LF_DERIVED_16t = 0x0205,
    LF_BITFIELD_16t = 0x0206,
    LF_METHODLIST_16t = 0x0207,
    LF_DIMCONU_16t = 0x0208,
    LF_DIMCONLU_16t = 0x0209,
    LF_DIMVARU_16t = 0x020a,
    LF_DIMVARLU_16t = 0x020b,
    LF_REFSYM = 0x020c,
    LF_BCLASS_16t = 0x0400,
    LF_VBCLASS_16t = 0x0401,
    LF_IVBCLASS_16t = 0x0402,
    LF_ENUMERATE_ST = 0x0403,
    LF_FRIENDFCN_16t = 0x0404,
    LF_INDEX_16t = 0x0405,
    LF_MEMBER_16t = 0x0406,
    LF_STMEMBER_16t = 0x0407,
    LF_METHOD_16t = 0x0408,
    LF_NESTTYPE_16t = 0x0409,
    LF_VFUNCTAB_16t = 0x040a,
    LF_FRIENDCLS_16t = 0x040b,
    LF_ONEMETHOD_16t = 0x040c,
    LF_VFUNCOFF_16t = 0x040d,

    # 32-bit type index versions of leaves, all have the 0x1000 bit set
    #
    LF_TI16_MAX = 0x1000,
    LF_MODIFIER = 0x1001,
    LF_POINTER = 0x1002,
    LF_ARRAY_ST = 0x1003,
    LF_CLASS_ST = 0x1004,
    LF_STRUCTURE_ST = 0x1005,
    LF_UNION_ST = 0x1006,
    LF_ENUM_ST = 0x1007,
    LF_PROCEDURE = 0x1008,
    LF_MFUNCTION = 0x1009,
    LF_COBOL0 = 0x100a,
    LF_BARRAY = 0x100b,
    LF_DIMARRAY_ST = 0x100c,
    LF_VFTPATH = 0x100d,
    LF_PRECOMP_ST = 0x100e,  # not referenced from symbol
    LF_OEM = 0x100f,  # oem definable type string
    LF_ALIAS_ST = 0x1010,  # alias (typedef) type
    LF_OEM2 = 0x1011,  # oem definable type string

    # leaf indices starting records but referenced only from type records
    LF_SKIP = 0x1200,
    LF_ARGLIST = 0x1201,
    LF_DEFARG_ST = 0x1202,
    LF_FIELDLIST = 0x1203,
    LF_DERIVED = 0x1204,
    LF_BITFIELD = 0x1205,
    LF_METHODLIST = 0x1206,
    LF_DIMCONU = 0x1207,
    LF_DIMCONLU = 0x1208,
    LF_DIMVARU = 0x1209,
    LF_DIMVARLU = 0x120a,
    LF_BCLASS = 0x1400,
    LF_VBCLASS = 0x1401,
    LF_IVBCLASS = 0x1402,
    LF_FRIENDFCN_ST = 0x1403,
    LF_INDEX = 0x1404,
    LF_MEMBER_ST = 0x1405,
    LF_STMEMBER_ST = 0x1406,
    LF_METHOD_ST = 0x1407,
    LF_NESTTYPE_ST = 0x1408,
    LF_VFUNCTAB = 0x1409,
    LF_FRIENDCLS = 0x140a,
    LF_ONEMETHOD_ST = 0x140b,
    LF_VFUNCOFF = 0x140c,
    LF_NESTTYPEEX_ST = 0x140d,
    LF_MEMBERMODIFY_ST = 0x140e,
    LF_MANAGED_ST = 0x140f,

    # Types w/ SZ names
    LF_ST_MAX = 0x1500,
    LF_TYPESERVER = 0x1501,  # not referenced from symbol
    LF_ENUMERATE = 0x1502,
    LF_ARRAY = 0x1503,
    LF_CLASS = 0x1504,
    LF_STRUCTURE = 0x1505,
    LF_UNION = 0x1506,
    LF_ENUM = 0x1507,
    LF_DIMARRAY = 0x1508,
    LF_PRECOMP = 0x1509,  # not referenced from symbol
    LF_ALIAS = 0x150a,  # alias (typedef) type
    LF_DEFARG = 0x150b,
    LF_FRIENDFCN = 0x150c,
    LF_MEMBER = 0x150d,
    LF_STMEMBER = 0x150e,
    LF_METHOD = 0x150f,
    LF_NESTTYPE = 0x1510,
    LF_ONEMETHOD = 0x1511,
    LF_NESTTYPEEX = 0x1512,
    LF_MEMBERMODIFY = 0x1513,
    LF_MANAGED = 0x1514,
    LF_TYPESERVER2 = 0x1515,
    LF_STRIDED_ARRAY = 0x1516,  # same as LF_ARRAY, but with stride between adjacent elements
    LF_HLSL = 0x1517,
    LF_MODIFIER_EX = 0x1518,
    LF_INTERFACE = 0x1519,
    LF_BINTERFACE = 0x151a,
    LF_VECTOR = 0x151b,
    LF_MATRIX = 0x151c,
    LF_VFTABLE = 0x151d,  # a virtual function table
    # LF_ENDOFLEAFRECORD  = 0x151d,
    LF_TYPE_LAST = 0x151d + 1,  # one greater than the last type record
    # LF_TYPE_MAX         = (LF_TYPE_LAST) - 1,
    LF_FUNC_ID = 0x1601,  # global func ID
    LF_MFUNC_ID = 0x1602,  # member func ID
    LF_BUILDINFO = 0x1603,  # build info: tool, version, command line, src/pdb file
    LF_SUBSTR_LIST = 0x1604,  # similar to LF_ARGLIST, for list of sub strings
    LF_STRING_ID = 0x1605,  # string ID
    LF_UDT_SRC_LINE = 0x1606,  # source and line on where an UDT is defined
    # only generated by compiler
    LF_UDT_MOD_SRC_LINE = 0x1607,  # module, source and line on where an UDT is defined
    # only generated by linker
    LF_ID_LAST = 0x1607 + 1,  # one greater than the last ID record
    # LF_ID_MAX           = (LF_ID_MAX) - 1,

    # LF_NUMERIC          = 0x8000,
    LF_CHAR = 0x8000,
    LF_SHORT = 0x8001,
    LF_USHORT = 0x8002,
    LF_LONG = 0x8003,
    LF_ULONG = 0x8004,
    LF_REAL32 = 0x8005,
    LF_REAL64 = 0x8006,
    LF_REAL80 = 0x8007,
    LF_REAL128 = 0x8008,
    LF_QUADWORD = 0x8009,
    LF_UQUADWORD = 0x800a,
    LF_REAL48 = 0x800b,
    LF_COMPLEX32 = 0x800c,
    LF_COMPLEX64 = 0x800d,
    LF_COMPLEX80 = 0x800e,
    LF_COMPLEX128 = 0x800f,
    LF_VARSTRING = 0x8010,
    LF_OCTWORD = 0x8017,
    LF_UOCTWORD = 0x8018,
    LF_DECIMAL = 0x8019,
    LF_DATE = 0x801a,
    LF_UTF8STRING = 0x801b,
    LF_REAL16 = 0x801c,
    LF_PAD0 = 0xf0,
    LF_PAD1 = 0xf1,
    LF_PAD2 = 0xf2,
    LF_PAD3 = 0xf3,
    LF_PAD4 = 0xf4,
    LF_PAD5 = 0xf5,
    LF_PAD6 = 0xf6,
    LF_PAD7 = 0xf7,
    LF_PAD8 = 0xf8,
    LF_PAD9 = 0xf9,
    LF_PAD10 = 0xfa,
    LF_PAD11 = 0xfb,
    LF_PAD12 = 0xfc,
    LF_PAD13 = 0xfd,
    LF_PAD14 = 0xfe,
    LF_PAD15 = 0xff,
)


def sRaw(name):
    return Struct(
        "_raw_attr" / Computed(lambda ctx: name),
        "_data0" / Int16ul,
        "_data1" / IfThenElse(
            lambda ctx: ctx._data0 < int(eLeafKind.LF_CHAR),
            CString(encoding = "utf8"),
            Switch(
                lambda ctx: ctx._data0,
                {
                    int(eLeafKind.LF_CHAR): Struct(
                        "value" / Int8sl,
                        "name" / CString(encoding = "utf8"),
                    ),
                    int(eLeafKind.LF_SHORT): Struct(
                        "value" / Int16sl,
                        "name" / CString(encoding = "utf8"),
                    ),
                    int(eLeafKind.LF_USHORT): Struct(
                        "value" / Int16ul,
                        "name" / CString(encoding = "utf8"),
                    ),
                    int(eLeafKind.LF_LONG): Struct(
                        "value" / Int32sl,
                        "name" / CString(encoding = "utf8"),
                    ),
                    int(eLeafKind.LF_ULONG): Struct(
                        "value" / Int32ul,
                        "name" / CString(encoding = "utf8"),
                    ),
                    int(eLeafKind.LF_QUADWORD): Struct(
                        "value" / Int64sl,
                        "name" / CString(encoding = "utf8"),
                    ),
                    int(eLeafKind.LF_UQUADWORD): Struct(
                        "value" / Int64ul,
                        "name" / CString(encoding = "utf8"),
                    ),
                },
            ),
        )
    )


def insert_field_of_raw(t_data):
    if not hasattr(t_data, "_raw"):
        return
    if t_data._raw._data0 < int(eLeafKind.LF_CHAR):
        t_data[t_data._raw._raw_attr] = t_data._raw._data0
        t_data["name"] = t_data._raw._data1
    else:
        t_data[t_data._raw._raw_attr] = t_data._raw._data1.value
        t_data["name"] = t_data._raw._data1.name


PadAlign = If(
    lambda ctx: ctx._pad != None and ctx._pad > 0xF0,
    Optional(Padding(lambda ctx: ctx._pad & 0x0F))
)

### alias Int32ul to inform that the  value is a type index
IntIndex = Int32ul

### Leaf types
sFieldAttr = BitStruct(
    "noconstruct" / Flag,
    "noinherit" / Flag,
    "pseudo" / Flag,
    "mprop" / Enum(
        BitsInteger(3),
        MTvanilla = 0x00,
        MTvirtual = 0x01,
        MTstatic = 0x02,
        MTfriend = 0x03,
        MTintro = 0x04,
        MTpurevirt = 0x05,
        MTpureintro = 0x06,
        _default_ = Pass,
    ),
    "access" / Enum(
        BitsInteger(2),
        private = 1,
        protected = 2,
        public = 3,
        _default_ = Pass,
    ),
    Padding(7),
    "compgenx" / Flag,
)

sSubStruct = Struct(
    "leafKind" / eLeafKind,
    "data" / Switch(
        lambda ctx: ctx.leafKind,
        {
            "LF_MEMBER_ST": Struct(
                "attr" / sFieldAttr,
                "index" / Int32ul,
                "offset" / Int16ul,
                "name" / PascalString(Int8ub, "utf8"),
                "_pad" / Peek(Int8ul),
                PadAlign,
            ),
            "LF_MEMBER": Struct(
                "attr" / sFieldAttr,
                "type" / Int32ul,
                "_raw" / sRaw("offset"),
                "_pad" / Peek(Int8ul),
                PadAlign,
            ),
            "LF_ENUMERATE": Struct(
                "attr" / sFieldAttr,
                "_raw" / sRaw("value"),
                "_pad" / Peek(Int8ul),
                PadAlign,
            ),
            "LF_BCLASS": Struct(
                "attr" / sFieldAttr,
                "index" / Int32ul,
                "_raw" / sRaw("offset"),
                "_pad" / Peek(Int8ul),
                PadAlign,
            ),
            "LF_VFUNCTAB": Struct(
                Padding(2),
                "type" / Int32ul,
                "_pad" / Peek(Int8ul),
                PadAlign,
            ),
            "LF_ONEMETHOD": Struct(
                "attr" / sFieldAttr,
                "index" / Int32ul,
                "intro" / Switch(
                    lambda ctx: ctx.fldattr.mprop,
                    {
                        "MTintro": Struct(
                            "val" / Int32ul,
                            "str_data" / CString(encoding = "utf8"),
                        ),
                        "MTpureintro": Struct(
                            "val" / Int32ul,
                            "str_data" / CString(encoding = "utf8"),
                        ),
                    },
                    default = "str_data" / CString(encoding = "utf8"),
                ),
                "_pad" / Peek(Int8ul),
                PadAlign,
            ),
            "LF_METHOD": Struct(
                "count" / Int16ul,
                "mlist" / Int32ul,
                "name" / CString(encoding = "utf8"),
                "_pad" / Peek(Int8ul),
                PadAlign,
            ),
            "LF_NESTTYPE": Struct(
                Padding(2),
                "type" / Int32ul,
                "name" / CString(encoding = "utf8"),
                "_pad" / Peek(Int8ul),
                PadAlign,
            ),
        },
    ),
)


lfFieldList = Struct(
    "fields" / GreedyRange(sSubStruct)
)

lfArray = "lfArray" / Struct(
    "elemType" / IntIndex,
    "idxType" / IntIndex,
    "_raw" / sRaw("size"),
)

lfArrayST = "lfArray" / Struct(
    "elemType" / IntIndex,
    "idxType" / IntIndex,
    "size" / Int16ul,
    "name" / PascalString(Int8ub, "utf8"),
)

lfModifier = "lfModifier" / Struct(
    "modifiedType" / Int32ul,
    "modifier" / BitStruct(
        Padding(5),
        "unaligned" / Flag,
        "volatile" / Flag,
        "const" / Flag,
        Padding(8),
    ),
)

lfBitfield = "lfBitfield" / Struct(
    "baseType" / IntIndex,
    "length" / Int8ul,
    "position" / Int8ul,
)

sCvProperty = BitStruct(
    "fwdref" / Flag,
    "opcast" / Flag,
    "opassign" / Flag,
    "cnested" / Flag,
    "isnested" / Flag,
    "ovlops" / Flag,
    "ctor" / Flag,
    "packed" / Flag,
    "reserved" / BitsInteger(7),
    "scoped" / Flag,
)

lfEnum = "lfEnum" / Struct(
    "count" / Int16ul,
    "property" / sCvProperty,
    "utype" / Int32ul,
    "fields" / Int32ul,
    "name" / CString(encoding = "utf8"),
)

lfStructure = Struct(
    "count" / Int16ul,
    "property" / sCvProperty,
    "fields" / IntIndex,
    "derived" / IntIndex,
    "vshape" / IntIndex,
    "_raw" / sRaw("size"),
)


lfStructureST = Struct(
    "count" / Int16ul,
    "property" / sCvProperty,
    "fields" / IntIndex,
    "derived" / IntIndex,
    "vshape" / IntIndex,
    "size" / Int16ul,
    "name" / PascalString(Int8ub, "utf8"),
)

lfUnion = Struct(
    "count" / Int16ul,
    "property" / sCvProperty,
    "fields" / Int32ul,
    "_raw" / sRaw("size"),
)

lfUnionST = Struct(
    "count" / Int16ul,
    "property" / sCvProperty,
    "fields" / Int32ul,
    "size" / Int16ul,
    "name" / PascalString(Int8ub, "utf8"),
)

lfPointer = Struct(
    "utype" / Int32ul,
    "ptr_attr" / BitStruct(
        "mode" / Enum(
            BitsInteger(3),
            PTR_MODE_PTR = 0x00000000,
            PTR_MODE_REF = 0x00000001,
            PTR_MODE_PMEM = 0x00000002,
            PTR_MODE_PMFUNC = 0x00000003,
            PTR_MODE_RESERVED = 0x00000004,
        ),
        "type" / Enum(
            BitsInteger(5),
            PTR_NEAR = 0x00000000,
            PTR_FAR = 0x00000001,
            PTR_HUGE = 0x00000002,
            PTR_BASE_SEG = 0x00000003,
            PTR_BASE_VAL = 0x00000004,
            PTR_BASE_SEGVAL = 0x00000005,
            PTR_BASE_ADDR = 0x00000006,
            PTR_BASE_SEGADDR = 0x00000007,
            PTR_BASE_TYPE = 0x00000008,
            PTR_BASE_SELF = 0x00000009,
            PTR_NEAR32 = 0x0000000A,
            PTR_FAR32 = 0x0000000B,
            PTR_64 = 0x0000000C,
            PTR_UNUSEDPTR = 0x0000000D,
        ),
        Padding(3),
        "restrict" / Flag,
        "unaligned" / Flag,
        "const" / Flag,
        "volatile" / Flag,
        "flat32" / Flag,
        Padding(16),
    ),
)

sTypType = Struct(
    "length" / Int16ul,
    "leafKind" / eLeafKind,
    "data" / RestreamData(
        Bytes(lambda this: this.length - 2),
        Switch(
            lambda this: this.leafKind,
            {
                "LF_ARRAY": lfArray,
                "LF_ARRAY_ST": lfArrayST,
                "LF_MODIFIER": lfModifier,
                "LF_BITFIELD": lfBitfield,
                "LF_ENUM": lfEnum,
                "LF_FIELDLIST": lfFieldList,
                "LF_STRUCTURE": lfStructure,
                "LF_STRUCTURE_ST": lfStructureST,
                "LF_UNION": lfUnion,
                "LF_UNION_ST": lfUnionST,
                "LF_POINTER": lfPointer,
            },
            default = Pass,
        ),
    ),
)


def flatten_leaf_data(lf):
    """ insert leafKind to data attribute, and return attribute as a new leaf """
    if lf.data is None:
        lf.data = Container()
    lf.data.leafKind = lf.leafKind
    return lf.data


"""
helper functions
"""
ARCH_PTR_SIZE = 4

def get_size(lf):
    if isinstance(lf, BasicType):
        return lf.size
    elif lf.leafKind in {
        eLeafKind.LF_STRUCTURE,
        eLeafKind.LF_STRUCTURE_ST,
        eLeafKind.LF_UNION,
        eLeafKind.LF_UNION_ST,
        eLeafKind.LF_ARRAY,
    }:
        return lf.size
    elif lf.leafKind == eLeafKind.LF_POINTER:
        return ARCH_PTR_SIZE
    elif lf.leafKind == eLeafKind.LF_ENUM:
        return 4  # FIXME not sure ??
    elif lf.leafKind == eLeafKind.LF_BITFIELD:
        return lf.baseTypeRef.size
    # elif lf.leafKind == eLeafKind.LF_MODIFIER:
    #     return get_size(lf.modified_type)
    else:
        return -1

def arr_dims(lf):
    assert lf.leafKind == eLeafKind.LF_ARRAY


def get_tpname(lf):
    if isinstance(lf, BasicType):
        return str(lf)
    elif lf.leafKind in {
        eLeafKind.LF_STRUCTURE,
        eLeafKind.LF_STRUCTURE_ST,
        eLeafKind.LF_UNION,
        eLeafKind.LF_UNION_ST,
        eLeafKind.LF_ENUM,
    }:
        return lf.name
    elif lf.leafKind == eLeafKind.LF_POINTER:
        return "(%s *)" % get_tpname(lf.utypeRef)
    # elif lf.leafKind == eLeafKind.LF_PROCEDURE:
    #     return proc_str(lf)
    # elif lf.leafKind == eLeafKind.LF_MODIFIER:
    #     return mod_str(lf)
    elif lf.leafKind == eLeafKind.LF_ARRAY:
        dims = []
        item_lf = lf
        while getattr(item_lf, "leafKind", None) == eLeafKind.LF_ARRAY:
            dims.append(get_size(item_lf) // get_size(item_lf.elemTypeRef))
            item_lf = item_lf.elemTypeRef
        return "%s%s" % (get_tpname(item_lf), "".join(["[%d]" % d for d in dims]))
    elif lf.leafKind == eLeafKind.LF_BITFIELD:
        return str(lf.leafKind)
    else:
        return str(lf.leafKind)