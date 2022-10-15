##
##   Copyright 2022 Roger D. Serwy
##
##   Licensed under the Apache License, Version 2.0 (the "License");
##   you may not use this file except in compliance with the License.
##   You may obtain a copy of the License at
##
##       http://www.apache.org/licenses/LICENSE-2.0
##
##   Unless required by applicable law or agreed to in writing, software
##   distributed under the License is distributed on an "AS IS" BASIS,
##   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##   See the License for the specific language governing permissions and
##   limitations under the License.
##

import os
import json

def norm_path(p):
    return str(p)


def place_crumb(p, d):
    f = norm_path(p) + '.sitepath'
    with open(f, 'w') as fp:
        json.dump(d, fp)


def has_crumb(p):
    f = norm_path(p) + '.sitepath'
    return os.path.isfile(f)


def remove_crumb(p):
    f = norm_path(p) + '.sitepath'
    os.remove(f)


def get_crumb(p):
    f = norm_path(p) + '.sitepath'
    if os.path.isfile(f):
        with open(f, 'r') as fp:
            src = fp.read()
        try:
            d = json.loads(src)
        except:
            d = {'contents': src}
    else:
        d = None

    return d, f


def get_pth(p):
    p = str(p)
    if not p.endswith('.sitepath.pth'):
        return None, p

    if not os.path.isfile(p):
        return None, p


    with open(p, 'r') as fp:
        lines = fp.readlines()

    d = {'pth':[]}

    for line in lines:
        if line.startswith('#:'):
            key, sep, value = line[2:].partition('=')
            if sep == '=':
                d[key]=value
            continue
        if line.startswith('# sitepath:'):
            pre,sep, js = line.partition(':')
            js = js.strip()
            try:
                d.update(json.loads(js))
            except:
                d['contents'] = js
        if line.startswith('#'):
            continue
        if not line.strip():
            continue

        d['pth'].append(line.strip())

    return d, p
