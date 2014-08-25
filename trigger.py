#! /usr/bin/env python
# This script is designed to trigger a job arbitrarily
# http://johnzeller.com/blog/2014/03/12/triggering-of-arbitrary-buildstests-is-now-possible/
#
# KNOWN ISSUES:
# * tbpl/self-serve will not show up your job running - bug 981825
#
# SETUP:
# * Install requests

import argparse
import getpass
import json

import requests

parser = argparse.ArgumentParser()
parser.add_argument('--buildername', dest='buildername', required=True)
parser.add_argument('--branch', dest='branch', required=True)
parser.add_argument('--rev', dest='revision', required=True)
parser.add_argument('--file', dest='files', action='append')
parser.add_argument('--user', dest='user', default=None)
parser.add_argument('--password', dest='password', default=None)
args = parser.parse_args()

branch = args.branch
revision = args.revision
buildername = args.buildername
files = args.files or []

def all_files_are_reachable(files):
    ''' All files should be reachable or requirying basic http authentication
    '''
    reachable_files = True
    for file in files:
        if file.startswith('http://pvtbuilds'):
            continue
        r = requests.head(file)
        if r.status_code != 200 and r.status_code != 401:
            # 401 files to us can be reachable within the releng network
            print "Status code: %d - The following files cannot be reached: %s" \
                    % (r.status_code, file)
            reachable_files = False

    return reachable_files

assert all_files_are_reachable(files), "All files should be reachable"

# Build jobs require no file
# Talos jobs require the installer
# Test jobs require the installer + a tests.zip
assert len(files) <= 2, "You have specified more than 2 files"

payload = {}
# Adding the properties here is so tbpl can show the job as they run
payload['properties'] = json.dumps({"branch": branch, "revision": revision})
payload['files'] = json.dumps(files)

url = r'''https://secure.pub.build.mozilla.org/buildapi/self-serve/%s/builders/%s/%s''' % \
        (branch, buildername, revision)

def make_request():
    auth = None
    if args.user and not args.password:
        args.password = getpass.getpass(prompt="LDAP password: ")

    if args.user and args.password:
        auth = (args.user, args.password)
    return requests.post(url, data=payload, auth=auth)

r = make_request()
if 400 <= int(r.status_code) < 500:
    args.user = raw_input("LDAP username: ")
    r = make_request()

print "You return code is: %s" % r.status_code
print "See your running jobs in here:"
print "https://secure.pub.build.mozilla.org/buildapi/revision/%s/%s" % (branch, revision)
