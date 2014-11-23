#!/usr/bin/python
# -*- coding: utf-8 -*-
# --- trame.py ---
# Author  : Samuel Bucquet
# Date    : 31.10.2014
# License : GPLv2

from collections import namedtuple, OrderedDict
import struct
import time

# coeffs
slong2deg = 180.0/(2**31)
sshort2deg = 180.0/(2**15)
ushort2deg = 360.0/(2**16)


class Trame(object):

    name = ''
    fieldsname = []
    first_bytes = ''

    def __init__(self, fd):
        self.framedesc = namedtuple(self.name, self.fieldsname)
        self.datas = OrderedDict(zip(self.fieldsname, [0]*len(self.fieldsname)))
        self.size = 0
        self.fd = fd

    def get_crctrame(self, fields):
        pass

    def do_crc(self, buff):
        pass

    def add_crc(self, buff):
        pass

    def get_fields(self, buff):
        pass

    def build_fields(self):
        pass

    def process_fields(self, fields):
        pass

    def read(self):
        pass

    def parse(self, buff):
        fields = self.get_fields(buff)
        if self.get_crctrame(fields) != self.do_crc(buff):
            return None

        fields = self.process_fields(fields)

        return self.framedesc._make(fields)

    def __iter__(self):
        return self

    def next(self):
        while True:
            return self.read()


class BinaryTrame(Trame):

    struct_fmt = ""

    def __init__(self, fd):
        super().__init__(self, fd)
        self.struct = struct.Struct(self.struct_fmt)
        self.size = self.struct.size

    def read(self, fd):
        buff = fd.read(self.size)
        sync_pos = buff.find(self.first_bytes)
        if sync_pos == -1:
            # impossible de trouver un marqueur de trame
            return None
        # else
        ts = time.time()
        if sync_pos != 0:
            buff = buff[sync_pos] + fd.read(sync_pos)
        trame = self.parse(buff)
        if trame is None:
            # Trame invalide (bad crc)
            return None
        self.timestamp = ts
        self.datas = trame
        return trame

    def get_fields(self, buff):
        return list(self.struct.unpack(buff))

    def build(self):
        fields = self.build_fields()
        buff = self.first_bytes + self.struct.pack(*[fields[n] for n in self.fieldsname])
        return self.add_crc(buff)


class AsciiTrame(Trame):

    delim = ','

    def __init__(self, fd):
        super().__init__(self, fd)

    def read(self, fd):
        line = fd.readline()
        ts = time.time()
        trame = self.parse(line)
        if trame is None:
            # Trame invalide (bad crc)
            return None
        self.timestamp = ts
        self.datas = trame
        return trame

    def get_fields(self, line):
        return line.strip().split(self.delim)

    def build(self):
        pass
