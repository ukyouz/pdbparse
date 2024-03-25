import io
import struct
from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from functools import cached_property
from io import BytesIO
from typing import Self, TypedDict

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

_strarray = "names" / GreedyRange(CString(encoding = "utf8"))


# ref: https://llvm.org/docs/PDB/MsfFile.html#file-layout
# ref: https://auscitte.github.io/posts/Func-Prototypes-With-Pdbparse

_PDB7_SIGNATURE = b"Microsoft C/C++ MSF 7.00\r\n\x1ADS\0\0\0"

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
        return self.getdata(fp)[hdr_offset:]

    def load_header(self, fp):
        data = self.getdata(fp)
        hdr_cls = getattr(self.__class__, "_sHeader", self._sHeader)
        self.header = hdr_cls.parse(data)

    def load_body(self, fp):
        """ heavy loading operations goes here """


class OldDirectory(Stream):
    ...


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
        """ return dict of {structname: idx} """
        types = getattr(self, "_types", {})
        return {
            t.name: t
            for t in types.values()
            if t.leafKind in {
                tpi.eLeafKind.LF_CLASS,
                tpi.eLeafKind.LF_STRUCTURE,
                tpi.eLeafKind.LF_STRUCTURE_ST,
                tpi.eLeafKind.LF_UNION,
                tpi.eLeafKind.LF_UNION_ST,
            }
        }

    def get_type_lf_from_id(self, ref: int):
        if ref < self.header.typeIndexBegin:
            try:
                return tpi.eBaseTypes[ref]
            except KeyError:
                print("Unknown Base Type %s" % hex(ref))
                raise KeyError
        elif ref >= self.header.typeIndexBegin:
            return self._types[ref]

    def get_type_lf_from_name(self, ref: str):
        for lf in tpi.eBaseTypes.values():
            if lf.name == ref:
                return lf
        return self.structs[ref]

    def _resolve_refs(self, lf, inside_fields: bool=False):
        ref_fields = tpi.FieldsRefAttrs if inside_fields else tpi.TypRefAttrs

        for attr in ref_fields.get(lf.leafKind, []):
            ref = lf[attr]
            if isinstance(ref, int):
                with suppress(KeyError):
                    setattr(lf, attr + "Ref", self.get_type_lf_from_id(ref))
            elif isinstance(ref, list):
                for i, x in enumerate(ref):
                    if isinstance(x, int):
                        with suppress(KeyError):
                            ref[i] = self.get_type_lf_from_id(x)
                    else:
                        raise NotImplementedError(ref)

    def _foward_refs(self, lf, fwdref_map, inside_fields: bool=False):
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

    def load_body(self, fp):
        data = self.getbodydata(fp)
        arr = Array(
            self.header.typeIndexEnd - self.header.typeIndexBegin,
            tpi.sTypType
        )
        types = arr.parse(data)
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
            if hasattr(t, "name") and hasattr(t, "property") and not t.property.fwdref and t.name in fwdrefs
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

        # resolve fields
        for t in type_dict.values():
            if t.leafKind is tpi.eLeafKind.LF_FIELDLIST:
                for f in t.fields:
                    self._resolve_refs(f, inside_fields=True)
            else:
                self._resolve_refs(t, inside_fields=False)

    def deref_pointer(self, lf, addr, recursive=True) -> StructRecord:
        if not hasattr(lf, "utypeRef"):
            raise ValueError("Shall be a pointer type, got: %r" % lf.name)
        struct = lf.utypeRef
        if struct is None:
            raise ValueError("Shall be a pointer type, got: %r" % lf.name)
        return self.form_structs(struct, addr, recursive)

    def form_structs(self, lf, addr=0, recursive=True, _depth=0) -> StructRecord:
        if isinstance(lf, tpi.BasicType):
            return new_struct(
                levelname=lf.name,
                type = tpi.get_tpname(lf),
                address = addr,
                size = tpi.get_size(lf),
                is_pointer=lf.is_ptr,
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
                type=tpi.get_tpname(lf),
                address = addr,
                size = tpi.get_size(lf),
                fields={},
                lf=lf,
            )
            if recursive or _depth == 0:
                for member in lf.fieldsRef.fields:
                    mem_struct = self.form_structs(member, addr, recursive, _depth+1)
                    if mem_struct is None:
                        continue
                    mem_struct["levelname"] = member.name
                    struct["fields"][member.name] = mem_struct
            return struct

        elif lf.leafKind == tpi.eLeafKind.LF_ARRAY:
            count = tpi.get_size(lf) // tpi.get_size(lf.elemTypeRef)

            struct = new_struct(
                levelname = lf.name,
                type = tpi.get_tpname(lf),
                address = addr,
                size = tpi.get_size(lf),
                fields = [],
                lf=lf,
            )
            if recursive or _depth == 0:
                for i in range(count):
                    off = i * tpi.get_size(lf.elemTypeRef)
                    elem_s = self.form_structs(lf.elemTypeRef, addr + off, recursive, _depth+1)
                    elem_s["levelname"] = "[%d]" % i
                    struct["fields"].append(elem_s)
            return struct

        elif lf.leafKind == tpi.eLeafKind.LF_MEMBER:
            struct = self.form_structs(lf.typeRef, addr+lf.offset, recursive, _depth)
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
                levelname = "",
                type = tpi.get_tpname(lf),
                address=addr,
                size=tpi.get_size(lf),
                bitoff=lf.position,
                bitsize=lf.length,
                lf=lf,
            )

        elif lf.leafKind == tpi.eLeafKind.LF_ENUM:
            return new_struct(
                levelname = lf.name,
                type = tpi.get_tpname(lf),
                address = addr,
                size = tpi.get_size(lf), #?
                fields = [], #?
                lf=lf,
            )

        elif lf.leafKind == tpi.eLeafKind.LF_POINTER:
            return new_struct(
                levelname = "",
                type = tpi.get_tpname(lf),
                address = addr,
                size = tpi.get_size(lf),
                fields = None,
                is_pointer=lf.utypeRef.leafKind != tpi.eLeafKind.LF_PROCEDURE,
                lf=lf,
            )

        elif lf.leafKind == tpi.eLeafKind.LF_MODIFIER:
            return self.form_structs(lf.modifiedTypeRef)
        else:
            raise NotImplementedError(lf)


def get_parsed_size(tp, con):
    return len(tp.build(con))


class DbiStream(Stream):
    _sHeader = Struct(
        "magic" / Const(b"\xFF\xFF\xFF\xFF", Bytes(4)),  # 0
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
        "Machine" / Enum(
            Int16ul,  # 58
            IMAGE_FILE_MACHINE_UNKNOWN = 0x0000,
            IMAGE_FILE_MACHINE_I386 = 0x014c,
            IMAGE_FILE_MACHINE_R3000 = 0x0162,
            IMAGE_FILE_MACHINE_R4000 = 0x0166,
            IMAGE_FILE_MACHINE_R10000 = 0x0168,
            IMAGE_FILE_MACHINE_WCEMIPSV2 = 0x0169,
            IMAGE_FILE_MACHINE_ALPHA = 0x0184,
            IMAGE_FILE_MACHINE_SH3 = 0x01a2,
            IMAGE_FILE_MACHINE_SH3DSP = 0x01a3,
            IMAGE_FILE_MACHINE_SH3E = 0x01a4,
            IMAGE_FILE_MACHINE_SH4 = 0x01a6,
            IMAGE_FILE_MACHINE_SH5 = 0x01a8,
            IMAGE_FILE_MACHINE_ARM = 0x01c0,
            IMAGE_FILE_MACHINE_THUMB = 0x01c2,
            IMAGE_FILE_MACHINE_ARMNT = 0x01c4,
            IMAGE_FILE_MACHINE_AM33 = 0x01d3,
            IMAGE_FILE_MACHINE_POWERPC = 0x01f0,
            IMAGE_FILE_MACHINE_POWERPCFP = 0x01f1,
            IMAGE_FILE_MACHINE_IA64 = 0x0200,
            IMAGE_FILE_MACHINE_MIPS16 = 0x0266,
            IMAGE_FILE_MACHINE_ALPHA64 = 0x0284,
            IMAGE_FILE_MACHINE_AXP64 = 0x0284,
            IMAGE_FILE_MACHINE_MIPSFPU = 0x0366,
            IMAGE_FILE_MACHINE_MIPSFPU16 = 0x0466,
            IMAGE_FILE_MACHINE_TRICORE = 0x0520,
            IMAGE_FILE_MACHINE_CEF = 0x0cef,
            IMAGE_FILE_MACHINE_EBC = 0x0ebc,
            IMAGE_FILE_MACHINE_AMD64 = 0x8664,
            IMAGE_FILE_MACHINE_M32R = 0x9041,
            IMAGE_FILE_MACHINE_CEE = 0xc0ee,
        ),
        "resvd" / Int32ul,  # 60
    )

    # struct MODI
    _DbiExHeader = Struct(
        "pmod" / Int32ul,  # currently open mod
        "sc" / Struct(
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
        "f" / BitStruct(
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
        "mpifileichFile" / Int32ul,  # array [0..ifileMac) of offsets into dbi.bufFilenames
        "niSrcFile" / Int32ul,  # name index for src file
        "niPdbFile" / Int32ul,  # name index for compiler PDB
        "modName" / CString(encoding = "utf8"),  # szModule
        "objName" / CString(encoding = "utf8"),  # szObjFile
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

        data = self.getbodydata(fp)

        dbiexhdrs = []
        dbiexhdr_data = data[:self.header.module_size]
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

        pos = (
            + self.header.module_size
            + self.header.secconSize
            + self.header.secmapSize
            + self.header.filinfSize
            + self.header.tsmapSize
            + self.header.ecinfoSize
        )
        self.dbgheader = self._DbiDbgHeader.parse(data[pos:])


class DbiModule(Stream):
    _sHeader = Struct(
        "unknown" / Int32ul,  # 4
    )

    def load_body(self, fp):
        data = self.getbodydata(fp)
        arr = GreedyRange(dbi.sSymType)
        types = arr.parse(data)
        self.types = [dbi.flatten_leaf_data(t) for t in types]


class GlobalSymbolStream(Stream):
    def load_body(self, fp):
        data = self.getbodydata(fp)
        from . import gdata
        globalsymbols = gdata.parse(data)
        for g in globalsymbols:
            if isinstance(g.leafKind, int):
                kind = "s_unknown"
                try:
                    d = getattr(self, kind)
                except AttributeError:
                    setattr(self, kind, [])
                    d = getattr(self, kind)
                d.append(g)
            else:
                kind = str(g.leafKind)
                try:
                    d = getattr(self, kind.lower())
                except AttributeError:
                    setattr(self, kind.lower(), {})
                    d = getattr(self, kind.lower())
                try:
                    d[g.name] = g
                except AttributeError:
                    breakpoint()

    def get_gvar_info(self, ref: str) -> Struct | None:
        glb_info = None
        with suppress(AttributeError, KeyError):
            glb_info = self.s_gdata32[ref]
        with suppress(AttributeError,KeyError):
            glb_info = self.s_ldata32[ref]
        return glb_info

    def get_user_define_typeid(self, ref: str) -> int | None:
        try:
            return self.s_udt[ref].typind
        except AttributeError:
            return None
        except KeyError:
            return None


class SectionStream(Stream):
    def load_body(self, fp):
        data = self.getbodydata(fp)
        from . import pe
        self.sections = pe.Sections.parse(data)


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
            "<" + ("%dI" % stream_dirs_pg_cnt),
            fp.read(stream_dirs_pg_cnt * U32_SZ)
        )

        root_pages_data = io.BytesIO()
        for ind in root_dir_indice:
            fp.seek(ind * pdb_hdr.blockSize)
            root_pages_data.write(fp.read(pdb_hdr.blockSize))
        root_pages_data.seek(0)

        """"""""""""""""""

        num_streams, = struct.unpack("<I", root_pages_data.read(U32_SZ))
        streamSizes = struct.unpack(
            "<" + ("%sI" % num_streams),
            root_pages_data.read(num_streams * U32_SZ)
        )

        _streams = []
        for id, stream_sz in enumerate(streamSizes):
            stream_pg_cnt = div_ceil(stream_sz, pdb_hdr.blockSize)
            stream_pages = list(struct.unpack(
                "<" + ("%sI" % stream_pg_cnt),
                root_pages_data.read(stream_pg_cnt * U32_SZ)
            ))
            s = STREAM_CLASSES.get(id, Stream)(
                byte_sz=stream_sz,
                page_sz=pdb_hdr.blockSize,
                pages=stream_pages
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

        for s in _streams:
            s.load_body(fp)

        self.streams = _streams

    @property
    def tpi_stream(self) -> TpiStream:
        return self.streams[2]

    @property
    def glb_stream(self) -> GlobalSymbolStream:
        dbi = self.streams[3]
        return self.streams[dbi.header.symrecStream]

    def remap_global_address(self, section: int, offset: int) -> int:
        dbi = self.streams[3]
        # remap global address
        try:
            sects = self.streams[dbi.dbgheader.snSectionHdrOrig].sections
            omap = self.streams[dbi.dbgheader.snOmapFromSrc]
        except AttributeError:
            sects = self.streams[dbi.dbgheader.snSectionHdr].sections
            omap = DummyOmap()
        section_offset = sects[section - 1].VirtualAddress
        return omap.remap(offset + section_offset)

    def get_type_lf_from_name(self, structname: str) -> tuple:
        glb_info = self.glb_stream.get_gvar_info(structname)
        udt_id = self.glb_stream.get_user_define_typeid(structname)
        var_offset = 0
        lf = None
        if glb_info:
            var_offset += self.remap_global_address(glb_info.section, glb_info.offset)
            lf = self.tpi_stream.get_type_lf_from_id(glb_info.typind)
        elif udt_id:
            lf = self.tpi_stream.get_type_lf_from_id(udt_id)
        else:
            with suppress(KeyError):
                lf = self.tpi_stream.get_type_lf_from_name(structname)
        return lf, var_offset


def parse(filename) -> PDB7:
    "Open a PDB file and autodetect its version"
    with open(filename, 'rb') as f:
        sig = f.read(len(_PDB7_SIGNATURE))
        f.seek(0)
        if sig == _PDB7_SIGNATURE:
            pdb = PDB7(f)
            pdb.name = filename
            return pdb
        else:
           raise NotImplementedError(sig)