from typing import NamedTuple
from typing import Self

from construct import Array
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
    "LF_ARGLIST": ["args"],
    "LF_PROCEDURE": ["rvtype", "arglist"],
    "LF_ARRAY": ["elemType", "idxType"],
    "LF_ARRAY_ST": ["elemType", "idxType"],
    "LF_BITFIELD": ["baseType"],
    "LF_CLASS": ["fields", "derived", "vshape"],
    "LF_ENUM": ["utype", "fields"],
    "LF_FIELDLIST": [],
    # "LF_MFUNCTION": ["return_type", "class_type", "this_type", "arglist"],
    "LF_MODIFIER": ["modifiedType"],
    "LF_POINTER": ["utype"],
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
    "LF_STMEMBER": ["index"],
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
    is_real: bool = False
    utype: int = -1
    # fields: list = []

    def __str__(self) -> str:
        return self.name


eBaseTypes = {
    0x0000: BasicType("T_NOTYPE"),
    # T_ABS           = 0x0001,   // absolute symbol
    # T_SEGMENT       = 0x0002,   // segment type
    0x0003: BasicType("T_VOID", 4),
    # T_CURRENCY      = 0x0004,   // BASIC 8 byte currency value
    # T_NBASICSTR     = 0x0005,   // Near BASIC string
    # T_FBASICSTR     = 0x0006,   // Far BASIC string
    # T_NOTTRANS      = 0x0007,   // type not translated by cvpack
    0x0008: BasicType("T_HRESULT", 4), #?
    0x0010: BasicType("T_CHAR", 1, has_sign=True),
    0x0011: BasicType("T_SHORT", 2, has_sign=True),
    0x0012: BasicType("T_LONG", 4, has_sign=True),
    0x0013: BasicType("T_QUAD", 8, has_sign=True),
    # T_OCT           = 0x0014,   // 128 bit signed
    0x0020: BasicType("T_UCHAR", 1),
    0x0021: BasicType("T_USHORT", 2),
    0x0022: BasicType("T_ULONG", 4),
    0x0023: BasicType("T_UQUAD", 8),
    # T_UOCT          = 0x0024,   // 128 bit unsigned
    0x0030: BasicType("T_BOOL08", 1),
    # T_BOOL16        = 0x0031,   // 16 bit boolean
    # T_BOOL32        = 0x0032,   // 32 bit boolean
    # T_BOOL64        = 0x0033,   // 64 bit boolean
    0x0040: BasicType("T_REAL32", 4, has_sign=True, is_real=True),
    0x0041: BasicType("T_REAL64", 8, has_sign=True, is_real=True),
    0x0042: BasicType("T_REAL80", 10, has_sign=True, is_real=True),
    # T_REAL128       = 0x0043,   // 128 bit real
    # T_REAL48        = 0x0044,   // 48 bit real
    # T_REAL32PP      = 0x0045,   // 32 bit PP real
    # T_REAL16        = 0x0046,   // 16 bit real
    # T_CPLX32        = 0x0050,   // 32 bit complex
    # T_CPLX80        = 0x0052,   // 80 bit complex
    # T_CPLX128       = 0x0053,   // 128 bit complex
    # T_BIT           = 0x0060,   // bit
    # T_PASCHAR       = 0x0061,   // Pascal CHAR
    # T_BOOL32FF      = 0x0062,   // 32-bit BOOL where true is 0xffffffff
    # T_INT1          = 0x0068,   // 8 bit signed int
    # T_UINT1         = 0x0069,   // 8 bit unsigned int
    0x0070: BasicType("T_RCHAR", 1),
    0x0071: BasicType("T_WCHAR", 2),
    # T_INT2          = 0x0072,   // 16 bit signed int
    # T_UINT2         = 0x0073,   // 16 bit unsigned int
    0x0074: BasicType("T_INT4", 4, has_sign=True),
    0x0075: BasicType("T_UINT4", 4),
    # T_INT8          = 0x0076,   // 64 bit signed int
    0x0077: BasicType("T_UINT8", 8),
    # T_INT16         = 0x0078,   // 128 bit signed int
    # T_UINT16        = 0x0079,   // 128 bit unsigned int
    0x007A: BasicType("T_CHAR16", 2),
    0x007B: BasicType("T_CHAR32", 4),
}
eBaseTypes.update({
    0x0103: BasicType("T_PVOID", 4, is_ptr=True, utype=0x03),
    # T_PFVOID        = 0x0203,   // far pointer to void
    # T_PHVOID        = 0x0303,   // huge pointer to void
    0x0403: BasicType("T_32PVOID", 4, is_ptr=True, utype=0x03),
    # T_32PFVOID      = 0x0503,   // 16:32 pointer to void
    0x0603: BasicType("T_64PVOID", 8, is_ptr=True, utype=0x03),

    0x0408: BasicType("LF_METHOD_16t", 4, is_ptr=True, utype=0x08),

    # T_PCHAR         = 0x0110,   // 16 bit pointer to 8 bit signed
    # T_PFCHAR        = 0x0210,   // 16:16 far pointer to 8 bit signed
    # T_PHCHAR        = 0x0310,   // 16:16 huge pointer to 8 bit signed
    # T_32PCHAR       = 0x0410,   // 32 bit pointer to 8 bit signed
    # T_32PFCHAR      = 0x0510,   // 16:32 pointer to 8 bit signed
    # T_64PCHAR       = 0x0610,   // 64 bit pointer to 8 bit signed

    # T_PUCHAR        = 0x0120,   // 16 bit pointer to 8 bit unsigned
    # T_PFUCHAR       = 0x0220,   // 16:16 far pointer to 8 bit unsigned
    # T_PHUCHAR       = 0x0320,   // 16:16 huge pointer to 8 bit unsigned
    0x0420: BasicType("T_32PUCHAR", 4, is_ptr=True, utype=0x20),
    # T_32PFUCHAR     = 0x0520,   // 16:32 pointer to 8 bit unsigned
    # T_64PUCHAR      = 0x0620,   // 64 bit pointer to 8 bit unsigned

    # T_PRCHAR        = 0x0170,   // 16 bit pointer to a real char
    # T_PFRCHAR       = 0x0270,   // 16:16 far pointer to a real char
    # T_PHRCHAR       = 0x0370,   // 16:16 huge pointer to a real char
    0x0470: BasicType("T_32PRCHAR", 4, is_ptr=True, utype=0x70),
    # T_32PFRCHAR     = 0x0570,   // 16:32 pointer to a real char
    # T_64PRCHAR      = 0x0670,   // 64 bit pointer to a real char

    # T_PWCHAR        = 0x0171,   // 16 bit pointer to a wide char
    # T_PFWCHAR       = 0x0271,   // 16:16 far pointer to a wide char
    # T_PHWCHAR       = 0x0371,   // 16:16 huge pointer to a wide char
    0x0471: BasicType("T_32PWCHAR", 4, is_ptr=True, utype=0x71),
    # T_32PFWCHAR     = 0x0571,   // 16:32 pointer to a wide char
    # T_64PWCHAR      = 0x0671,   // 64 bit pointer to a wide char

    # T_PCHAR16        = 0x017a,   // 16 bit pointer to a 16-bit unicode char
    # T_PFCHAR16       = 0x027a,   // 16:16 far pointer to a 16-bit unicode char
    # T_PHCHAR16       = 0x037a,   // 16:16 huge pointer to a 16-bit unicode char
    0x047A: BasicType("T_32PCHAR16", 4, is_ptr=True, utype=0x7A),
    # T_32PFCHAR16     = 0x057a,   // 16:32 pointer to a 16-bit unicode char
    # T_64PCHAR16      = 0x067a,   // 64 bit pointer to a 16-bit unicode char

    # T_PCHAR32        = 0x017b,   // 16 bit pointer to a 32-bit unicode char
    # T_PFCHAR32       = 0x027b,   // 16:16 far pointer to a 32-bit unicode char
    # T_PHCHAR32       = 0x037b,   // 16:16 huge pointer to a 32-bit unicode char
    0x047B: BasicType("T_32PCHAR32", 4, is_ptr=True, utype=0x7B),
    # T_32PFCHAR32     = 0x057b,   // 16:32 pointer to a 32-bit unicode char
    # T_64PCHAR32      = 0x067b,   // 64 bit pointer to a 32-bit unicode char

    # T_PINT1         = 0x0168,   // 16 bit pointer to 8 bit signed int
    # T_PFINT1        = 0x0268,   // 16:16 far pointer to 8 bit signed int
    # T_PHINT1        = 0x0368,   // 16:16 huge pointer to 8 bit signed int
    # T_32PINT1       = 0x0468,   // 32 bit pointer to 8 bit signed int
    # T_32PFINT1      = 0x0568,   // 16:32 pointer to 8 bit signed int
    # T_64PINT1       = 0x0668,   // 64 bit pointer to 8 bit signed int

    # T_PUINT1        = 0x0169,   // 16 bit pointer to 8 bit unsigned int
    # T_PFUINT1       = 0x0269,   // 16:16 far pointer to 8 bit unsigned int
    # T_PHUINT1       = 0x0369,   // 16:16 huge pointer to 8 bit unsigned int
    # T_32PUINT1      = 0x0469,   // 32 bit pointer to 8 bit unsigned int
    # T_32PFUINT1     = 0x0569,   // 16:32 pointer to 8 bit unsigned int
    # T_64PUINT1      = 0x0669,   // 64 bit pointer to 8 bit unsigned int

    # T_PSHORT        = 0x0111,   // 16 bit pointer to 16 bit signed
    # T_PFSHORT       = 0x0211,   // 16:16 far pointer to 16 bit signed
    # T_PHSHORT       = 0x0311,   // 16:16 huge pointer to 16 bit signed
    0x0411: BasicType("T_32PSHORT", 4, is_ptr=True, utype=0x11),
    # T_32PFSHORT     = 0x0511,   // 16:32 pointer to 16 bit signed
    # T_64PSHORT      = 0x0611,   // 64 bit pointer to 16 bit signed

    # T_PUSHORT       = 0x0121,   // 16 bit pointer to 16 bit unsigned
    # T_PFUSHORT      = 0x0221,   // 16:16 far pointer to 16 bit unsigned
    # T_PHUSHORT      = 0x0321,   // 16:16 huge pointer to 16 bit unsigned
    0x0421: BasicType("T_32PUSHORT", 4, is_ptr=True, utype=0x21),
    # T_32PFUSHORT    = 0x0521,   // 16:32 pointer to 16 bit unsigned
    # T_64PUSHORT     = 0x0621,   // 64 bit pointer to 16 bit unsigned

    # T_PINT2         = 0x0172,   // 16 bit pointer to 16 bit signed int
    # T_PFINT2        = 0x0272,   // 16:16 far pointer to 16 bit signed int
    # T_PHINT2        = 0x0372,   // 16:16 huge pointer to 16 bit signed int
    # T_32PINT2       = 0x0472,   // 32 bit pointer to 16 bit signed int
    # T_32PFINT2      = 0x0572,   // 16:32 pointer to 16 bit signed int
    # T_64PINT2       = 0x0672,   // 64 bit pointer to 16 bit signed int

    # T_PUINT2        = 0x0173,   // 16 bit pointer to 16 bit unsigned int
    # T_PFUINT2       = 0x0273,   // 16:16 far pointer to 16 bit unsigned int
    # T_PHUINT2       = 0x0373,   // 16:16 huge pointer to 16 bit unsigned int
    # T_32PUINT2      = 0x0473,   // 32 bit pointer to 16 bit unsigned int
    # T_32PFUINT2     = 0x0573,   // 16:32 pointer to 16 bit unsigned int
    # T_64PUINT2      = 0x0673,   // 64 bit pointer to 16 bit unsigned int

    # T_PLONG         = 0x0112,   // 16 bit pointer to 32 bit signed
    # T_PULONG        = 0x0122,   // 16 bit pointer to 32 bit unsigned
    # T_PFLONG        = 0x0212,   // 16:16 far pointer to 32 bit signed
    # T_PFULONG       = 0x0222,   // 16:16 far pointer to 32 bit unsigned
    # T_PHLONG        = 0x0312,   // 16:16 huge pointer to 32 bit signed
    # T_PHULONG       = 0x0322,   // 16:16 huge pointer to 32 bit unsigned

    0x0412: BasicType("T_32PLONG", 4, is_ptr=True, utype=0x12),
    0x0422: BasicType("T_32PULONG", 4, is_ptr=True, utype=0x22),
    # T_32PFLONG      = 0x0512,   // 16:32 pointer to 32 bit signed
    # T_32PFULONG     = 0x0522,   // 16:32 pointer to 32 bit unsigned
    # T_64PLONG       = 0x0612,   // 64 bit pointer to 32 bit signed
    # T_64PULONG      = 0x0622,   // 64 bit pointer to 32 bit unsigned

    # T_PINT4         = 0x0174,   // 16 bit pointer to 32 bit signed int
    # T_PFINT4        = 0x0274,   // 16:16 far pointer to 32 bit signed int
    # T_PHINT4        = 0x0374,   // 16:16 huge pointer to 32 bit signed int
    0x0474: BasicType("T_32PINT4", 4, is_ptr=True, utype=0x74),
    # T_32PFINT4      = 0x0574,   // 16:32 pointer to 32 bit signed int
    # T_64PINT4       = 0x0674,   // 64 bit pointer to 32 bit signed int

    # T_PUINT4        = 0x0175,   // 16 bit pointer to 32 bit unsigned int
    # T_PFUINT4       = 0x0275,   // 16:16 far pointer to 32 bit unsigned int
    # T_PHUINT4       = 0x0375,   // 16:16 huge pointer to 32 bit unsigned int
    0x0475: BasicType("T_32PUINT4", 4, is_ptr=True, utype=0x75),
    # T_32PFUINT4     = 0x0575,   // 16:32 pointer to 32 bit unsigned int
    # T_64PUINT4      = 0x0675,   // 64 bit pointer to 32 bit unsigned int

    # T_PQUAD         = 0x0113,   // 16 bit pointer to 64 bit signed
    # T_PFQUAD        = 0x0213,   // 16:16 far pointer to 64 bit signed
    # T_PHQUAD        = 0x0313,   // 16:16 huge pointer to 64 bit signed
    0x0413: BasicType("T_32PQUAD", 4, is_ptr=True, utype=0x13),
    # T_32PFQUAD      = 0x0513,   // 16:32 pointer to 64 bit signed
    # T_64PQUAD       = 0x0613,   // 64 bit pointer to 64 bit signed

    # T_PUQUAD        = 0x0123,   // 16 bit pointer to 64 bit unsigned
    # T_PFUQUAD       = 0x0223,   // 16:16 far pointer to 64 bit unsigned
    # T_PHUQUAD       = 0x0323,   // 16:16 huge pointer to 64 bit unsigned
    0x0423: BasicType("T_32PUQUAD", 4, is_ptr=True, utype=0x23),
    # T_32PFUQUAD     = 0x0523,   // 16:32 pointer to 64 bit unsigned
    # T_64PUQUAD      = 0x0623,   // 64 bit pointer to 64 bit unsigned

    # T_PINT8         = 0x0176,   // 16 bit pointer to 64 bit signed int
    # T_PFINT8        = 0x0276,   // 16:16 far pointer to 64 bit signed int
    # T_PHINT8        = 0x0376,   // 16:16 huge pointer to 64 bit signed int
    # T_32PINT8       = 0x0476,   // 32 bit pointer to 64 bit signed int
    # T_32PFINT8      = 0x0576,   // 16:32 pointer to 64 bit signed int
    # T_64PINT8       = 0x0676,   // 64 bit pointer to 64 bit signed int

    # T_PUINT8        = 0x0177,   // 16 bit pointer to 64 bit unsigned int
    # T_PFUINT8       = 0x0277,   // 16:16 far pointer to 64 bit unsigned int
    # T_PHUINT8       = 0x0377,   // 16:16 huge pointer to 64 bit unsigned int
    # T_32PUINT8      = 0x0477,   // 32 bit pointer to 64 bit unsigned int
    # T_32PFUINT8     = 0x0577,   // 16:32 pointer to 64 bit unsigned int
    # T_64PUINT8      = 0x0677,   // 64 bit pointer to 64 bit unsigned int

    # T_POCT          = 0x0114,   // 16 bit pointer to 128 bit signed
    # T_PFOCT         = 0x0214,   // 16:16 far pointer to 128 bit signed
    # T_PHOCT         = 0x0314,   // 16:16 huge pointer to 128 bit signed
    # T_32POCT        = 0x0414,   // 32 bit pointer to 128 bit signed
    # T_32PFOCT       = 0x0514,   // 16:32 pointer to 128 bit signed
    # T_64POCT        = 0x0614,   // 64 bit pointer to 128 bit signed

    # T_PUOCT         = 0x0124,   // 16 bit pointer to 128 bit unsigned
    # T_PFUOCT        = 0x0224,   // 16:16 far pointer to 128 bit unsigned
    # T_PHUOCT        = 0x0324,   // 16:16 huge pointer to 128 bit unsigned
    # T_32PUOCT       = 0x0424,   // 32 bit pointer to 128 bit unsigned
    # T_32PFUOCT      = 0x0524,   // 16:32 pointer to 128 bit unsigned
    # T_64PUOCT       = 0x0624,   // 64 bit pointer to 128 bit unsigned

    # T_PINT16        = 0x0178,   // 16 bit pointer to 128 bit signed int
    # T_PFINT16       = 0x0278,   // 16:16 far pointer to 128 bit signed int
    # T_PHINT16       = 0x0378,   // 16:16 huge pointer to 128 bit signed int
    # T_32PINT16      = 0x0478,   // 32 bit pointer to 128 bit signed int
    # T_32PFINT16     = 0x0578,   // 16:32 pointer to 128 bit signed int
    # T_64PINT16      = 0x0678,   // 64 bit pointer to 128 bit signed int

    # T_PUINT16       = 0x0179,   // 16 bit pointer to 128 bit unsigned int
    # T_PFUINT16      = 0x0279,   // 16:16 far pointer to 128 bit unsigned int
    # T_PHUINT16      = 0x0379,   // 16:16 huge pointer to 128 bit unsigned int
    # T_32PUINT16     = 0x0479,   // 32 bit pointer to 128 bit unsigned int
    # T_32PFUINT16    = 0x0579,   // 16:32 pointer to 128 bit unsigned int
    # T_64PUINT16     = 0x0679,   // 64 bit pointer to 128 bit unsigned int

    # T_PREAL16       = 0x0146,   // 16 bit pointer to 16 bit real
    # T_PFREAL16      = 0x0246,   // 16:16 far pointer to 16 bit real
    # T_PHREAL16      = 0x0346,   // 16:16 huge pointer to 16 bit real
    # T_32PREAL16     = 0x0446,   // 32 bit pointer to 16 bit real
    # T_32PFREAL16    = 0x0546,   // 16:32 pointer to 16 bit real
    # T_64PREAL16     = 0x0646,   // 64 bit pointer to 16 bit real

    # T_PREAL32       = 0x0140,   // 16 bit pointer to 32 bit real
    # T_PFREAL32      = 0x0240,   // 16:16 far pointer to 32 bit real
    # T_PHREAL32      = 0x0340,   // 16:16 huge pointer to 32 bit real
    0x0440: BasicType("T_32PREAL32", 4, is_ptr=True, utype=0x40),
    # T_32PFREAL32    = 0x0540,   // 16:32 pointer to 32 bit real
    # T_64PREAL32     = 0x0640,   // 64 bit pointer to 32 bit real

    # T_PREAL32PP     = 0x0145,   // 16 bit pointer to 32 bit PP real
    # T_PFREAL32PP    = 0x0245,   // 16:16 far pointer to 32 bit PP real
    # T_PHREAL32PP    = 0x0345,   // 16:16 huge pointer to 32 bit PP real
    # T_32PREAL32PP   = 0x0445,   // 32 bit pointer to 32 bit PP real
    # T_32PFREAL32PP  = 0x0545,   // 16:32 pointer to 32 bit PP real
    # T_64PREAL32PP   = 0x0645,   // 64 bit pointer to 32 bit PP real

    # T_PREAL48       = 0x0144,   // 16 bit pointer to 48 bit real
    # T_PFREAL48      = 0x0244,   // 16:16 far pointer to 48 bit real
    # T_PHREAL48      = 0x0344,   // 16:16 huge pointer to 48 bit real
    # T_32PREAL48     = 0x0444,   // 32 bit pointer to 48 bit real
    # T_32PFREAL48    = 0x0544,   // 16:32 pointer to 48 bit real
    # T_64PREAL48     = 0x0644,   // 64 bit pointer to 48 bit real

    # T_PREAL64       = 0x0141,   // 16 bit pointer to 64 bit real
    # T_PFREAL64      = 0x0241,   // 16:16 far pointer to 64 bit real
    # T_PHREAL64      = 0x0341,   // 16:16 huge pointer to 64 bit real
    0x0441: BasicType("T_32PREAL64", 4, is_ptr=True, utype=0x41),
    # T_32PFREAL64    = 0x0541,   // 16:32 pointer to 64 bit real
    # T_64PREAL64     = 0x0641,   // 64 bit pointer to 64 bit real

    # T_PREAL80       = 0x0142,   // 16 bit pointer to 80 bit real
    # T_PFREAL80      = 0x0242,   // 16:16 far pointer to 80 bit real
    # T_PHREAL80      = 0x0342,   // 16:16 huge pointer to 80 bit real
    # T_32PREAL80     = 0x0442,   // 32 bit pointer to 80 bit real
    # T_32PFREAL80    = 0x0542,   // 16:32 pointer to 80 bit real
    # T_64PREAL80     = 0x0642,   // 64 bit pointer to 80 bit real

    # T_PREAL128      = 0x0143,   // 16 bit pointer to 128 bit real
    # T_PFREAL128     = 0x0243,   // 16:16 far pointer to 128 bit real
    # T_PHREAL128     = 0x0343,   // 16:16 huge pointer to 128 bit real
    # T_32PREAL128    = 0x0443,   // 32 bit pointer to 128 bit real
    # T_32PFREAL128   = 0x0543,   // 16:32 pointer to 128 bit real
    # T_64PREAL128    = 0x0643,   // 64 bit pointer to 128 bit real

    # T_PCPLX32       = 0x0150,   // 16 bit pointer to 32 bit complex
    # T_PFCPLX32      = 0x0250,   // 16:16 far pointer to 32 bit complex
    # T_PHCPLX32      = 0x0350,   // 16:16 huge pointer to 32 bit complex
    # T_32PCPLX32     = 0x0450,   // 32 bit pointer to 32 bit complex
    # T_32PFCPLX32    = 0x0550,   // 16:32 pointer to 32 bit complex
    # T_64PCPLX32     = 0x0650,   // 64 bit pointer to 32 bit complex

    # T_PCPLX64       = 0x0151,   // 16 bit pointer to 64 bit complex
    # T_PFCPLX64      = 0x0251,   // 16:16 far pointer to 64 bit complex
    # T_PHCPLX64      = 0x0351,   // 16:16 huge pointer to 64 bit complex
    # T_32PCPLX64     = 0x0451,   // 32 bit pointer to 64 bit complex
    # T_32PFCPLX64    = 0x0551,   // 16:32 pointer to 64 bit complex
    # T_64PCPLX64     = 0x0651,   // 64 bit pointer to 64 bit complex

    # T_PCPLX80       = 0x0152,   // 16 bit pointer to 80 bit complex
    # T_PFCPLX80      = 0x0252,   // 16:16 far pointer to 80 bit complex
    # T_PHCPLX80      = 0x0352,   // 16:16 huge pointer to 80 bit complex
    # T_32PCPLX80     = 0x0452,   // 32 bit pointer to 80 bit complex
    # T_32PFCPLX80    = 0x0552,   // 16:32 pointer to 80 bit complex
    # T_64PCPLX80     = 0x0652,   // 64 bit pointer to 80 bit complex

    # T_PCPLX128      = 0x0153,   // 16 bit pointer to 128 bit complex
    # T_PFCPLX128     = 0x0253,   // 16:16 far pointer to 128 bit complex
    # T_PHCPLX128     = 0x0353,   // 16:16 huge pointer to 128 bit real
    # T_32PCPLX128    = 0x0453,   // 32 bit pointer to 128 bit complex
    # T_32PFCPLX128   = 0x0553,   // 16:32 pointer to 128 bit complex
    # T_64PCPLX128    = 0x0653,   // 64 bit pointer to 128 bit complex


    # T_PBOOL08       = 0x0130,   // 16 bit pointer to  8 bit boolean
    # T_PFBOOL08      = 0x0230,   // 16:16 far pointer to  8 bit boolean
    # T_PHBOOL08      = 0x0330,   // 16:16 huge pointer to  8 bit boolean
    0x0430: BasicType("T_32PBOOL08", 4, is_ptr=True, utype=0x30),
    # T_32PFBOOL08    = 0x0530,   // 16:32 pointer to 8 bit boolean
    # T_64PBOOL08     = 0x0630,   // 64 bit pointer to 8 bit boolean

    # T_PBOOL16       = 0x0131,   // 16 bit pointer to 16 bit boolean
    # T_PFBOOL16      = 0x0231,   // 16:16 far pointer to 16 bit boolean
    # T_PHBOOL16      = 0x0331,   // 16:16 huge pointer to 16 bit boolean
    # T_32PBOOL16     = 0x0431,   // 32 bit pointer to 18 bit boolean
    # T_32PFBOOL16    = 0x0531,   // 16:32 pointer to 16 bit boolean
    # T_64PBOOL16     = 0x0631,   // 64 bit pointer to 18 bit boolean

    # T_PBOOL32       = 0x0132,   // 16 bit pointer to 32 bit boolean
    # T_PFBOOL32      = 0x0232,   // 16:16 far pointer to 32 bit boolean
    # T_PHBOOL32      = 0x0332,   // 16:16 huge pointer to 32 bit boolean
    # T_32PBOOL32     = 0x0432,   // 32 bit pointer to 32 bit boolean
    # T_32PFBOOL32    = 0x0532,   // 16:32 pointer to 32 bit boolean
    # T_64PBOOL32     = 0x0632,   // 64 bit pointer to 32 bit boolean

    # T_PBOOL64       = 0x0133,   // 16 bit pointer to 64 bit boolean
    # T_PFBOOL64      = 0x0233,   // 16:16 far pointer to 64 bit boolean
    # T_PHBOOL64      = 0x0333,   // 16:16 huge pointer to 64 bit boolean
    # T_32PBOOL64     = 0x0433,   // 32 bit pointer to 64 bit boolean
    # T_32PFBOOL64    = 0x0533,   // 16:32 pointer to 64 bit boolean
    # T_64PBOOL64     = 0x0633,   // 64 bit pointer to 64 bit boolean

    # T_NCVPTR        = 0x01f0,   // CV Internal type for created near pointers
    # T_FCVPTR        = 0x02f0,   // CV Internal type for created far pointers
    # T_HCVPTR        = 0x03f0,   // CV Internal type for created huge pointers
    # T_32NCVPTR      = 0x04f0,   // CV Internal type for created near 32-bit pointers
    # T_32FCVPTR      = 0x05f0,   // CV Internal type for created far 32-bit pointers
    # T_64NCVPTR      = 0x06f0,   // CV Internal type for created near 64-bit pointers

    # T_64PHRESULT    = 0x0608,   // OLE/COM HRESULT __ptr64 *
})


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
# to speed up a little bit, reduce the fields need to be parsed
sFieldAttr = Int16ul

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
            "LF_STMEMBER": Struct(
                "attr" / sFieldAttr,
                "index" / Int32ul,
                "name" / CString(encoding = "utf8"),
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
# to speed up a little bit, reduce the fields need to be parsed
sCvProperty = BitStruct(
    "fwdref" / Flag,
    "reserved" / BitsInteger(15),
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

_PtrAttr = BitStruct(
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
)
# to speed up a little bit, reduce the fields need to be parsed
_PtrAttr = Int32ul

lfPointer = Struct(
    "utype" / Int32ul,
    "ptr_attr" / _PtrAttr,
)

lfProcedure = Struct(
    "rvtype" / IntIndex,
    "calltype" / Int8ub,
    "funcattr" / Int8ub,
    "parmcount" / Int16ul, # number of parameters
    "arglist" / IntIndex,
)

lfArgList = Struct(
    "count" / Int32ul,
    "args" / Array(lambda ctx: ctx.count, IntIndex)
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
                "LF_CLASS": lfStructure,
                "LF_STRUCTURE": lfStructure,
                "LF_STRUCTURE_ST": lfStructureST,
                "LF_UNION": lfUnion,
                "LF_UNION_ST": lfUnionST,
                "LF_POINTER": lfPointer,
                "LF_PROCEDURE": lfProcedure,
                "LF_ARGLIST": lfArgList,
            },
            default = Pass,
        ),
    ),
)


def parse(data: int, count: int) -> list[Struct]:
    arr = Array(count, sTypType)
    return arr.parse(data)


def flatten_leaf_data(lf):
    """ insert leafKind to data attribute, and return attribute as a new leaf """
    if lf.data is None:
        lf.data = Container()
    lf.data.leafKind = lf.leafKind
    return lf.data

