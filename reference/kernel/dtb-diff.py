#!/usr/bin/env python3
"""Diff two DTBs by meaning, not by phandle numbers.

  dtb-diff.py OLD.dtb NEW.dtb

Every property whose 32-bit cells hold a phandle is compared with that cell
replaced by the target node's path, so a rebuild that renumbers phandles
shows no change, while a changed value, a new property or a new node does.
Needs python3-libfdt.
"""
import sys
import libfdt


def walk(fdt):
    """{node path: {property name: raw bytes}} for every node, depth first."""
    nodes, stack, off, depth = {}, [], 0, 0
    while True:
        stack = stack[:depth] + [fdt.get_name(off)]
        props = {}
        po = fdt.first_property_offset(off, [libfdt.NOTFOUND])
        while po >= 0:
            prop = fdt.get_property_by_offset(po)
            props[prop.name] = bytes(prop)
            po = fdt.next_property_offset(po, [libfdt.NOTFOUND])
        nodes["/" + "/".join(stack[1:])] = props
        try:
            off, depth = fdt.next_node(off, depth)
        except libfdt.FdtException:
            return nodes
        if off < 0 or depth <= 0:
            return nodes


def load(path):
    fdt = libfdt.Fdt(open(path, "rb").read())
    nodes = walk(fdt)
    ph = {}
    for p, props in nodes.items():
        v = props.get("phandle")
        if v and len(v) == 4:
            ph[int.from_bytes(v, "big")] = p
    return nodes, ph



def show(v):
    if isinstance(v, bytes):
        s = v.rstrip(b"\0")
        if s and all(32 <= b < 127 or b == 0 for b in s):
            return repr(s.replace(b"\0", b"|").decode())
        return v.hex()
    return " ".join(x if isinstance(x, str) else hex(x) for x in v)


def main():
    (a, pa), (b, pb) = load(sys.argv[1]), load(sys.argv[2])
    for p in sorted(set(a) - set(b)):
        print(f"- node {p}")
    for p in sorted(set(b) - set(a)):
        print(f"+ node {p}")
    for p in sorted(set(a) & set(b)):
        A, B = a[p], b[p]
        for n in sorted(set(A) | set(B)):
            if n in ("phandle", "linux,phandle"):
                continue
            if n not in B:
                print(f"- {p}:{n} = {show(A[n])}")
            elif n not in A:
                print(f"+ {p}:{n} = {show(B[n])}")
            elif A[n] != B[n] and not same_cells(A[n], B[n], pa, pb):
                print(f"~ {p}:{n}: {show(A[n])} -> {show(B[n])}")


def same_cells(va, vb, pa, pb):
    """Equal up to phandle renumbering: each 32-bit cell is either the same
    number, or a phandle on both sides pointing at the same node path."""
    if len(va) != len(vb) or len(va) % 4:
        return False
    for i in range(0, len(va), 4):
        ca, cb = int.from_bytes(va[i:i + 4], "big"), int.from_bytes(vb[i:i + 4], "big")
        if ca != cb and not (ca in pa and cb in pb and pa[ca] == pb[cb]):
            return False
    return True


if __name__ == "__main__":
    main()
