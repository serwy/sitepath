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
import pathlib
import sys
import os
import filecmp

from .crumb import *
from .common import *


def _check_ident(p):
    p = str(p)
    head, tail = os.path.split(p)
    ident, _ = os.path.splitext(tail)
    if not ident.isidentifier():
        raise SitePathFailure('not a valid Python identifier: %r' % ident)
    return ident


def _link_copy(command, top, what, flags=None):
    stdout, stderr = top.stdout, top.stderr

    origin = top.abspath(what)   # origin path of the package.
    base = origin.name
    ident = _check_ident(origin)

    if not origin.exists():
        raise SitePathException('path not found: %r' % str(origin))

    tried = []
    for sp in top.asp:
        dst = pathlib.Path(sp, base)

        if dst.exists():
            if not has_crumb(dst):
                raise SitePathFailure(
                    'Existing package not created by sitepath: %r' % dst)

            # Ensure that the target is the correct type.
            if command == 'symlink' and not dst.is_symlink():
                raise SitePathException(
                    'Target was copied, not symlinked: %r' % (str(dst), ))

            elif command == 'copy' and dst.is_symlink():
                raise SitePathException(
                    'Target was symlinked, not copied: %r' % (str(dst), ))

        # So far, if `dst` exists, it has a sitepath crumb, otherwise nothing is there.
        if command == 'symlink':
            cdir = '-->'
            try:
                if dst.exists():
                    dst.unlink()
                os.symlink(origin, dst, target_is_directory=True)
                base = dst.name

            except OSError as err:
                tried.append(str(err))
                continue

        elif command == 'copy':
            cdir = '<--'
            try:
                if origin.is_dir():
                    shutil.rmtree(dst, ignore_errors=True)
                    shutil.copytree(origin, dst)
                elif origin.is_file():
                    shutil.copy(origin, dst)
                else:
                    raise SitePathFailure(
                        'Expecting a directory or file: %r' % str(origin))
            except OSError as err:
                tried.append(str(err))
                continue

        else:
            raise SitePathFailure('unrecognized command: %r' % command)

        # Successfully completed command, now place the sitepath crumb.
        place_crumb(dst,
            {
                'when':top.now,
                'from':str(origin),
                'how': command,
                'base':base
            }
        )
        fprint(stdout, '%s: %r %s %r' % (command, str(dst), cdir, str(origin)))
        # TODO: warn if file/dir conflict
        break

    else:
        raise SitePathFailure(
            'Unable to %s anywhere.\n    %s' % (command, '\n    '.join(tried)))



def symlink(top, what, flags=None):
    return _link_copy('symlink', top, what, flags)

def copy(top, what, flags=None):
    return _link_copy('copy', top, what, flags)


def _uncommand(top, what):
    # helper for unlink/uncopy/undevelop
    origin = ''
    if what.isidentifier():
        needs_origin = False
        ident = what
    else:
        p = top.abspath(what)
        p = str(p)
        head, tail = os.path.split(p)
        ident, _ = os.path.splitext(tail)
        if not ident.isidentifier():
            raise SitePathFailure('not a valid Python identifier: %r' % ident)
        needs_origin = True
        origin = str(p)

    return result._using('ident, needs_origin, origin', locals())


def _unlink_uncopy(command, top, what, flags=None):
    stdout, stderr = top.stdout, top.stderr
    uflags = _uncommand(top, what)

    if flags and flags.path_to_name:
        uflags.needs_origin = False

    ident = uflags.ident

    tried = []
    for sp in top.asp:
        p = str(pathlib.Path(sp, ident))

        # Check for possible crumbs.
        if not has_crumb(p):  # directory crumb
            if has_crumb(p + '.py'):   # file crumb
                p = p + '.py'
            else:
                tried.append(p + '.sitepath')
                tried.append(p + '.py.sitepath')
                continue

        # Open the crumb, get the undo data.
        c, cfile = get_crumb(p)
        base = c['base']

        if uflags.needs_origin:
            # compare paths
            if uflags.origin != c['from']:
                raise SitePathFailure('%s path mismatch. need %r, found %r' % (command,
                        uflags.origin, c['from']))

        target = os.path.join(sp, base)
        tried.append(target)

        if command == 'unsymlink':
            if os.path.islink(target):
                rlink = os.readlink(target) # TODO: sanity check the link
                os.remove(target)
            else:
                raise SitePathFailure('Path is not a symlink: %r' % p)

        elif command == 'uncopy':
            if os.path.isdir(target):
                shutil.rmtree(target)
            elif os.path.isfile(target):
                os.remove(target)
            else:
                if os.path.exists(target):
                    raise SitePathFailure('not a directory or file: %r' % target)
        else:
            raise SitePathFailure('unrecongnized command: %r' % command)


        fprint(stdout, 'deleted crumb:', c)
        remove_crumb(target)
        fprint(stdout, '%s: %r' % (command, target))
        break

    else:
        raise SitePathFailure(
            'Package not found: %r. Tried:\n    %s' % (
                ident, '\n    '.join(tried)))


def uncopy(top, what, flags=None):
    return _unlink_uncopy('uncopy', top, what, flags)


def unsymlink(top, what, flags=None):
    return _unlink_uncopy('unsymlink', top, what, flags)


def develop(top, what, flags=None):
    stdout, stderr = top.stdout, top.stderr

    p = top.abspath(what)
    package = _check_ident(p)

    if not os.path.exists(p):
        raise SitePathException('path not found: %r' % p)

    devpath, filename = os.path.split(p)
    pth_file = '%s.sitepath.pth' % package

    tried = []
    for sp in top.asp:
        pth = os.path.join(sp, pth_file)
        try:
            with open(pth, 'w') as fp:
                js = json.dumps(
                    {
                        'when':top.now,
                        'from':str(p),
                        'how':'develop',
                        'base':package
                    }
                )
                print('# sitepath: %s' % js, file=fp)
                print(devpath, file=fp)

            fprint(stdout, 'develop: %r >>> %r' % (pth, devpath))
            break
        except OSError as err:
            tried.append(str(err))
    else:
        raise SitePathFailure(
            'Unable to create %r.\n    %s' % (pth_file, '\n    '.join(tried)))


def undevelop(top, what, flags=None):
    stdout, stderr = top.stdout, top.stderr
    uflags = _uncommand(top, what)
    if flags and flags.path_to_name:
        uflags.needs_origin = False

    ident = uflags.ident

    tried = []
    for sp in top.asp:
        pth_file = '%s.sitepath.pth' % ident

        p = os.path.join(sp, pth_file)

        tried.append(p)
        if os.path.exists(p):
            os.remove(p)
            fprint(stdout, 'undevelop: %r' % (p, ))
            break
    else:
        head, tail = os.path.split(p)
        raise SitePathFailure(
            '%r not found. Tried:\n    %s' % (
                pth_file, '\n    '.join(tried)))


def info(top, what, flags=None):
    # print out the crumb contents
    stdout, stderr = top.stdout, top.stderr
    uflags = _uncommand(top, what)
    ident = uflags.ident

    if flags and flags.path_to_name:
        uflags.needs_origin = False

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
            fprint(stdout, '%s:' % ident)
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
                    if uflags.needs_origin:
                        if value != uflags.origin:
                            s.append('(mismatched to %r)' % uflags.origin)
                if s:
                    value = value + ' # ' + ' '.join(s)

                fprint(stdout,  kvf % (key, repr(value)))
        break
    else:
        raise SitePathFailure(
            'Package not found: %r. Tried:\n    %s' % (
                ident, '\n    '.join(tried)))


def _compare_crumb(p):
    c, cfile = get_crumb(p)
    origin = c.get('from')
    base = c.get('base')
    if not os.path.exists(origin):
        raise SitePathFailure('MISSING: package %r origin not found: %r' % (
            base, origin))

    head, tail = os.path.split(cfile)
    src = os.path.join(head, base)
    if not os.path.exists(src):
        raise SitePathFailure('package for crumb missing: %r' % src)

    changed = False
    if os.path.isfile(src) and os.path.isfile(origin):
        if not filecmp.cmp(src, origin, shallow=False):
            changed = True
    elif os.path.isdir(src) and os.path.isdir(origin):
        dcmp = filecmp.dircmp(src, origin)
        x = []
        for attr in ['left_only', 'right_only', 'diff_files']:
            x.extend(getattr(dcmp, attr))
        if x:
            changed = True

    else:
        changed = True

    return result(locals())
