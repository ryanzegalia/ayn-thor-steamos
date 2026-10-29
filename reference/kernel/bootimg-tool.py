#!/usr/bin/env python3
"""Read and rewrite the Thor's ABL KERNEL (Android boot image header v0).

  bootimg-tool.py info    KERNEL                 header, cmdline, DTB models, sizes
  bootimg-tool.py unpack  KERNEL DIR             Image.gz, dtb-NN-<model>.dtb, ramdisk.cpio.gz
  bootimg-tool.py cmdline KERNEL OUT --from REF  OUT = KERNEL with REF's cmdline, nothing else

KERNEL layout (pb-os external-and-mods/kernel-sm8650/build.sh): page 0 header,
then gzip(Image) with the DTBs appended after the gzip stream, then a gzip
cpio ramdisk (busybox init). ABL picks the DTB whose `model` matches the
device ("AYN Thor").

`cmdline` keeps kernel, ramdisk and every header field, swaps only the
cmdline and recomputes the header id the way mkbootimg does (same as pb-os
ufs-bootimg.py retarget). We use it so a new kernel boots with exactly the
cmdline the current one has (root=PARTLABEL=STORAGE, no `splash`).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import struct
import sys
import zlib
from pathlib import Path

MAGIC = b"ANDROID!"
HDR = struct.Struct("<8s10I16s512s32s1024s")
FDT_MAGIC = b"\xd0\x0d\xfe\xed"


class BootImg:
    def __init__(self, data: bytes):
        if data[:8] != MAGIC:
            sys.exit("not an Android boot image (no ANDROID! magic)")
        f = HDR.unpack_from(data)
        (self.magic, self.kernel_size, self.kernel_addr, self.ramdisk_size,
         self.ramdisk_addr, self.second_size, self.second_addr, self.tags_addr,
         self.page_size, self.header_version, self.os_version, self.name,
         cmd, self.id, self.extra) = f
        if self.header_version != 0:
            sys.exit(f"header v{self.header_version}, expected v0")
        self.cmdline = cmd.rstrip(b"\0").decode("ascii", "replace")
        p = self.page_size
        off = p
        self.kernel = data[off:off + self.kernel_size]
        off += -(-self.kernel_size // p) * p
        self.ramdisk = data[off:off + self.ramdisk_size]
        off += -(-self.ramdisk_size // p) * p
        self.second = data[off:off + self.second_size]
        if len(self.kernel) != self.kernel_size or len(self.ramdisk) != self.ramdisk_size:
            sys.exit("truncated boot image")

    def expected_id(self) -> bytes:
        sha = hashlib.sha1()
        for blob in (self.kernel, self.ramdisk, self.second):
            sha.update(blob)
            sha.update(struct.pack("<I", len(blob)))
        return sha.digest().ljust(32, b"\0")

    def build(self, cmdline: str) -> bytes:
        raw = cmdline.encode("ascii")
        if len(raw) >= 512:
            sys.exit("cmdline too long for header v0")
        hdr = HDR.pack(MAGIC, self.kernel_size, self.kernel_addr, self.ramdisk_size,
                       self.ramdisk_addr, self.second_size, self.second_addr,
                       self.tags_addr, self.page_size, 0, self.os_version, self.name,
                       raw.ljust(512, b"\0"), self.expected_id(), self.extra)
        p = self.page_size
        pad = lambda b: b + b"\0" * (-len(b) % p)
        return pad(hdr) + pad(self.kernel) + pad(self.ramdisk) + (pad(self.second) if self.second else b"")

    def split_kernel(self) -> tuple[bytes, list[bytes]]:
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        d.decompress(self.kernel)
        tail = d.unused_data
        gz = self.kernel[:len(self.kernel) - len(tail)]
        dtbs = []
        while len(tail) >= 8 and tail[:4] == FDT_MAGIC:
            size = struct.unpack(">I", tail[4:8])[0]
            dtbs.append(tail[:size])
            tail = tail[size:]
        if tail.strip(b"\0"):
            sys.exit(f"{len(tail)} unexpected bytes after the DTBs")
        return gz, dtbs


def dtb_model(dtb: bytes) -> str:
    # model is a root-node property; good enough to find the first "model" string value.
    off_struct, off_strings = struct.unpack(">II", dtb[8:16])
    size_strings = struct.unpack(">I", dtb[32:36])[0]
    strings = dtb[off_strings:off_strings + size_strings]
    i, depth = off_struct, 0
    while i < len(dtb):
        tok = struct.unpack(">I", dtb[i:i + 4])[0]
        i += 4
        if tok == 1:  # BEGIN_NODE
            end = dtb.index(b"\0", i)
            i = (end + 4) & ~3
            depth += 1
        elif tok == 2:
            depth -= 1
        elif tok == 3:  # PROP
            ln, nameoff = struct.unpack(">II", dtb[i:i + 8])
            i += 8
            name = strings[nameoff:strings.index(b"\0", nameoff)].decode()
            val = dtb[i:i + ln]
            i = (i + ln + 3) & ~3
            if depth == 1 and name == "model":
                return val.rstrip(b"\0").decode("ascii", "replace")
        elif tok == 9:
            break
    return "?"


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("info"); a.add_argument("kernel")
    a = sub.add_parser("unpack"); a.add_argument("kernel"); a.add_argument("dir")
    a = sub.add_parser("cmdline"); a.add_argument("kernel"); a.add_argument("out")
    a.add_argument("--from", dest="ref", required=True, help="boot image whose cmdline to copy")
    args = ap.parse_args()

    data = Path(args.kernel).read_bytes()
    img = BootImg(data)
    if args.cmd == "info":
        gz, dtbs = img.split_kernel()
        print(f"page_size={img.page_size} kernel={img.kernel_size} ramdisk={img.ramdisk_size} second={img.second_size}")
        print(f"ID_OK={'yes' if img.id == img.expected_id() else 'no'}")
        print(f"PARTLABEL_ROOT={'yes' if re.search(r'(^| )root=PARTLABEL=STORAGE( |$)', img.cmdline) else 'no'}")
        print(f"cmdline={img.cmdline}")
        print(f"image_gz={len(gz)} dtbs={len(dtbs)}")
        for n, d in enumerate(dtbs):
            print(f"dtb[{n}] {len(d)} {dtb_model(d)}")
    elif args.cmd == "unpack":
        out = Path(args.dir); out.mkdir(parents=True, exist_ok=True)
        gz, dtbs = img.split_kernel()
        (out / "Image.gz").write_bytes(gz)
        (out / "ramdisk.cpio.gz").write_bytes(img.ramdisk)
        (out / "cmdline").write_text(img.cmdline + "\n")
        for n, d in enumerate(dtbs):
            slug = re.sub(r"[^A-Za-z0-9]+", "-", dtb_model(d)).strip("-").lower()
            (out / f"dtb-{n:02d}-{slug}.dtb").write_bytes(d)
        print(f"unpacked {len(dtbs)} DTBs to {out}")
    elif args.cmd == "cmdline":
        ref = BootImg(Path(args.ref).read_bytes())
        new = img.build(ref.cmdline)
        check = BootImg(new)
        assert check.kernel == img.kernel and check.ramdisk == img.ramdisk and check.cmdline == ref.cmdline
        assert check.id == check.expected_id()
        Path(args.out).write_bytes(new)
        print(f"wrote {args.out} with cmdline: {ref.cmdline}")


if __name__ == "__main__":
    main()
