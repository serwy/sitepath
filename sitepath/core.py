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
import io
import pathlib
from pprint import pprint
import shutil
import datetime
import json

from ._version import __version__
from . import ops
from .crumb import *
from .common import *


class SystemDefault:
    def __repr__(self):
        return '<system default>'

system = SystemDefault()


class SitePathTop:
    def __init__(self,
                 sp=system,
                 usp=system,
                 syspath=system,
                 cwd=system,
                 stdout=system,
                 stderr=system,
                 enable_user_site=system,
                 now=system,
                 env=system):

        if cwd is system:
            cwd = os.getcwd()

        if sp is system:
            sp = site.getsitepackages()[:]   # site packages

        if usp is system:
            usp = site.getusersitepackages()  # user site packages

        if enable_user_site is system:
            enable_user_site = site.ENABLE_USER_SITE

        if syspath is system:
            syspath = sys.path.copy()

        if stdout is system:
            stdout = sys.stdout

        if stderr is system:
            stderr = sys.stderr

        if now is system:
            now = datetime.datetime.now().isoformat()

        if env is system:
            env = dict(os.environ)

        vars(self).update(locals())

    @property
    def orig_asp(self):   # all site packages
        sites = list(self.sp)
        usp = self.usp
        if self.enable_user_site:
            if usp is not None:
                if os.path.isdir(usp):
                    sites.append(usp)
        return sites

    @property
    def asp(self):
        sites = self.orig_asp
        v = self.env.get('VIRTUAL_ENV', None)
        if v is not None:
            if v in sites:
                # push the venv root to the back of the list
                # so that the venv site-packages comes first
                sites.remove(v)
                sites.append(v)
        return sites

    def abspath(self, p):
        p = os.path.expanduser(p)
        p = os.path.expandvars(p)
        p = os.path.join(self.cwd, p)
        p = os.path.abspath(p)
        return pathlib.Path(p)


def show_help(top):
    fprint(top.stdout,
'''sitepath {version}
----------------------------------

Usage:

    python -m sitepath <command> [options] [name/dirs/files]

Commands:
    symlink         Symlink a given directory/file to site-packages.
    unsymlink       Remove a symlink for a package name or directory/file.
    copy            Copy a given directory/file to site-packages.
    uncopy          Delete the package name from site-packages.
    develop         Add the parent of the dir/file to [package].sitepath.pth.
    undevelop       Remove [package].sitepath.pth.

    info            Given detailed information about packages and crumbs.
    list            List by given package type (symlinks, copies, develops).
                    Also lists copied differences with 'changed'.
    mvp             Given a name, print the content of a minimum viable
                    pyproject.toml file.

    help,
    -h, --help      Show this help message

General Options:
    -r <file>       Batch process directory/file lines in given <file>.
    -n              Translate directory/file to its package name
    -nr <file>      Treat directory/file names as package names
                    Useful for unlink/uncopy/undevelop

Examples:

    # Copy a project
    python -m sitepath copy ./my_project
    python -c "import my_project"

    # Save the copy paths, remove the copies, and then re-copy
    python -m sitepath list copies > copies.txt
    python -m sitepath uncopy -r copies.txt
    python -m sitepath copy -r copies.txt

'''.format(version=__version__))



def _proc_args(top, arg, un):
    # helper for core functionality

    if len(arg) == 0:
        return [None]

    path_to_name = False
    skip_errors = False
    todo = []

    if arg[0] == '-n':
        path_to_name = True
        arg.pop(0)

    if arg[0] in ('-r', '-nr'):  # -r for read
        if arg[0] == '-nr':
            path_to_name = True

        if arg[1] is None:
            raise SitePathException("Expecting a file.")

        file = top.abspath(arg[1])

        if not os.path.exists(file):
            raise SitePathException("File not found %r" % file)

        with open(file, 'r') as fp:
            lines = fp.readlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line[0] == '#':
                continue
            todo.append(line)
    else:
        while arg:
            item = arg.pop(0)
            if item is None:
                continue
            todo.append(item)

        if len(todo) == 0:
            todo.append(None)

    if path_to_name:
        if not un:
            fprint(top.stderr,
                   'note: using -n or -nr has an effect with un-commands only.')

    return result._using('items=todo, skip_errors, path_to_name', locals())


def indent_error(err):
    return '\n    '.join(str(err).splitlines())


def process(argv, top):

    stdout = top.stdout
    stderr = top.stderr


    arg = [None] * 10
    arg[:len(argv)] = argv

    cmd = arg[1]

    if cmd is None:
        default_info(top)
        return

    elif cmd in ['-h', '--help', 'help']:
        show_help(top)
        return

    elif cmd in ('symlink', 'unsymlink', 'link', 'unlink',
                 'copy', 'uncopy', 'develop', 'undevelop', 'info'):

        # allow for short-hand
        if cmd == 'link':
            cmd = 'symlink'
        elif cmd == 'unlink':
            cmd = 'unsymlink'


        un = cmd.startswith('un')
        cmd_info = _proc_args(top, arg[2:], un)
        collected = []


        if cmd_info.items[0] is None:
            if cmd == 'info':
                status = _get_status(top)
                cmd_info.path_to_name = False
                cmd_info.items = sorted(status.names)

        ecount = 0
        fcount = 0
        for what in cmd_info.items:
            if what is None:
                if un:
                    raise SitePathException(
                        'Need a package name, directory, or file path.')
                else:
                    raise SitePathException('Need a directory or file path.')
            try:
                func = getattr(ops, cmd)
                func(top, what, cmd_info)
            except (SitePathException, SitePathFailure) as err:
                if isinstance(err, SitePathException):
                    ecount += 1
                elif isinstance(err, SitePathFailure):
                    fcount += 1
                collected.append((what, err))

        errs = io.StringIO()
        success = len(cmd_info.items) - len(collected)

        if collected:
            fprint(errs, '(%i total)' % len(collected))
            for what, err in collected:
                fprint(errs, 'command: %s %r\n    - %s' % (cmd, what, indent_error(err)))

            if len(cmd_info.items) > 1:
                fprint(errs, 'Result (success=%i, errors=%i, failures=%i)' % (
            success, ecount, fcount))

        s = errs.getvalue()
        if fcount:
            raise SitePathFailure(s)
        elif ecount:
            raise SitePathException(s)

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
# urls = {"Home-page" = "http://example.com"}
''' % repr(name)

        fprint(stdout, src)


    elif cmd == 'list':
        what = arg[2]
        if what is None:
            raise SitePathException(
                'Expecting "symlinks", "copies", "develops", "all" , or "changed".')
        status = _get_status(top)

        todo = set()
        for what in arg[2:]:
            if what is None:
                break

            if what in ['symlinks', 'syms', 'sym', 'symlinked', 'symlink', 's',
                        'links', 'link', 'linked']:
                todo.add('symlinks')
            elif what in ['copies', 'copy', 'copied', 'c']:
                todo.add('copies')
            elif what in ['develops', 'dev', 'devs', 'developed', 'develop', 'd']:
                todo.add('develops')
            elif what in ['all']:
                todo.update(['symlinks', 'copies', 'develops'])
            elif what in ['changed', 'change', 'changes']:
                todo.add('changes')
            else:
                raise SitePathException('not recognized: %r' % what)

        if 'symlinks' in todo:
            fprint(stdout, '# sitepath-symlinked')
            for p in status.syms:
                try:
                    fprint(stdout, os.readlink(p))
                except OSError:
                    fprint(stdout, '# Error: unable to readlink %r' % p)

        if 'copies' in todo:
            fprint(stdout, '# sitepath-copied')
            for p in status.copies:
                c, cfile = get_crumb(p)
                fprint(stdout,  c.get('from', '# error: %r' % p))

        if 'changes' in todo:
            fprint(stdout, '# sitepath-copied and different')
            for p in status.copies:
                try:
                    cr = ops._compare_crumb(p)
                except SitePathFailure as f:
                    fprint(stdout, '# ' + str(f))
                    continue

                if cr.changed:
                    fprint(stdout, cr.origin)

        if 'develops' in todo:
            fprint(stdout, '# sitepath-developed')
            for d in status.dev:
                try:
                    c, cfile = get_pth(d)
                except OSError:
                    fprint(stdout, '# error: unable to open %r' % d)
                    continue

                if c is None:
                    fprint(stdout, '# error: unable to open %r' % d)
                    continue

                f = c.get('from')
                if f is None:
                    f = '# error: missing "from" in %r' % (str(d),)
                fprint(stdout, f)

    else:
        raise SitePathException('Command not recognized: %r' % cmd)


def _get_status(top):

    names = set()

    dev = []
    pth = []
    for d in top.asp:
        d = pathlib.Path(d)
        pth_list = sorted(d.glob('*.pth'))
        for name in pth_list:
            pth.append(name)
            if str(name).endswith('.sitepath.pth'):
                dev.append(name)
                n, _, _ = name.name.rsplit('.', maxsplit=2)
                names.add(n)

    syms = []
    copies = []

    for d in top.asp:
        d = pathlib.Path(d)
        if d.is_dir():
            for item in sorted(d.iterdir()):
                if has_crumb(item):
                    if item.is_symlink():
                        syms.append(item)
                        names.add(item.name)
                    else:
                        copies.append(item)
                        names.add(item.name)

    return result._using('dev, pth, syms, copies, names', locals())


def default_info(top):
    stdout = top.stdout
    print = lambda *args, **kw: fprint(stdout, *args, **kw)

    print( '-' * 60)
    print( 'sitepath %s' % __version__)
    print( '-' * 60)
    print()

    for evar in ('VIRTUAL_ENV', 'PYTHONPATH', 'PYTHONHOME'):
        v = top.env.get(evar, None)
        if v is not None:
            print( '%s=%s' % (evar, v))

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
    for p in top.orig_asp:
        print( '    %s' % str(p))

    status = _get_status(top)
    print()
    print( 'Active .pth files:')

    for name in status.pth:
        print( '    %s' % str(name))

    syms = status.syms
    copies = status.copies
    dev = status.dev

    print()
    print( 'sitepath-symlinked packages: %i found' % len(status.syms))
    for s in status.syms:
        src = s.readlink()
        if os.path.exists(src):
            print( '    %s --> %s' % (s, src))
        else:
            print( '!!! %s --> %s (broken)' % (s, src))

    print( 'sitepath-copied packages:    %i found' % len(status.copies))
    for s in status.copies:
        c, cfile = get_crumb(s)
        src = c.get('from', '# error: %r' % c)
        if os.path.exists(src):
            print( '    %s <-- %s' % (s, src))
        else:
            print( "?   %s <-- %s (doesn't exist)" % (s, src))

    print( 'sitepath-developed packages: %i found' % len(status.dev))
    for s in status.dev:
        c, cfile = get_pth(s)
        src = c.get('pth', ['# error: %r' % s])
        if len(src) == 1:
            print( '    %s  >>>  %s' % (s, src[0]))
        else:
            # the file has been modified outside sitepath
            print( '?   %s  >>>  %s' % (s, src))
    print()

    return locals()
