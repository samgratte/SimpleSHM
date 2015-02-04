#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    ---- serv_data.py ----

    Author: samuel.bucquet@gmail.com
    Date  : 2015-01-14
"""

from flask import Flask, Response, request, jsonify, send_file
import sys
import json
# import eventlet
# eventlet.monkey_patch()
# à lancer avec gunicorn -k eventlet serv_data:app

from shareddata import DataDict, SharedMemory
from divers import Waiting


app = Flask(__name__, static_url_path='/static')


def select_fields(nt, fields=None):
    dico = nt._asdict()
    if fields is None:
        return dico
    # else:
    for f in nt._fields:
        if f not in fields:
            del dico[f]
    return dico


@app.route('/servdata/<dataname>')
def servdata(dataname):
    fields = request.args.get('fields', 'all')
    fields = fields.split(',') if fields != 'all' else None
    frequency = float(request.args.get('frequency', 1))
    dd = DataDict(request.environ['REMOTE_ADDR'], shm)
    data = dd.fetch_new_data(dataname)
    trame = dd.read_data(data)
    if frequency < 0:
        data_iter = dd.listen_to_datas([dataname])

        def serv_data(trame):
            yield 'data: %s\n\n' % json.dumps(select_fields(trame, fields))
            for trame in data_iter:
                yield 'data: %s\n\n' % json.dumps(select_fields(trame, fields))

    elif frequency == 0:
        result = select_fields(trame, fields)
        dd.close()
        return json.dumps(dict(result=result))
    else:

        def serv_data(trame):
            periode = Waiting(frequency)
            periode.set_start()
            while True:
                # trame = trame._replace(ts=periode.start_time)
                yield 'data: %s\n\n' % json.dumps(select_fields(trame, fields))
                periode.wait_next(set_start=True)
                trame = dd.read_data(data)

    return Response(serv_data(trame), mimetype='text/event-stream')


@app.route('/setdata/<dataname>', methods=['GET', 'POST'])
def setdata(dataname):
    params_dict = json.loads(request.args.get('params', ''))
    print "BLIP : ", params_dict
    try:
        dd = DataDict(request.environ['REMOTE_ADDR'], shm)
        data = dd.fetch_new_data(dataname)
        data.set(**params_dict)
        dd.write_data(data)
        dd.close()
    except IOError:
        return jsonify(result=False)
    return jsonify(result=True)


@app.route('/page')
def get_page():
    return send_file('page.html')


@app.route('/battery')
def get_battery():
    return send_file('battery.html')

if __name__ == '__main__':
    print sys.argv
    shm = SharedMemory()
    app.run(host='0.0.0.0', threaded=True, debug=True)
