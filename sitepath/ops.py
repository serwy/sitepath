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

import shutil
import sys
import os

from .crumb import *
from .common import *


def _check_ident(p):
    head, tail = os.path.split(p)
    ident, _ = os.path.splitext(tail)
    if not ident.isidentifier():
        raise SitePathFailure('not a valid Python identifier: %r' % ident)
    return ident


def _uncommand(top, what):
    # helper for unlink/uncopy/undevelop
    if what.isidentifier():
        needs_origin = False
        ident = what
    else:
        p = top.abspath(what)
        head, tail = os.path.split(p)
        ident, _ = os.path.splitext(tail)
        if not ident.isidentifier():
            raise SitePathFailure('not a valid Python identifier: %r' % ident)
        needs_origin = p

    return result._using('ident, needs_origin', locals())


def symlink(top, what, cfg=None):
    stdout, stderr = top.stdout, top.stderr

    p = top.abspath(what)

    _check_ident(p)

    if not os.path.exists(p):
        raise SitePathException('path not found: %r' % p)

    head, tail = os.path.split(p)

    tried = []
    for sp in top.asp:
        dst = os.path.join(sp, tail)

        command = 'Symlinked'
        if has_crumb(dst):
            if os.path.islink(dst):
                prior = os.readlink(dst)
                if top.abspath(prior) == top.abspath(p):
                    command == 'Symlinked'
                else:
                    command = 'Relinked'
                os.remove(dst)


            if os.path.exists(dst):
                raise SitePathException('Already copied: %r' % (dst, ))

        else:
            if os.path.exists(dst):
                raise SitePathFailure('Already exists: %r' % (dst, ))


        try:
            os.symlink(p, dst, target_is_directory=True)
            _, base = os.path.split(dst)

            place_crumb(dst, {'when':top.now, 'from':p, 'how':'symlink',
                              'base':base})

            fprint(stdout, '%s: %r --> %r' % (command, dst, p))
            break
        except OSError as err:
            tried.append(str(err))

    else:
        raise SitePathFailure(
            'Unable to symlink anywhere.\n    %s' % ('\n    '.join(tried)))


def unsymlink(top, what, cfg=None):
    stdout, stderr = top.stdout, top.stderr

    x = _uncommand(top, what)

    needs_origin = x.needs_origin
    if cfg and cfg.path_to_name:
        needs_origin = False

    ident = x.ident

    tried = []
    for sp in top.asp:
        p = ident
        p = os.path.join(sp, p)

        # check for crumb
        if not has_crumb(p):
            tried.append(p + '.sitepath')
            continue

        # open the crumb, get the undo data
        c, cfile = get_crumb(p)
        base = c['base']

        target = os.path.join(sp, base)
        tried.append(target)
        if os.path.islink(target):
            rlink = os.readlink(target)
            if needs_origin:
                if needs_origin != top.abspath(rlink):
                    raise SitePathFailure('unlink path mismatch. need %r, found %r' % (
                        needs_origin, top.abspath(rlink)))

            os.remove(target)
            remove_crumb(target)
            fprint(stdout, 'Unlinked: %r --> %r' % (target, rlink))
            break
        else:
            raise SitePathFailure('Path is not a symlink: %r' % p)
    else:
        raise SitePathFailure(
            'Package not found: %r. Tried:\n    %s' % (
                ident, '\n    '.join(tried)))


def copy(top, what, cfg=None):
    stdout, stderr = top.stdout, top.stderr
    p = top.abspath(what)

    _check_ident(p)

    head, tail = os.path.split(p)
    if not os.path.exists(p):
        raise SitePathException('path not found: %r' % p)

    tried = []
    for sp in top.asp:
        dst = os.path.join(sp, tail)

        if os.path.exists(dst):
            if not has_crumb(dst):
                raise SitePathFailure(
                    'Existing package not copied by sitepath: %r' % dst)

        if os.path.islink(dst):
            raise SitePathException('Already linked: %r. Unlink it then try again.' % (dst, ))

        try:
            if has_crumb(dst):
                c, cfile = get_crumb(dst)
                fprint(stdout, 'prior crumb: ', c)

            if os.path.isdir(p):
                shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(p, dst)
            elif os.path.isfile(p):
                shutil.copy(p, dst)
            else:
                raise SitePathFailure(
                    'Expecting a directory or file: %r' % p)

            fprint(stdout, 'copied: %r --> %r' % (p, dst))

            _, base = os.path.split(dst)

            place_crumb(dst, {'when':top.now, 'from':p, 'how':'copy',
                              'base':base})
            break

        except OSError as err:
            tried.append(str(err))
            continue

    else:
        raise SitePathFailure(
            'Unable to copy anywhere.\n    %s' % ('\n    '.join(tried)))


def uncopy(top, what, cfg=None):
    stdout, stderr = top.stdout, top.stderr

    x = _uncommand(top, what)
    needs_origin = x.needs_origin

    if cfg and cfg.path_to_name:
        needs_origin = False

    ident = x.ident

    tried = []
    for sp in top.asp:
        p = ident
        p = os.path.join(sp, p)

        # check for crumbs
        if not has_crumb(p):
            tried.append(p + '.sitepath')
            continue

        # open the crumb, get the undo data
        c, cfile = get_crumb(p)
        base = c['base']

        if needs_origin:
            if needs_origin != c['from']:
                raise SitePathFailure('uncopy path mismatch. need %r, found %r' % (
                        needs_origin, c['from']))

        target = os.path.join(sp, base)

        if os.path.isdir(target):
            shutil.rmtree(target)
        elif os.path.isfile(target):
            os.remove(target)
        else:
            if os.path.exists(target):
                raise SitePathFailure('not a directory or file: %r' % target)
            # we have a crumb without a package, clear the crumb

        fprint(stdout, 'deleted crumb:', c)
        remove_crumb(target)
        fprint(stdout, 'deleted: %r' % (target,))
        break

    else:
        raise SitePathFailure(
            'Package not found: %r. Tried:\n    %s' % (
                ident, '\n    '.join(tried)))


def develop(top, what, cfg=None):
    stdout, stderr = top.stdout, top.stderr

    p = top.abspath(what)
    package = _check_ident(p)

    if not os.path.exists(p):
        raise SitePathException('path not found: %r' % p)


    devpath, filename = os.path.split(p)

    tried = []

    for sp in top.asp:
        pth = os.path.join(sp, '%s.sitepath.pth' % package)
        try:
            with open(pth, 'w') as fp:
                js = json.dumps({'when':top.now, 'from':p, 'how':'develop', 'base':package})
                print('# sitepath: %s' % js, file=fp)
                print(devpath, file=fp)
            fprint(stdout, 'Develop %r >>> %r' % (pth, devpath))
            break
        except OSError as err:
            tried.append(str(err))
    else:
        raise SitePathFailure(
            'Unable to create %s.sitepath.pth.\n    %s' % (package, '\n    '.join(tried)))


def undevelop(top, what, cfg=None):
    stdout, stderr = top.stdout, top.stderr

    x = _uncommand(top, what)
    needs_origin = x.needs_origin
    ident = x.ident

    tried = []
    for sp in top.asp:
        pth_file = '%s.sitepath.pth' % ident
        p = os.path.join(sp, pth_file)
        tried.append(p)
        if os.path.exists(p):
            os.remove(p)
            fprint(stdout, 'Undeveloped %r' % (p, ))
            break
    else:
        head, tail = os.path.split(p)
        raise SitePathFailure(
            '%r not found. Tried:\n    %s' % (
                pth_file, '\n    '.join(tried)))


def info(top, what, cfg=None):
    # print out the crumb contents
    stdout, stderr = top.stdout, top.stderr
    x = _uncommand(top, what)
    needs_origin = x.needs_origin
    ident = x.ident

    if cfg and cfg.path_to_name:
        needs_origin = False

    tried = []
    for sp in top.asp:
        base = os.path.join(sp, ident)

        c, cfile = get_crumb(base)
        p, pfile = get_pth(base + '.sitepath.pth')

        if c is None and p is None:
            tried.append(cfile)
            tried.append(pfile)
            continue

        # It is possible to have a developed and linked/copied package.
        # I'm not going to stop you.
        for d, dfile in [(c, cfile), (p, pfile)]:
            if d is None:
                continue

            kvf = '%10s: %s'  # formatting string
            fprint(stdout, 'info: %r' % ident)
            fprint(stdout, kvf % ('crumb', dfile))
            for key in sorted(d, reverse=True):
                value = d[key]

                s = []
                if key == 'from':
                    if not os.path.exists(value):
                        if 'link' in d.get('how', ''):
                            s.append('(broken)')
                        else:
                            s.append('(missing)')
                    if needs_origin:
                        if value != needs_origin:
                            s.append('(mismatched to %r)' % needs_origin)
                if s:
                    value = value + ' ' + ' '.join(s)

                fprint(stdout,  kvf % (key, value))
        break
    else:
        raise SitePathFailure(
            'Package not found: %r. Tried:\n    %s' % (
                ident, '\n    '.join(tried)))
