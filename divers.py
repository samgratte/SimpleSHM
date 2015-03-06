#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    ---- divers.py ----

    Author: samuel.bucquet@gmail.com
    Date  : 2014-11-23 17:28:08 CET

    Ensemble de function utiles
"""

from sys import stderr
from os import environ, getenv
from time import time, sleep, tzset
from operator import xor, not_
import plac


def fatal_error(msg):
    " fin du programme avec un message envoyé sur stderr "
    stderr.write("\n%s\n" % msg)
    exit(1)


def set_UTC_time():
    " On travaille en UTC "
    environ['TZ'] = 'UTC'
    tzset()


def assert_option(option, option_name):
    """ Vérifie qu'une variable d'environnement a bien éte positionnée
    et la renvoie si l'option n'est pas valide """
    if not option:
        option = getenv(option_name)
        if not option:
            raise ValueError("%s non positionné" % option_name)
    return option


def frange(start, stop, step=1, K=1000000):
    """
    like xrange with floats allowed
    >>>frange(0,100,100.0/8)
    [0.0, 12.5, 25.0, 37.5, 50.0, 62.5, 75.0, 87.5]
    """
    return (x/(K*1.0) for x in xrange(start*K, stop*K, int(step*K)))


def bits_grow(nbbits):
    """
    renvoie un générateur de nombre avec les bits positionnés croissants
    exemple :
    >>>map(lambda x: format(x,"016b"),bits_grow(16))
    ['0000000000000001',
     '0000000000000011',
     '0000000000000111',
     '0000000000001111',
     '0000000000011111',
     '0000000000111111',
     '0000000001111111',
     '0000000011111111',
     '0000000111111111',
     '0000001111111111',
     '0000011111111111',
     '0000111111111111',
     '0001111111111111',
     '0011111111111111',
     '0111111111111111',
     '1111111111111111']
    """
    return ((reduce(lambda x, y: x | (1 << y), range(i), 0))
            for i in range(1, nbbits + 1))


def bits_recess(nbbits):
    """
    renvoie un générateur de nombre avec les bits positionnés décroissants
    exemple :
    >>> map(bin,bits_recess(16))
    ['0b1111111111111111',
     '0b1111111111111110',
     '0b1111111111111100',
     '0b1111111111111000',
     '0b1111111111110000',
     '0b1111111111100000',
     '0b1111111111000000',
     '0b1111111110000000',
     '0b1111111100000000',
     '0b1111111000000000',
     '0b1111110000000000',
     '0b1111100000000000',
     '0b1111000000000000',
     '0b1110000000000000',
     '0b1100000000000000',
     '0b1000000000000000']
    """
    return ((reduce(lambda x, y: x ^ (1 << y), range(i), 2**nbbits - 1))
            for i in range(nbbits))


def threshold(value, thresholds, nullvalue=0):
    """
    Parcoure une liste de paire (seuil,objet) et renvoie l'objet correspondant
    à la valeur avant le seuil
    """
    return nullvalue if value == 0 else filter(lambda x: x[0] < value, thresholds)[-1][1]


def xor_cks(buff):

    """ renvoie un entier 8bit, le résultat du checksum XOr
    sur chaque caractère de 'buff :
    crc = 0
    for c in bytearray(buff):
        crc ^= c
    return crc

    >>>xor_cks('blip')
    23
    """
    # /!\ le map/reduce est un peu moins performant en 2.7.8 que
    # l'implémentation native comme au-dessus !
    return reduce(xor, bytearray(buff))


def parse_hexa(buff, nbint=None):
    """ renvoie les entiers correspondants à chaque couple de caractères hexa
    en ascii : 'A0' -> 160 dans 'buff' :

    >>> parse_hexa('A0B2C3DE')
    (160, 178, 195, 222)

    si nbint est renseigné, on ne renvoie que ce nombre d'entiers.
    """

    if nbint is None:
        nbint = len(buff)
    return [i for i in bytearray.fromhex(buff)[:nbint]]


def bools_from8bit(value, nbbits=8, negate=False):
    """ on renvoie une liste de bool : False si bit à 1 avec negate=True
    et si nbbits est renseigné, on ne lit que ceux-ci

    >>> bools_from8bit(7,4)
    [True, True, True, False]
    >>> bools_from8bit(7, negate=True)
    [False, False, False, True, True, True, True, True]
    """
    bools = (bool(value & i) for i in [1, 2, 4, 8, 16, 32, 64, 128][:nbbits])
    return map(not_, bools) if negate else list(bools)


class Waiting(object):

    def __init__(self, frequency, set_start=False):
        self.periode = 1.0/frequency
        if set_start:
            self.set_start()

    def set_start(self):
        self.start_time = time()

    def wait_next(self, set_start=False):
        time_passed = time() - self.start_time
        if time_passed > self.periode:
            if set_start:
                self.set_start()
            return
        # else:
        sleep(self.periode - time_passed)
        if set_start:
            self.set_start()


def main():
    " testons tout celà et plus"

if __name__ == '__main__':
    plac.call(main)
