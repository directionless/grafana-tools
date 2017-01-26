#!/usr/bin/env python

# Because we use the AUTH_PROXY stuff, we are *unable* to login as
# admin. So, this is a tool to upgrade and downgrade a given user, via
# the api, to have admin rights.
#
# Interacting with grafana, via native, old, python, is pretty grotty.
# No Requests. The basic_auth stuff didn't work with a handler, so I
# manually computed the base64 header. I needed to force
# content-type. hack hack.
#
# If you have SQL you can:
#   UPDATE user SET is_admin=1 WHERE login LIKE 'seph'
#
# If you have curl, and know the id, you can:
#     curl 'localhost:3000/api/admin/users/12/permissions' \
#     -u 'admin:admin' -H "Content-Type: application/json" \
#     -X PUT --data '{"isGrafanaAdmin": true}';


from six.moves import urllib
from six.moves import configparser

import base64
import json
import sys
import argparse

permissions = {
    'admin':  { 'isGrafanaAdmin': True },
    'user':  { 'isGrafanaAdmin': False },
}

# This is a bit of a hack. We're going to attempt to read the
# grafana.ini file, and use it to populate the default values for
# admin/password
grafana_ini = configparser.RawConfigParser()
grafana_ini.read('/etc/grafana/grafana.ini')
gdefaults = {
    'user': 'admin',
    'pass': 'admin',
}
try:
    gdefaults['user'] = grafana_ini.get('security', 'admin_user')
    gdefaults['pass'] = grafana_ini.get('security', 'admin_password')
except configparser.NoOptionError:
    pass
except configparser.NoSectionError:
    pass

parser = argparse.ArgumentParser(description='Toggle grafana admin status')

parser.add_argument('--url', dest='url', default='http://localhost:3000', type=str,
                    help='What user to adjust admin state for')

parser.add_argument('--user', dest='admin', default=gdefaults['user'], type=str,
                    help='Grafana Login User')

parser.add_argument('--password', dest='password', default=gdefaults['pass'], type=str,
                    help='Grafana Login Password')

parser.add_argument('user', metavar='username', type=str,
                    help='What user to adjust admin state for')

parser.add_argument('action', choices=permissions.keys(),
                    help='What permissions to grant the user')

args = parser.parse_args()

basic_auth_string = base64.encodestring('%s:%s' % (args.admin, args.password)).rstrip()

# Find the user id
request = urllib.request.Request(args.url + '/api/users')
request.add_header("Authorization", "Basic %s" % basic_auth_string)
result = urllib.request.urlopen(request)
# result.code == 200
allusers = json.load(result)

matches = [u for u in allusers if args.user in u['login'] ]

if len(matches) == 0:
    print("No users match that")
    sys.exit(1)
elif len(matches) > 1:
    print("Too many users. Narrow it down")
    sys.exit(2)

# Now toggle the user
userid = matches[0]['id']
put_req = urllib.request.Request(args.url + "/api/admin/users/%s/permissions" % userid)
put_req.data = json.dumps(permissions[args.action])
put_req.add_header("Authorization", "Basic %s" % basic_auth_string)
put_req.add_header("Content-Type", "application/json") # this line feels like a grafana bug
put_req.get_method = lambda: 'PUT'
put_res = urllib.request.urlopen(put_req)
