#!/usr/bin/env python

import os
import json
import sys
import datetime
import requests
from flask import Flask, request
from functools import wraps
import logging
import sqlite3

app = Flask(__name__, static_url_path='', static_folder='static')

def serialize_to_json(object):
    """Serialize class objects to json"""
    try:
        return object.__dict__
    except AttributeError:
        raise TypeError(repr(object) + 'is not JSON serializable')


def json_response(func):
    """Decorator: Serialize response to json"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return json.dumps(result or {'error': 'No data found for your request'},
            default=serialize_to_json)

    return wrapper


def create_db_connection(database='backfill-db.sqlite'):
    if os.path.exists(database):
        try:
            connection = sqlite3.connect(database)
            connection.execute("PRAGMA foreign_keys = ON;")
            cursor = connection.cursor()
        except sqlite3.OperationalError:
            print "Could not get database connection to %s" % database
            exit(2)
    else:
        try:
            connection = sqlite3.connect(database)
            connection.execute("PRAGMA foreign_keys = ON;")
            cursor = connection.cursor()
            cursor.execute("create table jobs ("
                                "id integer primary key autoincrement, "
                                "dateadded text, "
                                "datefinished text, "
                                "revision text, "
                                "branch text, "
                                "buildername text, "
                                "buildrevs text, "
                                "analyzerevs text, "
                                "status text"
                                ")"
                                )
            connection.commit()
        except sqlite3.OperationalError:
            print "SQLError creating schema in datatbase %s" % database
            exit(2)

    return connection

def run_query(where_clause):
    db = create_db_connection()
    cursor = db.cursor()

    fields = ['id', 'dateadded', 'datefinished', 'revision', 'branch', 'buildername', 'status', 'buildrevs', 'analyzerevs']
    sql = """select %s from jobs %s;""" % (', '.join(fields), where_clause)
    print sql
    cursor.execute(sql)

    alerts = cursor.fetchall()

    retVal = []
    for alert in alerts:
        data = {}
        i = 0
        while i < len(fields):
            data[fields[i]] = alert[i]
            i += 1
        retVal.append(data)
    return retVal


def add_new_request():
    db = create_db_connection()
    cursor = db.cursor()

    jd = request.get_json()
    if jd:
        print jd
        rev = jd["revision"]
        branch = jd["branch"]
        bn = jd["buildername"]
    else:
        rev = request.form['revision']
        branch = request.form['branch']
        bn = request.form['buildername']

    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    sql = "insert into jobs (dateadded, revision, branch, buildername, status) values ('%s', '%s', '%s', '%s', 'new');" % (ts, rev, branch, bn)
    print sql
    cursor.execute(sql)
    db.commit()
    return root()

def display_request_form():
    return root()

@app.route('/new_request', methods=['GET', 'POST'])
def new_request():
    if request.method == "POST":
        return add_new_request()
    else:
        return display_request_form()

@app.route('/active_jobs')
@json_response
def get_jobs():
    return {'jobs': run_query("where status!='done'")}

@app.route("/update_status", methods=['POST'])
@json_response
def run_updatestatus_data():
    data = request.get_json()
    sql = """update jobs set status='%s' where id=%s;""" % (data['status'], data['id'])
    db = create_db_connection()
    cursor = db.cursor()
    cursor.execute(sql)
    db.commit()
    #TODO: verify via return value in alerts
    return data

@app.route("/update", methods=['POST'])
@json_response
def run_submit_data():
    retVal = {}
    data = request.get_json()
    sql = """update jobs set buildrevs='%s',analyzerevs='%s' where id=%s;""" % (data['buildrevs'], data['analyzerevs'], data['id'])
    db = create_db_connection()
    cursor = db.cursor()
    cursor.execute(sql)
    db.commit()
    return data

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    @app.route('/')
    def root():
        return app.send_static_file('jobs.html')

    @app.route('/js/<path:path>')
    def static_proxy(path):
        # send_static_file will guess the correct MIME type
        return app.send_static_file(os.path.join('js', path))


    app.run(host="0.0.0.0", port=8314)

