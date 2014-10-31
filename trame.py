#!/usr/bin/python
# -*- coding: utf-8 -*-
# --- trame.py ---
# Author  : Samuel Bucquet
# Date    : 31.10.2014
# License : GPLv2

from collections import namedtuple, OrderedDict
import struct

# coeffs
slong2deg = 180.0/(2**31)
sshort2deg = 180.0/(2**15)
ushort2deg = 360.0/(2**16)


def xor_crc(buff):

    crc = 0
    for c in buff:
        crc ^= ord(c)
    return crc


class Trame(object):

    name = ''
    fieldsname = []
    first_bytes = ''

    def __init__(self):
        self.framedesc = namedtuple(self.name, self.fieldsname)
        self.datas = OrderedDict(zip(self.fieldsname, [0]*len(self.fieldsname)))

    def get_crctrame(self, fields):
        pass

    def do_crc(self, buff):
        pass

    def add_crc(self, buff):
        pass

    def build_fields(self):
        pass

    def process_fields(self, fields):
        pass


class Bintrame(Trame):

    struct_fmt = ""

    def __init__(self):
        super().__init__(self)
        self.struct = struct.Struct(self.struct_fmt)

    def parse(self, buff):

        fields = list(self.struct.unpack(buff))
        if self.get_crctrame(fields) != self.do_crc(buff):
            return None

        fields = self.process_fields(fields)

        return self.framedesc._make(fields)

    def build(self):

        fields = self.build_fields()
        buff = self.first_bytes + self.struct.pack(*[fields[n] for n in self.fieldsname])
        return self.add_crc(buff)


class Asciitrame(Trame):

    def __init__(self):
        super().__init__(self)
