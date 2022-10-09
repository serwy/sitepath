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

import site
import sys
import os
import pathlib
from pprint import pprint
import shutil
import datetime
import json

from ._version import __version__


def fprint(file, *args, **kw):
    print(*args, file=file, **kw)


class SystemDefault:
    def __repr__(self):
        return '<system default>'

system = SystemDefault()


class SitePathTop:
    def __init__(self,
                 asp=system,
                 usp=system,
                 syspath=system,
                 cwd=system,
                 stdout=system,
                 stderr=system,
                 enable_user_site=system):

        if cwd is system:
            cwd = os.getcwd()

        if asp is system:
            asp = site.getsitepackages()[:]   # all site packages

        if usp is system:
            usp = site.getusersitepackages()  # user site packages

        if enable_user_site is system:
            enable_user_site = site.ENABLE_USER_SITE

        if enable_user_site:
            if usp is not None:
                if os.path.isdir(usp):
                    asp.append(usp)

        if syspath is system:
            syspath = sys.path.copy()

        if stdout is system:
            stdout = sys.stdout

        if stderr is system:
            stderr = sys.stderr

        vars(self).update(locals())

    def abspath(self, p):
        p = os.path.expanduser(p)
        p = os.path.expandvars(p)
        p = os.path.join(self.cwd, p)
        p = os.path.abspath(p)
        return p

    @property
    def now(self):
        return datetime.datetime.now().isoformat()

class SitePathException(ValueError):
    pass


class SitePathFailure(RuntimeError):
    # everything has been tried, nothing succeeded
    pass


def norm_path(p):
    p = str(p)
    if p.endswith('.py'):
        p = p[:-3]
    return p


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
    with open(f, 'r') as fp:
        src = fp.read()
    try:
        d = json.loads(src)
    except:
        d = {'contents': src}
    return d


def show_help(top):
    fprint(top.stdout, '''  sitepath {version}
----------------------------------
Commands available:

   link      - symlink a given file/directory to site-packages
   unlink    - unlink the given importable name, if it was linked.

   copy      - copy a given file/directory to site-packages
   uncopy    - delete a given importable name, if it was copied.

   develop   - add the parent directory of a project to a .sitepath.pth file
   undevelop - removes the .sitepath.pth file for the given importable name

   mvp       - print the contents of a simple setup.py for a given package path.
             - e.g. python -m sitepath mvp my_project > pyproject.toml

   help      - show this message
'''.format(version=__version__))


def _check_ext(what):
    package, ext  = os.path.splitext(what)
    if ext:
        raise SitePathException('Did you mean %r?' % (
            package, ))

def process(argv, top):

    stdout = top.stdout
    stderr = top.stderr


    arg = [None] * 10
    arg[:len(argv)] = argv

    cmd = arg[1]

    if cmd is None:
        info(top)
        return

    elif cmd in ['-h', '--help', 'help']:
        show_help(top)
        return

    elif cmd == 'link':
        what = arg[2]
        if what is None:
            raise SitePathException('Need a directory or file to link')

        p = top.abspath(what)
        if not os.path.exists(p):
            raise SitePathException('package not found: %r' % p)

        head, tail = os.path.split(p)

        tried = []
        for sp in top.asp:
            dst = os.path.join(sp, tail)

            if has_crumb(dst):
                if os.path.islink(dst):
                    os.remove(dst)

                if os.path.exists(dst):
                    raise SitePathException('Already copied: %r' % (dst, ))

            else:
                if os.path.exists(dst):
                    raise SitePathException('Already exists: %r' % (dst, ))

            tried.append(dst)
            try:
                os.symlink(p, dst, target_is_directory=True)
                _, base = os.path.split(dst)

                place_crumb(dst, {'when':top.now, 'from':p, 'how':'link',
                                  'base':base})

                fprint(stdout, 'Linking: %r --> %r' % (dst, p))
                break
            except OSError as err:
                fprint(stderr,
                        'Unable to link %r\n%s' % (dst, err))
        else:
            raise SitePathFailure(
                'Unable to link anywhere.\nTried:\n    %s' % ('\n    '.join(tried)))

    elif cmd == 'unlink':
        what = arg[2]
        if what is None:
            raise SitePathException('Need a project name to unlink')

        _check_ext(what)

        tried = []
        for sp in top.asp:
            p = what
            p = os.path.join(sp, p)

            # check for crumb
            if not has_crumb(p):
                tried.append(p + '.sitepath')
                continue

            # open the crumb, get the undo data
            c = get_crumb(p)
            base = c['base']

            target = os.path.join(sp, base)
            if os.path.islink(target):
                fprint(stdout, 'Unlinking: %r --> %r' % (target, os.readlink(target)))
                os.remove(target)
                remove_crumb(target)
                break
            else:
                fprint(stderr, 'Expected a symlink: %r' % p)
        else:
            raise SitePathFailure(
                'Package not found: %r\nTried:\n    %s' % (
                    what, '    \n'.join(tried)))

    elif cmd == 'copy':
        what = arg[2]
        if what is None:
            raise SitePathException('Need a directory to copy')

        p = top.abspath(what)

        head, tail = os.path.split(p)
        if not os.path.exists(p):
            raise SitePathException('project not found: %r' % p)

        for sp in top.asp:
            dst = os.path.join(sp, tail)

            if os.path.exists(dst):
                if not has_crumb(dst):
                    raise SitePathException(
                        'Existing project not copied by sitepath: %r' % dst)

            if os.path.islink(dst):
                raise SitePathException('Already linked: %r' % (dst, ))

            try:
                if has_crumb(dst):
                    c = get_crumb(dst)
                    fprint(stdout, 'prior crumb: ', c)

                fprint(stdout, 'Copying: %r --> %r' % (p, dst))
                if os.path.isdir(p):
                    shutil.rmtree(dst, ignore_errors=True)
                    shutil.copytree(p, dst)
                elif os.path.isfile(p):
                    shutil.copy(p, dst)
                else:
                    raise SitePathException(
                        'Expecting a directory or file: %r' % p)

                _, base = os.path.split(dst)

                place_crumb(dst, {'when':top.now, 'from':p, 'how':'copy',
                                  'base':base})
                break

            except OSError as err:
                fprint(stderr, 'Unable to copy: %s\n%s' % (dst, err))

        else:
            raise SitePathFailure('Unable to copy anywhere.')

    elif cmd == 'uncopy':
        what = arg[2]
        if what is None:
            raise SitePathException('Need a project name to unlink')

        _check_ext(what)

        tried = []
        for sp in top.asp:
            p = what
            p = os.path.join(sp, p)

            # check for crumbs
            if not os.path.exists(p + '.sitepath'):
                tried.append(p + '.sitepath')
                continue

            # open the crumb, get the undo data
            c = get_crumb(p)
            base = c['base']

            target = os.path.join(sp, base)
            fprint(stdout, 'Deleting: %r' % (target,))
            if os.path.isdir(target):
                shutil.rmtree(target)
            elif os.path.isfile(target):
                os.remove(target)
            else:
                # has crumb but not a dir or file
                # raise a warning
                pass
            fprint(stdout, 'deleted crumb:', c)
            remove_crumb(target)
            break

        else:
            raise SitePathFailure(
                'Package not found: %r\nTried:\n    %s' % (
                    what, '\n    '.join(tried)))

    elif cmd == 'develop':
        what = arg[2]
        if what is None:
            raise SitePathException('Need a directory to develop')

        p = top.abspath(what)
        if not os.path.exists(p):
            raise SitePathException('Package not found: %r' % p)


        devpath, filename = os.path.split(p)
        package, _  = os.path.splitext(filename)

        tried = []

        for sp in top.asp:
            p = os.path.join(sp, '%s.sitepath.pth' % package)
            try:
                with open(p, 'w') as fp:
                    print(devpath, file=fp)
                fprint(stdout, 'Developing %r in %r' % (devpath, p))
                break
            except OSError as err:
                tried.append(p)
        else:
            raise SitePathFailure('Unable to create %s.sitepath.pth' % package)

    elif cmd == 'undevelop':
        what = arg[2]
        if what is None:
            raise SitePathException('Need a project name to unlink')

        _check_ext(what)

        package = what

        tried = []
        for sp in top.asp:
            p = os.path.join(sp, '%s.sitepath.pth' % package)
            tried.append(p)
            if os.path.exists(p):
                fprint(stdout, 'Deleting %r' % (p, ))
                os.remove(p)
                break
        else:
            head, tail = os.path.split(p)
            raise SitePathFailure(
                '%r not found.\nTried:\n    %s' % (
                    tail, '\n    '.join(tried)))

    elif cmd == 'mvp':
        what = arg[2]
        if what is None:
            raise SitePathException('Need a project name')
        p = os.path.abspath(what)
        head, tail = os.path.split(p)
        name, _ = os.path.splitext(tail)

        src = '''# (redirect output) > pyproject.toml
# See: https://packaging.python.org/en/latest/tutorials/packaging-projects/
[project]
name = %s
version = "0.0.0"
# authors = [ {name="Name", email="you@example.com"}, ]
# description = ""
# readme = "README.md"
# license = {file="LICENSE.txt"}
# requires-python = ">=3.3"
# classifiers = [ "Development Status :: 1 - Planning", ]
# urls = {"Home-page" = "http://example.com'}
''' % repr(name)

        fprint(stdout, src)

    else:
        raise SitePathException('Command not recognized: %r' % cmd)


def info(top):
    stdout = top.stdout
    print = lambda *args, **kw: fprint(stdout, *args, **kw)

    print( '-' * 60)
    print( 'sitepath %s' % __version__)
    print( '-' * 60)
    print()
    v = os.environ.get('VIRTUAL_ENV', None)
    if v is not None:
        print( 'VIRTUAL_ENV=%s' % v)

    print( 'sys.executable = %r' % sys.executable)

    if 1:
        # inspired from site._script()
        print( "sys.path = [")
        for d in top.syspath:
            print( "    %r," % (d,))
        print( "]")
        def exists(path):
            if path is not None and os.path.isdir(path):
                return "exists"
            else:
                return "doesn't exist"

        print( 'USER_SITE: %r (%s)' % (top.usp, exists(top.usp)))
        print( "ENABLE_USER_SITE: %r" % (top.enable_user_site, ))

    print()
    print( 'Active site-packages:')
    for p in top.asp:
        print( '    %s' % str(p))

    print()
    print( 'Active .pth files:')
    dev = []
    for d in top.asp:
        d = pathlib.Path(d)
        pth_list = sorted(d.glob('*.pth'))
        for name in pth_list:
            print( '    %s' % str(name))
            if str(name).endswith('.sitepath.pth'):
                dev.append(name)

    syms = []
    copies = []
    for d in top.asp:
        d = pathlib.Path(d)
        if d.is_dir():
            for item in d.iterdir():
                if has_crumb(item):
                    if item.is_symlink():
                        syms.append(item)
                    else:
                        copies.append(item)

    print()
    print( 'sitepath-symlinked packages: %i found' % len(syms))
    for s in syms:
        print( '    %s --> %s' % (s, s.readlink()))

    print( 'sitepath-copied packages:    %i found' % len(copies))
    for s in copies:
        print( '    %s' % (s, ))

    print( 'sitepath-developed packages: %i found' % len(dev))
    for s in dev:
        print( '    %s' % (s, ))

    print()

    return locals()
