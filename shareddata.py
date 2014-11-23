#!/usr/bin/python
# -*- coding: utf-8 -*-
# --- sharedata.py ---
# Author   : Samuel Bucquet
# Date     : 2014.10.22
# License  : GPLv2
"""
module d'accès à la mémoire partagée via Redis
HOWTO :
>>> shm_conx = SharedMemory()
>>> ddict = Datadict('APP_NAME', shm_conx)
>>> ddict.set_datas_to_read(['DATA1', 'DATA2', 'DATA3])
>>> data4, data5 = ddict.set_datas_to_write(['DATA4', 'DATA5'])

# Pour lire :
>>> trame1, trame2, trame3 = ddict.next()

# Pour écrire :
>>> data4.set(val1, val2)
>>> data5.set(val3, ts=time.time(), sender='someone_else')
>>> ddict.flush()

# ou encore :
    with SharedMemory('192.250.100.101') as shm:
        shm.wait_for_init('mon_app')  # optionnel
        ddict = DataDict('LogsBattery', shm)
        ddict.set_datas_to_read(['BATTERY__alarms', 'BATTERY__status',
            'BATTERY__measures'])
        for alarms, status, measures in ddict:
            # log des infos de chaque trame
            ...

"""

import time
from os import path, getenv
from sys import argv
import redis
import json
import csv
from collections import namedtuple, OrderedDict
from itertools import izip

from divers import fatal_error, assert_option, set_UTC_time

import plac


def check_appname(app_name):
    if not app_name:
        app_name = path.basename(argv[0])
        pos = app_name.rfind('.py')
        if pos > 0:
            app_name = app_name[:pos]
    return app_name


class Waiting(object):

    def __init__(self, frequency):
        self.periode = 1.0/frequency

    def set_start(self):
        self.start_time = time.time()

    def wait_next(self):
        time_passed = time.time() - self.start_time
        if time_passed > self.periode:
            return
        # else:
        time.sleep(self.periode - time_passed)


class SharedMemory(object):

    def __init__(self, host='127.0.0.1', port=6379, env_init_option=None,
                 time_in_utc=True):
        "Initialise la connection au serveur redis"
        self.conx = redis.Redis(host=host, port=port)
        for i in range(10):
            if self.conx.ping():
                break
            print "[%02d] Attente de Redis ...." % i
            time.sleep(10)
        else:
            fatal_error("Impossible de se connecter à Redis %s:%d!" % (host, port))

        if env_init_option:
            init_msg = assert_option(None, env_init_option)
            self.wait_for_init(init_msg)
        if time_in_utc:
            set_UTC_time()

        self.datadicts = []

    def __enter__(self):
        return self

    def close(self):
        for dd in self.datadicts:
            dd.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def blank_and_initSHM(self, jsonfile, env_option_name=''):
        initmsg = assert_option(None, env_option_name)
        descfile = open(jsonfile, 'r')
        datadesc = json.loads(descfile.read(), object_pairs_hook=OrderedDict)
        self.conx.flushdb()
        p = self.conx.pipeline()
        for dd in datadesc:
            p.set(dd, json.dumps(OrderedDict(datadesc[dd])))
        p.set(initmsg, 'OK')
        p.execute()

    def rejeu(self, filelist, timestart, timend):
        """
        rejoue les données d'après leur timestamp et selon
        une liste de fichiers de données en entrée
        """
        # TODO:
        # TODO: à faire l'IHM pour lancer le rejeu
        pass

    def moos_bridge(self):
        " Echange de données avec MOOS-DB "
        # TODO:
        pass

    def wait_for_init(self, initmsg=''):
        " attente de l'initialisation de la SHM "
        initmsg = assert_option(initmsg, 'INIT_MSG')
        for i in range(10):
            if self.conx.get(initmsg):
                break
            print "[%02d] Attente de %s ...." % (i, initmsg)
            time.sleep(1)
        else:
            fatal_error("\nLa SHM ne s'est pas initialisée !\n")


class Fifo(object):
    """
    Utilise une liste de Redis pour implémenter un tube avec plusieurs
    écrivains et (en général) un seul lecteur.r
    """
    def __init(self, data, shm):
        " "
        self.conx = shm.conx
        self.data = data

    def push(self, *args, **kv):
        """ affecte les champs à la donnée et envoie la donnée dans le tube """
        self.data.set(*args, **kv)
        self.conx.rpush(self.data.name, self.data.to_shm())

    def pop(self):
        """ récupère une donnée du tube et la renvoie
        sous sa forme en namedtuple """
        self.data.from_shm(self.conx.lpop(self.data.name))
        return self.data.trame

    def drain(self):
        """ récupère toutes les données disponibles dans le tube et les
        renvoie sous forme de liste """
        p = self.conx.pipeline()
        p.lrange(self.name, 0, -1)
        p.delete(self.name)
        return [self.data.from_shm(trame) for trame in p.execute()[0]]


class Data(object):

    def __init__(self, name, jsonframe, sender=''):
        self.name = name
        # on parse une première fois l'objet JSON pour connaître
        # les champs (la déclaration de ceux-ci n'est faite qu'à un seul
        # endroit, par le code chargé d'initialiser la SHM
        od = json.loads(jsonframe, object_pairs_hook=OrderedDict)
        self.nt = namedtuple(name, od.keys())
        self.trame = self.nt._make(od.values())  # un namedtuple (non modifiable)
        self.expire = None  # durée de validité non positionné (infini)
        self.is_to_be_written = False
        self.logdir = getenv('LOGDIR')
        if sender:
            self.sender = sender

    def from_shm(self, jsonframe):
        if jsonframe:
            dico = json.loads(jsonframe, object_pairs_hook=OrderedDict)
            self.trame = self.nt._make(dico.values())
        else:
            self.trame = None
        return self.trame

    def to_shm(self):
        return json.dumps(self.trame._asdict())

    @property
    def ts(self):
        return self.trame.ts

    @ts.setter
    def ts(self, ts):
        self.trame = self.trame._replace(ts=ts)

    @property
    def sender(self):
        return self.trame.sender

    @sender.setter
    def sender(self, sendername):
        self.trame = self.trame._replace(sender=sendername)

    def set(self, *args, **kv):
        """
        affecte les champs dans l'ordre des arguments et positionne
        le timestamp et l'émetteur si besoin
        """
        now = time.time()
        self.trame = self.nt._make([self.ts, self.sender]+list(args))
        if len(kv):
            od = self.trame._asdict()
            for k in od:
                if k in kv:
                    od[k] = kv[k]
            self.trame = self.nt._make(od.values())
            self.expire = None if 'expire' not in kv else kv['expire']
        if self.ts == 0.0:  # on positionne un timestamp valide
            self.ts = now
        self.is_to_be_written = True
        self.log()

    def log(self):
        if not self.logdir:
            return
        if not hasattr(self, 'logfile'):
            # open csv log file
            logfilename = getenv('LOGFILE')
            if not logfilename:
                logfilename = time.strftime('%Y-%m-%d_%Hh%Mm%SsZ') + '_' \
                    + self.sender + '_' + self.name + '.csv'
                logfilename = path.join(self.logdir, logfilename)
            self.logfile = open(logfilename, 'wb', buffering=1)  # line buffering
            self.csv = csv.writer(self.logfile)
            self.csv.writerow(self.trame._fields)
        self.csv.writerow(self.trame)

    def close(self):
        if hasattr(self, 'logfile'):
            self.logfile.close()


class DataDict(object):

    def __init__(self, sender_name, shm):
        self.conx = shm.conx
        self.origin = check_appname(sender_name)
        self.datasfromshm = []
        self.datastoshm = []
        self.fifos = []
        self.keys = shm.conx.keys('*')
        self.shm = shm
        shm.datadicts.append(self)

    def fetch_new_datas(self, namelist):
        datas = []
        for name in namelist:
            if name not in self.keys:
                raise ValueError("%s dataname not in SHM !" % name)
            datas.append(Data(name, self.conx.get(name), sender=self.origin))
        return datas

    def declare_fifos(self, namelist):
        """
        déclare les tubes utilisés par la suite :
        - pour émettre une donnée dans un tube : fifo.push(*fields)
        - pour récupérer une donnée du tube et la sortir : donnee = fifo.pop()
        - pour travailler sur toutes les données disponibles à ce moment :
            for donnee in fifo.drain():
                print donnee
        """
        for data in self.fetch_new_datas(namelist):
            self.fifos.append(Fifo(data, self.conx))
        return [f for f in self.fifos if f.data.name in namelist]

    def set_datas_to_read(self, namelist):
        # TODO: renvoyer un itérateur sur les données à lire
        # de manière à pouvoir récupérer plusieurs groupes de données
        # séparement (avec des fréquences différentes par ex.
        newdatas = self.fetch_new_datas(namelist)
        self.datasfromshm += newdatas
        return newdatas

    def read_datas(self, datalist):
        # la lecture des données s'effectue au sein d'une transaction
        p = self.conx.pipeline()
        datas_nt = []
        for data in datalist:
            # récupération à partir de Redis
            p.get(data.name)
        for data, result in izip(datalist, p.execute()):
            nt = data.from_shm(result)
            if not data.sender:  # donnée non initialisée
                nt = None
            datas_nt.append(nt)
        return datas_nt

    def listen_to(self, datalist, pattern):
        ps = self.conx.pubsub()
        if pattern:
            ps.psubscribe(pattern)
        else:
            ps.subscribe(datalist[0].name)
        for message in ps.listen():
            if not message['data'] is 'available':
                continue
            yield self.read_datas(datalist)

    def listen_to_datas(self, namelist, pattern=None):
        """
        la première data sert aussi à l'écoute et les autres sont lues
        et renvoyées en même temps.
        Renvoie un générateur qui bloque en attente de rafraichissement
        de la donnée.
        """
        newdatas = self.fetch_new_datas(namelist)
        return self.listen_to(newdatas, pattern)

    def set_datas_to_write(self, namelist):
        newdatas = self.fetch_new_datas(namelist)
        self.datastoshm += newdatas
        return newdatas

    def __iter__(self):
        return self

    def write(self):
        """
        écrit toutes les données à écrire vers la mémoire partagée
        """
        p = self.conx.pipeline()
        for data in self.datastoshm:
            if data.is_to_be_written:
                data.sender = self.origin
                p.set(data.name, data.to_shm(), data.expire)
                p.publish(data.name, 'available')
                # on indique que la donnée a été écrite
                data.is_to_be_written = False
                data.ts = 0.0
        p.execute()

    def get_data(self, data):
        return data.from_shm(self.conx.get(data.name))

    def next(self):
        """
        renvoie à chaque itération une liste de namedtuple
        corespondants aux données lues dans Redis
        """
        return self.read_datas(self.datasfromshm)

    def close(self):
        for data in self.datastoshm:
            data.close()
            self.datastoshm.remove(data)
        self.shm.datadicts.remove(self)


@plac.annotations(
    descfile=("fichier JSON de description des données", 'positional'),
    redis_server=("Nom ou @ IP de la cpu sur laquelle tourne Redis", 'option', 'r'),
    redis_port=("N° de port tcp pour se connecter à Redis", 'option', 'p', int),
    env_init=("Nom de la variable d'environnement qui contient la data d'init de la shm", 'option', 'i')
)
def main(descfile, redis_server='localhost', redis_port=6379, env_init=None):
    shm = SharedMemory(host=redis_server, port=redis_port)
    shm.blank_and_initSHM(descfile, env_init)

if __name__ == '__main__':
    plac.call(main)
