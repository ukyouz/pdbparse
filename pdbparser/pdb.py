import io
import struct
from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from functools import cached_property
from io import BytesIO
from typing import TypedDict

from construct import Array
from construct import Bytes
from construct import Const
from construct import Container
from construct import CString
from construct import Enum
from construct import GreedyRange
from construct import Int16sl
from construct import Int16ul
from construct import Int32ul
from construct import Padding
from construct import Struct

from . import tpi

_strarray = "names" / GreedyRange(CString(encoding = "utf8"))


# ref: https://llvm.org/docs/PDB/MsfFile.html#file-layout

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
    val: int
    type: str
    address: int
    size: int
    bitoff: int
    bitsize: int
    fields: list


def new_struct(**kwargs):
    s = StructRecord(
        levelname="",
        value=0,
        type="",
        address=0,
        size=0,
        bitoff=None,
        bitsize=None,
        fields=None,
        is_pointer=False,
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

    @property
    def structs(self) -> dict[str, StructRecord]:
        """ return dict of {structname: idx} """
        types = getattr(self, "types", {})
        return {
            t.name: t
            for t in types.values()
            if t.leafKind in {
                tpi.eLeafKind.LF_STRUCTURE,
                tpi.eLeafKind.LF_STRUCTURE_ST,
                tpi.eLeafKind.LF_UNION,
                tpi.eLeafKind.LF_UNION_ST,
            }
        }

    def _resolve_refs(self, lf, inside_fields: bool=False):
        ref_fields = tpi.FieldsRefAttrs if inside_fields else tpi.TypRefAttrs

        for attr in ref_fields.get(lf.leafKind, []):
            ref = lf[attr]
            if isinstance(ref, int):
                if ref < self.header.typeIndexBegin:
                    try:
                        setattr(lf, attr + "Ref", tpi.eBaseTypes[ref])
                    except KeyError:
                        print("Unknown Base Type %s" % hex(ref))
                elif ref >= self.header.typeIndexBegin:
                    with suppress(KeyError):
                        setattr(lf, attr + "Ref", self.types[ref])
            elif isinstance(ref, list):
                raise NotImplemented(ref)

    def _foward_refs(self, lf, fwdref_map, inside_fields: bool=False):
        ref_fields = tpi.FieldsRefAttrs if inside_fields else tpi.TypRefAttrs

        for attr in ref_fields.get(lf.leafKind, []):
            ref = lf[attr]
            if isinstance(ref, int):
                if ref < self.header.typeIndexBegin:
                    with suppress(KeyError):
                        setattr(lf, attr, fwdref_map[ref])
                elif ref >= self.header.typeIndexBegin:
                    with suppress(KeyError):
                        setattr(lf, attr, fwdref_map[ref])
            elif isinstance(ref, list):
                raise NotImplemented(ref)

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
        self.types = type_dict

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

    def form_structs(self, lf, addr=0) -> StructRecord:
        if isinstance(lf, tpi.BasicType):
            return new_struct(
                levelname=lf.name,
                type = str(lf),
                address = addr,
                size = tpi.get_size(lf),
            )
        elif lf.leafKind in {
            tpi.eLeafKind.LF_STRUCTURE,
            tpi.eLeafKind.LF_STRUCTURE_ST,
            tpi.eLeafKind.LF_UNION,
            tpi.eLeafKind.LF_UNION_ST,
        }:
            struct = new_struct(
                levelname="",
                type=lf.name,
                address = addr,
                size = tpi.get_size(lf),
                fields={},
            )
            for member in lf.fieldsRef.fields:
                mem_struct = self.form_structs(member, addr)
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
            )
            for i in range(count):
                off = i * tpi.get_size(lf.elemTypeRef)
                elem_s = self.form_structs(lf.elemTypeRef, addr=addr + off)
                elem_s["levelname"] = "[%d]" % i
                struct["fields"].append(elem_s)
            return struct

        elif lf.leafKind == tpi.eLeafKind.LF_MEMBER:
            struct = self.form_structs(lf.typeRef, addr=addr+lf.offset)
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
                type = str(lf.leafKind),
                address=addr,
                size=tpi.get_size(lf),
                bitoff=lf.position,
                bitsize=lf.length,
            )

        elif lf.leafKind == tpi.eLeafKind.LF_ENUM:
            return new_struct(
                levelname = lf.name,
                type = str(lf.leafKind),
                address = addr,
                size = tpi.get_size(lf), #?
                fields = [], #?
            )

        elif lf.leafKind == tpi.eLeafKind.LF_POINTER:
            return new_struct(
                levelname = "",
                type = "%s *" % (lf.utypeRef.name),
                address = addr,
                size = tpi.get_size(lf),
                fields = None,
                is_pointer=True,
            )

        else:
            raise NotImplementedError(lf)


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
        pos = (
            + self.header.module_size
            + self.header.secconSize
            + self.header.secmapSize
            + self.header.filinfSize
            + self.header.tsmapSize
            + self.header.ecinfoSize
        )
        data = self.getbodydata(fp)
        self.dbgheader = self._DbiDbgHeader.parse(data[pos:])


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