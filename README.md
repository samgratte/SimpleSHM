SimpleSHM
=========

a very simple and functionnal Shared Memory based on Redis

# Mise en route de la mémoire partagée (SHM) et des applications

## Redis

- Installer **Redis** et les modules *Python* associés :

```
# aptitude install redis-server redis-tools python-redis python-hiredis
```

- Éditer le fichier de configuration `/etc/redis/redis.conf`.
Y modifier sur quelle(s) interface(s) redis écoute par ex.

- Puis le lancer si nécessaire avec :

```
# /etc/init.d/redis-server start
```

## Initialiser la SHM

- Avoir un fichier *JSON* décrivant les données avec des valeurs à vide :

```
...
    "PUPITRE__joyleft": [
        [ "ts", 0.0 ], 
        [ "sender", "blip" ], 
        [ "axe_horizontal", 0 ], 
        [ "axe_vertical", 0 ], 
        [ "rotation", 0 ], 
        [ "bouton", false ]
    ], 
...
```

Les champs *ts* et *sender* sont obligatoires pour l'application et doivent être
les premiers, dans cet ordre.

- Initialiser la SHM avec ce dictionnaire à blanc et un flag pour annoncer aux
applications que la SHM est prête :

```
$ export INIT_MSG='SPARTAN_INIT'
$ python -m shareddata -i INIT_MSG datadesc.json
```

## Lancer les applications

Chaque application dispose d'une aide intégrée et d'une vérification
élémentaire des paramètres qui lui sont passés en argument.
Cette fonctionnalité repose sur le module Python *plac*.

```
$ ./hdl_battery.py -h
usage: hdl_battery.py [-h] [-do-debug] [-s /dev/ttyO1] [-f 2] [-r redissrv]
                      [-p 6379] [-a ./hdl_battery.py] [-i None]

optional arguments:
  -h, --help            show this help message and exit
  -do-debug             Affiche les infos de debug pour la batterie
  -s /dev/ttyO1, --serialport /dev/ttyO1
                        Périphérique série connecté à la batterie
  -f 2, --frequency 2   À quelle fréquence on interroge (et répond à) la
                        batterie
  -r redissrv, --redis-server redissrv
                        Nom ou @ IP de la cpu sur laquelle tourne Redis
  -p 6379, --redis-port 6379
                        N° de port tcp pour se connecter à Redis
  -a ./hdl_battery.py, --app-name ./hdl_battery.py
                        Nom de l'application pour la SHM
  -i None, --env-init None
                        Nom de la variable d'environnement qui contient la
                        data d'init de la shm
$ 

```

On lance ensuite les applications en renseignant au minimum `--app-name` qui
correspond au nom de l'émétteur d'une donnée dans la SHM et qui apparaît aussi
dans le nom de fichier de log de la donnée.
On doit aussi renseigner `--env-init` qui, comme vu plus haut, est la variable
d'environnement qui contient le nom de la donnée qui indique que le dictionnaire
de donnée pour l'application est bien initialisé.

```
$ ./hdl_battery.py -i 'INIT_MSG' -a 'HDL_BATTERY' &
$ ./hdl_ains.py -i 'INIT_MSG' -a 'READ_PROP' -f 10 'PROP__readings' 0 1 2 3
$ ./hdl_dacs.py -i 'INIT_MSG' 'PROP__consignes' 2 3 # n"écrit rien vers la SHM
```

# Utiliser la SHM dans les applications *Python*

## Initialiser l'accès à la SHM

```Python
>>> shm_conx = SharedMemory()
>>> ddict = Datadict('APP_NAME', shm_conx)
```

ou encore

```Python
with SharedMemory(redis_server, redis_port, env_init) as shm:
    dd = DataDict(app_name, shm)
```
On utilise ici un *context manager* qui fermera automatiquement les fichiers de
logs des données ouverts.

## Déclarer les données en lecture et en écritures

```Python
    dd.set_datas_to_read(['BATTERY__command'])
    shm_status, shm_measures, shm_alarms = dd.set_datas_to_write(['BATTERY__status', 'BATTERY__measures', 'BATTERY__alarms'])

```

/!\\ on déclare une liste de noms de données et **on récupère une liste** d'instances
de l'objet `Data` pour l'écriture.
Donc même si on écrit qu'une seule donnée vers la SHM, on a :

```Python
    cmd_data, = self.ddict.set_datas_to_write(['BATTERY__command']
```

## Lire la SHM

L'objet `DataDict` est un générateur qui renvoie à chaque itération une liste de
trames lues de la SHM dans l'ordre de la déclaration avec `set_datas_to_read`.

```Python
    for trame1, trame2, trame3 in dd:
        ...
```

ou bien :

```Python
    trame1, trame2, trame3 = dd.next()
```

On peut rester en attente bloquante sur une nouvelle donnée. Il faut alors
déclarer la donnée ou le groupe de données avec `listen_to_datas`.
La contrainte est que c'est la première donnée du groupe qui est en écoute et
toutes les données sont lues et renvoyées **sous forme d'une liste** dès que la première est rafraîchit
dans la SHM.

```Python
    data_listen = dd.listen_to_datas(['DATA1', 'DATA2', 'DATA3'])
    # lecture bloquante sur 'DATA1'
    for trame1, trame2, trame3 in data_listen:
        ...
```

## Écrire vers la SHM

Il faut renseigner les valeurs affectées aux champs de la données, et si les
champs `ts` et `sender` ne sont pas déjà positionnés dans l'objet `Data`, on les
passe en paramètres avec un `keyword` :

```Python
    cmd_data.set('acknowledge', ts=time.time())
```

Lorsque toutes les données ont été renseignées **on envoie l'ordre de les écrire
vers la SHM avec `flush()`**. On peut ainsi grouper l'écriture de plusieurs données afin qu'elles
restent cohérentes entre elles, l'écriture vers la SHM étant réalisée au sein
d'une *transaction*, garantissant l'atomicité de l'opération.

```Python
   dd.flush()
```

**Un fichier de log** est créé pour chaque donnée en écriture et les champs y sont
inscrits ligne par ligne au format *CSV* pour chaque ordre `set()` sur la donnée.
Il faut qu'une variable d'environnement `'LOGDIR'` soit positionnée, les fichiers de logs
y sont écrits, sinon cela désactive le log des données.

```
$ export LOGDIR='/var/log'
$ ./hdl_ains.py -i 'INIT_MSG' -a 'PROP_READING' -f 10 'PROP__readings' 0 1 2 3
$ LOGDIR='' ./hdl_gpio_in.py -a 'WATER_DETECT' -i 'INIT_MSG' 'PHINS__Enclosure_water_detected' 48
```

