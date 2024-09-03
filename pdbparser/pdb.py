from . import gdata
import io
import struct
import itertools
from collections import deque
from pathlib import Path
from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from functools import cached_property
from io import BytesIO
from typing import Callable, Self, TypedDict

from construct import Array
from construct import Bytes
from construct import BitStruct
from construct import Const
from construct import Container
from construct import CString
from construct import Enum
from construct import Flag
from construct import GreedyRange
from construct import Int8ul
from construct import Int16sl
from construct import Int16ul
from construct import Int32ul
from construct import Int32sl
from construct import Padding
from construct import Struct

from . import tpi
from . import dbi

_strarray = "names" / GreedyRange(CString(encoding="utf8"))


# ref: https://llvm.org/docs/PDB/MsfFile.html#file-layout
# ref: https://auscitte.github.io/posts/Func-Prototypes-With-Pdbparse

_PDB7_SIGNATURE = b"Microsoft C/C++ MSF 7.00\r\n\x1aDS\0\0\0"

StructPdbHeader = Struct(
    "signature" / Bytes(len(_PDB7_SIGNATURE)),
    "blockSize" / Int32ul,
    "freeBlockMapCount" / Int32ul,
    "numBlocks" / Int32ul,
    "numDirectoryBytes" / Int32ul,
    "Unknown" / Int32ul,
    # pointer array to each Stream Directory
    "BlockMapAddr" / Int32ul,
)


@dataclass
class Stream:
    byte_sz: int
    page_sz: int
    pages: list[int]
    _sHeader: Struct = field(default_factory=Struct)

    def getdata(self, fp) -> bytes:
        data = BytesIO()
        for p in self.pages:
            fp.seek(p * self.page_sz)
            data.write(fp.read(self.page_sz))
        return data.getbuffer()

    def getbodydata(self, fp) -> bytes:
        hdr_cls = getattr(self.__class__, "_sHeader", self._sHeader)
        hdr_offset = hdr_cls.sizeof()
        return bytes(self.getdata(fp)[hdr_offset:])

    def load_header(self, fp):
        data = self.getdata(fp)
        hdr_cls = getattr(self.__class__, "_sHeader", self._sHeader)
        self.header = hdr_cls.parse(data)

    def load_body(self, bdata):
        """heavy loading operations goes here"""


class OldDirectory(Stream): ...


class PdbStream(Stream):
    _sHeader = Struct(
        "version" / Int32ul,
        "signature" / Int32ul,
        "age" / Int32ul,
        "guid" / Bytes(16),
        "charCnt" / Int32ul,
    )

    def load_data(self, fp):
        self.timestamp = datetime.fromtimestamp(self.header.signature)

        data = self.getbodydata(fp)
        self.strings = _strarray.parse(data[: self.header.charCnt])


class StructRecord(TypedDict):
    levelname: str
    value: int | None
    type: str
    address: int
    size: int
    bitoff: int | None
    bitsize: int | None
    fields: list[Self] | dict[str, Self] | None
    is_pointer: bool
    is_real: bool
    has_sign: bool
    lf: Struct | None


def new_struct(**kwargs):
    s = StructRecord(
        levelname="",
        value=None,
        type="",
        address=0,
        size=0,
        bitoff=None,
        bitsize=None,
        fields=None,
        is_pointer=False,
        is_real=False,
        has_sign=False,
        lf=None,
    )
    s.update(**kwargs)
    return s


class TpiStream(Stream):
    _sHeader = Struct(
        "version" / Int32ul,
        "headerSize" / Int32ul,
        "typeIndexBegin" / Int32ul,
        "typeIndexEnd" / Int32ul,
        "typeRecordBytes" / Int32ul,
        "sn" / Int16ul,
        Padding(2),
        "hashKey" / Int32ul,
        "numHashBuckets" / Int32ul,
        "hashValueBufferOffset" / Int32ul,
        "hashValueBufferLength" / Int32ul,
        "indexOffsetBufferOffset" / Int32ul,
        "indexOffsetBufferLength" / Int32ul,
        "hashAdjBufferOffset" / Int32ul,
        "hashAdjBufferLength" / Int32ul,
    )

    @cached_property
    def structs(self) -> dict[str, StructRecord]:
        """return dict of {structname: idx}"""
        types = getattr(self, "_types", {})
        return {
            t.name: t
            for t in types.values()
            if t.leafKind
            in {
                tpi.eLeafKind.LF_CLASS,
                tpi.eLeafKind.LF_STRUCTURE,
                tpi.eLeafKind.LF_STRUCTURE_ST,
                tpi.eLeafKind.LF_UNION,
                tpi.eLeafKind.LF_UNION_ST,
            }
        }

    def get_lf_from_tid(self, ref: int):
        if ref < self.header.typeIndexBegin:
            try:
                return tpi.eBaseTypes[ref]
            except KeyError:
                print("Unknown Base Type %s" % hex(ref))
                raise KeyError(ref)
        elif ref >= self.header.typeIndexBegin:
            return self._types[ref]

    def get_lf_from_name(self, ref: str):
        for lf in tpi.eBaseTypes.values():
            if lf.name == ref:
                return lf
        return self.structs[ref]

    def _foward_refs(self, lf, fwdref_map, inside_fields: bool = False):
        ref_fields = tpi.FieldsRefAttrs if inside_fields else tpi.TypRefAttrs

        def get_ref(ref: int):
            if ref < self.header.typeIndexBegin:
                return fwdref_map[ref]
            elif ref >= self.header.typeIndexBegin:
                return fwdref_map[ref]

        for attr in ref_fields.get(lf.leafKind, []):
            ref = lf[attr]
            if isinstance(ref, int):
                with suppress(KeyError):
                    setattr(lf, attr, get_ref(ref))
            elif isinstance(ref, list):
                for i, x in enumerate(ref):
                    if isinstance(x, int):
                        with suppress(KeyError):
                            ref[i] = get_ref(x)
                    else:
                        raise NotImplementedError(ref)

    def load_body(self, bdata):
        types = tpi.parse(bdata, self.header.typeIndexEnd - self.header.typeIndexBegin)
        type_dict = {}
        for idx, t in zip(
            range(self.header.typeIndexBegin, self.header.typeIndexEnd),
            types,
        ):
            new_t = tpi.flatten_leaf_data(t)
            if new_t.leafKind is tpi.eLeafKind.LF_FIELDLIST:
                for i, f in enumerate(new_t.fields):
                    new_t.fields[i] = tpi.flatten_leaf_data(f)
            type_dict[idx] = new_t

        # fix values
        for t in type_dict.values():
            if t.leafKind is tpi.eLeafKind.LF_FIELDLIST:
                for f in t.fields:
                    tpi.insert_field_of_raw(f)
            else:
                tpi.insert_field_of_raw(t)
        self._types = type_dict

        ## eliminate fwdrefs
        # Get list of fwdrefs
        fwdrefs = {
            t.name: idx
            for idx, t in type_dict.items()
            if hasattr(t, "property") and t.property.fwdref
        }
        # Map them to the real type
        fwdrefs_map = {
            fwdrefs[t.name]: idx
            for idx, t in type_dict.items()
            if hasattr(t, "name")
            and hasattr(t, "property")
            and not t.property.fwdref
            and t.name in fwdrefs
        }
        # resolve fields
        for t in type_dict.values():
            if t.leafKind is tpi.eLeafKind.LF_FIELDLIST:
                for f in t.fields:
                    self._foward_refs(f, fwdrefs_map, inside_fields=True)
            else:
                self._foward_refs(t, fwdrefs_map, inside_fields=False)
        # Get rid of the resolved fwdrefs
        for k in fwdrefs_map.keys():
            del type_dict[k]

    ARCH_PTR_SIZE = 4

    def get_lf_size(self, lf):
        if isinstance(lf, tpi.BasicType):
            return lf.size
        elif lf.leafKind in {
            tpi.eLeafKind.LF_CLASS,
            tpi.eLeafKind.LF_STRUCTURE,
            tpi.eLeafKind.LF_STRUCTURE_ST,
            tpi.eLeafKind.LF_UNION,
            tpi.eLeafKind.LF_UNION_ST,
            tpi.eLeafKind.LF_ARRAY,
        }:
            return lf.size
        elif lf.leafKind == tpi.eLeafKind.LF_POINTER:
            return self.ARCH_PTR_SIZE
        elif lf.leafKind == tpi.eLeafKind.LF_ENUM:
            return 4  # FIXME not sure ??
        elif lf.leafKind == tpi.eLeafKind.LF_BITFIELD:
            return self.get_lf_from_tid(lf.baseType).size
        elif lf.leafKind == tpi.eLeafKind.LF_MODIFIER:
            return self.get_lf_size(lf.modifiedType)
        else:
            return -1

    def get_lf_tpname(self, lf):
        """return type string"""
        if isinstance(lf, tpi.BasicType):
            return str(lf)
        elif lf.leafKind in {
            tpi.eLeafKind.LF_CLASS,
            tpi.eLeafKind.LF_STRUCTURE,
            tpi.eLeafKind.LF_STRUCTURE_ST,
            tpi.eLeafKind.LF_UNION,
            tpi.eLeafKind.LF_UNION_ST,
        }:
            return lf.name
        elif lf.leafKind == tpi.eLeafKind.LF_POINTER:
            ref = self.get_lf_from_tid(lf.utype)
            if ref.leafKind == tpi.eLeafKind.LF_PROCEDURE:
                return self.get_lf_tpname(ref)
            return "%s *" % self.get_lf_tpname(ref)
        elif lf.leafKind == tpi.eLeafKind.LF_ENUM:
            return str(lf.leafKind)
        elif lf.leafKind == tpi.eLeafKind.LF_PROCEDURE:
            rtntype = self.get_lf_tpname(self.get_lf_from_tid(lf.rvtype))
            args = [
                self.get_lf_tpname(self.get_lf_from_tid(x))
                for x in self.get_lf_from_tid(lf.arglist).args
            ]
            return "%s (*)(%s)" % (rtntype, ", ".join(args))
        elif lf.leafKind == tpi.eLeafKind.LF_MODIFIER:
            tpname = self.get_lf_tpname(self.get_lf_from_tid(lf.modifiedType))
            modifiers = [
                m for m in ["const", "unaligned", "volatile"] if lf.modifier[m]
            ]
            return "%s %s" % (" ".join(modifiers), tpname)
        elif lf.leafKind == tpi.eLeafKind.LF_ARRAY:
            dims = deque()
            item_lf = lf
            item_size = self.get_lf_size(item_lf)
            while getattr(item_lf, "leafKind", None) == tpi.eLeafKind.LF_ARRAY:
                next_dim_lf = self.get_lf_from_tid(item_lf.elemType)
                dims.append(item_size // self.get_lf_size(next_dim_lf))
                item_lf = next_dim_lf
            structname = self.get_lf_tpname(item_lf)
            if structname.endswith("*"):
                return "(%s)%s" % (structname, "".join(["[%d]" % d for d in dims]))
            else:
                return "%s%s" % (structname, "".join(["[%d]" % d for d in dims]))
        elif lf.leafKind == tpi.eLeafKind.LF_BITFIELD:
            return str(lf.leafKind)
        else:
            return str(lf.leafKind)

    def deref_pointer(self, lf, addr, recursive=True) -> StructRecord:
        if not hasattr(lf, "utype"):
            raise ValueError("Shall be a pointer type, got: %r" % lf.name)
        try:
            struct = self.get_lf_from_tid(lf.utype)
        except KeyError:
            raise ValueError("Shall be a pointer type, got: %r" % lf.name)
        return self.form_structs(struct, addr, recursive)

    def form_structs(self, lf, addr=0, recursive=True, _depth=0) -> StructRecord:
        if isinstance(lf, tpi.BasicType):
            return new_struct(
                levelname=lf.name,
                type=self.get_lf_tpname(lf),
                address=addr,
                size=self.get_lf_size(lf),
                is_pointer=lf.is_ptr,
                is_real=lf.is_real,
                has_sign=lf.has_sign,
                lf=lf,
            )
        elif lf.leafKind in {
            tpi.eLeafKind.LF_CLASS,
            tpi.eLeafKind.LF_STRUCTURE,
            tpi.eLeafKind.LF_STRUCTURE_ST,
            tpi.eLeafKind.LF_UNION,
            tpi.eLeafKind.LF_UNION_ST,
        }:
            struct = new_struct(
                levelname="",
                type=self.get_lf_tpname(lf),
                address=addr,
                size=self.get_lf_size(lf),
                fields={},
                lf=lf,
            )
            if recursive or _depth == 0:
                for member_lf in self.get_lf_from_tid(lf.fields).fields:
                    mem_struct = self.form_structs(
                        member_lf, addr, recursive, _depth + 1
                    )
                    if mem_struct is None:
                        continue
                    mem_struct["levelname"] = member_lf.name
                    struct["fields"][member_lf.name] = mem_struct
            return struct

        elif lf.leafKind == tpi.eLeafKind.LF_ARRAY:
            elem_lf = self.get_lf_from_tid(lf.elemType)
            elem_size = self.get_lf_size(elem_lf)
            count = self.get_lf_size(lf) // elem_size

            struct = new_struct(
                levelname=lf.name,
                type=self.get_lf_tpname(lf),
                address=addr,
                size=self.get_lf_size(lf),
                fields=[],
                lf=lf,
            )
            if recursive or _depth == 0:
                for i, off in zip(range(count), itertools.count(0, elem_size)):
                    elem_s = self.form_structs(
                        elem_lf, addr + off, recursive, _depth + 1
                    )
                    elem_s["levelname"] = "[%d]" % i
                    struct["fields"].append(elem_s)
            return struct

        elif lf.leafKind == tpi.eLeafKind.LF_MEMBER:
            ref = self.get_lf_from_tid(lf.type)
            struct = self.form_structs(ref, addr + lf.offset, recursive, _depth)
            struct["levelname"] = lf.name
            return struct

        elif lf.leafKind == tpi.eLeafKind.LF_NESTTYPE:
            # # anonymous?
            # struct = self.form_structs(lf.typeRef, address=addr)
            # struct["name"] = lf.name
            # return struct
            return None

        elif lf.leafKind == tpi.eLeafKind.LF_BITFIELD:
            return new_struct(
                levelname="",
                type=self.get_lf_tpname(lf),
                address=addr,
                size=self.get_lf_size(lf),
                bitoff=lf.position,
                bitsize=lf.length,
                lf=lf,
            )

        elif lf.leafKind == tpi.eLeafKind.LF_ENUM:
            return new_struct(
                levelname=lf.name,
                type=self.get_lf_tpname(lf),
                address=addr,
                size=self.get_lf_size(lf),  # ?
                fields=[],  # ?
                lf=lf,
            )

        elif lf.leafKind == tpi.eLeafKind.LF_POINTER:
            ref = self.get_lf_from_tid(lf.utype)
            return new_struct(
                levelname="",
                type=self.get_lf_tpname(lf),
                address=addr,
                size=self.get_lf_size(lf),
                fields=None,
                is_pointer=True,
                is_funcptr=ref.leafKind == tpi.eLeafKind.LF_PROCEDURE,
                lf=lf,
            )

        elif lf.leafKind == tpi.eLeafKind.LF_MODIFIER:
            return self.form_structs(self.get_lf_from_tid(lf.modifiedType))
        else:
            raise NotImplementedError(lf)


def get_parsed_size(tp, con):
    return len(tp.build(con))


class DbiStream(Stream):
    _sHeader = Struct(
        "magic" / Const(b"\xff\xff\xff\xff", Bytes(4)),  # 0
        "version" / Int32ul,  # 4
        "age" / Int32ul,  # 8
        "gssymStream" / Int16sl,  # 12
        "vers" / Int16ul,  # 14
        "pssymStream" / Int16sl,  # 16
        "pdbver" / Int16ul,  # 18
        "symrecStream" / Int16sl,  # stream containing global symbols   # 20
        "pdbver2" / Int16ul,  # 22
        "module_size" / Int32ul,  # total size of DBIExHeaders            # 24
        "secconSize" / Int32ul,  # 28
        "secmapSize" / Int32ul,  # 32
        "filinfSize" / Int32ul,  # 36
        "tsmapSize" / Int32ul,  # 40
        "mfcIndex" / Int32ul,  # 44
        "dbghdrSize" / Int32ul,  # 48
        "ecinfoSize" / Int32ul,  # 52
        "flags" / Int16ul,  # 56
        "Machine"
        / Enum(
            Int16ul,  # 58
            IMAGE_FILE_MACHINE_UNKNOWN=0x0000,
            IMAGE_FILE_MACHINE_I386=0x014C,
            IMAGE_FILE_MACHINE_R3000=0x0162,
            IMAGE_FILE_MACHINE_R4000=0x0166,
            IMAGE_FILE_MACHINE_R10000=0x0168,
            IMAGE_FILE_MACHINE_WCEMIPSV2=0x0169,
            IMAGE_FILE_MACHINE_ALPHA=0x0184,
            IMAGE_FILE_MACHINE_SH3=0x01A2,
            IMAGE_FILE_MACHINE_SH3DSP=0x01A3,
            IMAGE_FILE_MACHINE_SH3E=0x01A4,
            IMAGE_FILE_MACHINE_SH4=0x01A6,
            IMAGE_FILE_MACHINE_SH5=0x01A8,
            IMAGE_FILE_MACHINE_ARM=0x01C0,
            IMAGE_FILE_MACHINE_THUMB=0x01C2,
            IMAGE_FILE_MACHINE_ARMNT=0x01C4,
            IMAGE_FILE_MACHINE_AM33=0x01D3,
            IMAGE_FILE_MACHINE_POWERPC=0x01F0,
            IMAGE_FILE_MACHINE_POWERPCFP=0x01F1,
            IMAGE_FILE_MACHINE_IA64=0x0200,
            IMAGE_FILE_MACHINE_MIPS16=0x0266,
            IMAGE_FILE_MACHINE_ALPHA64=0x0284,
            IMAGE_FILE_MACHINE_AXP64=0x0284,
            IMAGE_FILE_MACHINE_MIPSFPU=0x0366,
            IMAGE_FILE_MACHINE_MIPSFPU16=0x0466,
            IMAGE_FILE_MACHINE_TRICORE=0x0520,
            IMAGE_FILE_MACHINE_CEF=0x0CEF,
            IMAGE_FILE_MACHINE_EBC=0x0EBC,
            IMAGE_FILE_MACHINE_AMD64=0x8664,
            IMAGE_FILE_MACHINE_M32R=0x9041,
            IMAGE_FILE_MACHINE_CEE=0xC0EE,
        ),
        "resvd" / Int32ul,  # 60
    )

    # struct MODI
    _DbiExHeader = Struct(
        "pmod" / Int32ul,  # currently open mod
        "sc"
        / Struct(
            "isect" / Int16sl,  # index of Section
            Padding(2),
            "off" / Int32sl,
            "size" / Int32sl,
            "dwCharacteristics" / Int32ul,
            "imod" / Int16sl,  # index of module
            Padding(2),
            "dwDataCrc" / Int32ul,
            "dwRelocCrc" / Int32ul,
        ),
        "f"
        / BitStruct(
            "Written" / Flag,
            "ECEnabled" / Flag,
            Padding(6),
        ),
        "iTSM" / Int8ul,
        "sn" / Int16sl,  # stream number
        "symSize" / Int32ul,  # cbSyms
        "oldLineSize" / Int32ul,  # cbLines
        "lineSize" / Int32ul,  # cbC13Lines
        "nSrcFiles" / Int16sl,  # ifileMac
        Padding(2),
        # array [0..ifileMac) of offsets into dbi.bufFilenames
        "mpifileichFile" / Int32ul,
        "niSrcFile" / Int32ul,  # name index for src file
        "niPdbFile" / Int32ul,  # name index for compiler PDB
        "modName" / CString(encoding="utf8"),  # szModule
        "objName" / CString(encoding="utf8"),  # szObjFile
    )

    _DbiDbgHeader = Struct(
        "snFPO" / Int16sl,
        "snException" / Int16sl,
        "snFixup" / Int16sl,
        "snOmapToSrc" / Int16sl,
        "snOmapFromSrc" / Int16sl,
        "snSectionHdr" / Int16sl,
        "snTokenRidMap" / Int16sl,
        "snXdata" / Int16sl,
        "snPdata" / Int16sl,
        "snNewFPO" / Int16sl,
        "snSectionHdrOrig" / Int16sl,
    )

    def load_header(self, fp):
        super().load_header(fp)

        bdata = self.getbodydata(fp)

        dbiexhdrs = deque()
        dbiexhdr_data = bdata[: self.header.module_size]
        _ALIGN = 4
        while dbiexhdr_data:
            h = self._DbiExHeader.parse(dbiexhdr_data)
            dbiexhdrs.append(h)
            # sizeof() is broken on CStrings for construct, so
            # this ugly ugly hack is necessary
            sz = get_parsed_size(self._DbiExHeader, h)
            if sz % _ALIGN != 0:
                sz = sz + (_ALIGN - (sz % _ALIGN))
            dbiexhdr_data = dbiexhdr_data[sz:]
        self.exheaders = dbiexhdrs
        pdb_folder = str(Path(fp.name).parent)
        self.mymod_indexes = [i for i, h in enumerate(dbiexhdrs) if h.objName.startswith(pdb_folder)]

        pos = (
            self.header.module_size
            + self.header.secconSize
            + self.header.secmapSize
            + self.header.filinfSize
            + self.header.tsmapSize
            + self.header.ecinfoSize
        )
        self.dbgheader = self._DbiDbgHeader.parse(bdata[pos:])


class DbiModule(Stream):
    _sHeader = Struct(
        "unknown" / Int32ul,  # 4
    )
    def load_header(self, fp):
        super().load_header(fp)
        self.symbols = []

    def load_body(self, bdata):
        types = dbi.parse(bdata)
        _flattern_types = [tpi.flatten_leaf_data(t) for t in types]
        _named_syms = [t for t in _flattern_types if hasattr(t, "name")]
        self.symbols = [s for s in _named_syms if not s.name.startswith("std::")]


class GlobalSymbolStream(Stream):
    def load_body(self, bdata):
        # data = self.getbodydata(fp)
        globalsymbols = gdata.parse(bdata)
        # skip standard lib, since there is usually no need to debug them
        my_symbols = [s for s in globalsymbols if not getattr(s, "name", "").startswith("std::")]
        for g in my_symbols:
            if isinstance(g.leafKind, int):
                kind = "s_unknown"
                try:
                    d = getattr(self, kind)
                except AttributeError:
                    d = []
                    setattr(self, kind, d)
                d.append(g)
            else:
                kind = str(g.leafKind)
                try:
                    d = getattr(self, kind.lower())
                except AttributeError:
                    d = []
                    setattr(self, kind.lower(), d)
                try:
                    d.append(g)
                except AttributeError:
                    breakpoint()

    @cached_property
    def symbols(self) -> dict[gdata.DATASYM32]:
        syms = {}
        for attr in ("s_gdata32", "s_ldata32"):
            for v in getattr(self, attr, []):
                # there will be multiple Leaf
                # with same v.name buf different v.offset
                # I don't know what they stand for, though.
                # Using the last one seems just work for mapping address usage
                # so here I simply override the old one temporarily.
                syms[v.name] = v
        return syms

    @cached_property
    def refsymbols(self) -> dict[gdata.REFSYM2]:
        syms = {}
        for attr in ("s_procref", "s_lprocref"):
            for v in getattr(self, attr, []):
                # there will be multiple Leaf
                # with same v.name buf different v.ibSym (kind of offset)
                # I don't know what they stand for, though.
                # Using the last one seems just work for imod mapping
                # so here I simply override the old one temporarily.
                syms[v.name] = v
        return syms

    @cached_property
    def user_defines(self) -> dict[gdata.UDT]:
        syms = {}
        for v in getattr(self, "s_udt", []):
            syms[v.name] = v
        return syms

    def get_gvar_info(self, ref: str) -> Struct | None:
        return self.symbols.get(ref, None)

    def get_proc_info(self, ref: str) -> Struct | None:
        return self.refsymbols.get(ref, None)

    def get_user_define_typeid(self, ref: str) -> int | None:
        try:
            return self.user_defines[ref].typind
        except AttributeError:
            return None
        except KeyError:
            return None


class SectionStream(Stream):
    def load_body(self, bdata):
        from . import pe

        self.sections = pe.Sections.parse(bdata)


class OmapStream(Stream):
    def load(self):
        from . import omap

        self.omap_data = omap.Omap(self.data)

    def remap(self, addr):
        return self.omap_data.remap(addr)


STREAM_CLASSES = {
    # fix index
    0: OldDirectory,
    1: PdbStream,
    2: TpiStream,
    3: DbiStream,
    # additional streams will be added dynamically
}

U32_SZ = 4


def div_ceil(x, y):
    return (x + y - 1) // y


class DummyOmap:
    def remap(self, addr):
        return addr


class PDB7:
    def __init__(self, fp):
        fp.seek(0)
        pdb_hdr_data = fp.read(StructPdbHeader.sizeof())
        pdb_hdr = StructPdbHeader.parse(pdb_hdr_data)
        self.header = pdb_hdr

        if pdb_hdr.signature != _PDB7_SIGNATURE:
            raise ValueError("Invalid signature for PDB version 7")

        """
        struct {
            uint32 numDirectoryBytes;
            uint32 blockSizes[numDirectoryBytes];
            uint32 blocks[numDirectoryBytes][];
        }
        """
        stream_dirs_pg_cnt = div_ceil(pdb_hdr.numDirectoryBytes, pdb_hdr.blockSize)
        fp.seek(pdb_hdr.BlockMapAddr * pdb_hdr.blockSize)
        root_dir_indice = struct.unpack(
            "<" + ("%dI" % stream_dirs_pg_cnt), fp.read(stream_dirs_pg_cnt * U32_SZ)
        )

        root_pages_data = io.BytesIO()
        for ind in root_dir_indice:
            fp.seek(ind * pdb_hdr.blockSize)
            root_pages_data.write(fp.read(pdb_hdr.blockSize))
        root_pages_data.seek(0)

        """""" """""" """"""

        (num_streams,) = struct.unpack("<I", root_pages_data.read(U32_SZ))
        streamSizes = struct.unpack(
            "<" + ("%sI" % num_streams), root_pages_data.read(num_streams * U32_SZ)
        )

        _streams = []
        for id, stream_sz in enumerate(streamSizes):
            # Seen in some recent symbols. Not sure what the difference between this
            # and stream_size == 0 is.
            if stream_sz == 0xFFFFFFFF:
                stream_sz = 0

            stream_pg_cnt = div_ceil(stream_sz, pdb_hdr.blockSize)
            stream_pages = list(
                struct.unpack(
                    "<" + ("%sI" % stream_pg_cnt),
                    root_pages_data.read(stream_pg_cnt * U32_SZ),
                )
            )
            s = STREAM_CLASSES.get(id, Stream)(
                byte_sz=stream_sz, page_sz=pdb_hdr.blockSize, pages=stream_pages
            )
            s.load_header(fp)
            _streams.append(s)

            if id == 3:
                for mod in s.exheaders:
                    STREAM_CLASSES[mod.sn] = DbiModule
                # dbistream contains supported info for other debug streams
                if s.header.symrecStream != -1:
                    STREAM_CLASSES[s.header.symrecStream] = GlobalSymbolStream
                if s.dbgheader.snSectionHdr != -1:
                    STREAM_CLASSES[s.dbgheader.snSectionHdr] = SectionStream
                if s.dbgheader.snSectionHdrOrig != -1:
                    STREAM_CLASSES[s.dbgheader.snSectionHdrOrig] = SectionStream
                if s.dbgheader.snOmapToSrc != -1:
                    STREAM_CLASSES[s.dbgheader.snOmapToSrc] = OmapStream
                if s.dbgheader.snOmapFromSrc != -1:
                    STREAM_CLASSES[s.dbgheader.snOmapFromSrc] = OmapStream

        for i, s in enumerate(_streams):
            if isinstance(s, DbiModule):
                continue
            s.load_body(s.getbodydata(fp))

        dbs = _streams[3]
        for mod in dbs.mymod_indexes:
            header = dbs.exheaders[mod]
            s = _streams[header.sn]
            s.load_body(s.getbodydata(fp))

        self.streams = _streams
        # self._addrmap_cache = {}

        # sets global ARCH_PTR_SIZE
        if dbs.header.Machine in ('IMAGE_FILE_MACHINE_I386'):
            # print("// Architecture pointer width 4 bytes")
            self.tpi_stream.ARCH_PTR_SIZE = 4
        elif dbs.header.Machine in ('IMAGE_FILE_MACHINE_AMD64', 'IMAGE_FILE_MACHINE_IA64'):
            # print("// Architecture pointer width 8 bytes")
            self.tpi_stream.ARCH_PTR_SIZE = 8

    @property
    def tpi_stream(self) -> TpiStream:
        return self.streams[2]

    @property
    def glb_stream(self) -> GlobalSymbolStream:
        dbi = self.streams[3]
        return self.streams[dbi.header.symrecStream]

    @cached_property
    def addrress_map(self) -> dict[int, str]:
        """`offset` is without virtual base"""
        map = {}

        var_offset = -1
        remap_fn = self._secoff_to_func()
        for glb_info in self.glb_stream.symbols.values():
            try:
                var_offset = remap_fn(glb_info.section, glb_info.offset)
            except IndexError:
                continue
            map[var_offset] = glb_info.name

        for proc_info in self.glb_stream.refsymbols.values():
            module = self._ximod_to_imod(proc_info.ximod)
            for sym in module.symbols:
                seg = getattr(sym, "seg", None)
                off = getattr(sym, "off", None)
                if seg is None or off is None:
                    continue
                var_offset = remap_fn(seg, off)
                map[var_offset] = sym.name

        return map

    def _secoff_to_func(self) -> Callable[[ int, int ], int]:
        dbi = self.streams[3]
        # remap global address
        try:
            sects = self.streams[dbi.dbgheader.snSectionHdrOrig].sections
            omap = self.streams[dbi.dbgheader.snOmapFromSrc]
        except AttributeError:
            sects = self.streams[dbi.dbgheader.snSectionHdr].sections
            omap = DummyOmap()

        def remap(section: int, offset: int):
            section_offset = sects[section - 1].VirtualAddress
            return omap.remap(section_offset + offset)
        return remap

    def _ximod_to_imod(self, ximod: int) -> DbiModule:
        dbi = self.streams[3]
        return self.streams[dbi.exheaders[ximod - 1].sn]

    def get_refname_from_offset(self, offset: int) -> str | None:
        """`offset` is without virtual base"""
        return self.addrress_map.get(offset, None)

    def _get_glb(self, ref: str):
        glb_info = self.glb_stream.get_gvar_info(ref)
        if glb_info is None:
            return None, 0
        var_offset = self._secoff_to_func()(glb_info.section, glb_info.offset)
        lf = self.tpi_stream.get_lf_from_tid(glb_info.typind)
        return lf, var_offset

    def _get_proc(self, ref: str):
        proc_info = self.glb_stream.get_proc_info(ref)
        if proc_info is None:
            return None, 0
        lf = None
        module = self._ximod_to_imod(proc_info.ximod)
        for sym in module.symbols:
            name = getattr(sym, "name", "")
            if name == ref:
                lf = sym
                break
        if lf:
            var_offset = self._secoff_to_func()(lf.seg, lf.off)
            return lf, var_offset
        else:
            return None, 0

    def _get_udt(self, ref: str):
        udt_id = self.glb_stream.get_user_define_typeid(ref)
        if udt_id is None:
            return None, 0
        lf = self.tpi_stream.get_lf_from_tid(udt_id)
        return lf, 0

    def _get_struct(self, ref: str):
        try:
            lf = self.tpi_stream.get_lf_from_name(ref)
            return lf, 0
        except KeyError:
            return None, 0

    def get_lf_from_name(self, structname: str) -> tuple:
        for test_func in (
            self._get_glb,
            self._get_proc,
            self._get_udt,
            self._get_struct,
        ):
            lf, var_offs = test_func(structname)
            if lf is not None and var_offs is not None:
                return lf, var_offs

        return None, 0


def parse(filename) -> PDB7:
    "Open a PDB file and autodetect its version"
    with open(filename, "rb") as f:
        f.seek(0)
        sig = f.read(len(_PDB7_SIGNATURE))
        if sig == _PDB7_SIGNATURE:
            pdb = PDB7(f)
            pdb.name = filename
            return pdb
        else:
            raise NotImplementedError(sig)
