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

import unittest
import shutil
import tempfile
import os
import pathlib
import io
import sys
import platform


WINDOWS = (platform.system() == 'Windows')

import sitepath
from sitepath import core




def _write_text(path, s):  # Python 3.4
    with open(str(path), 'w') as fp:
        fp.write(s)

def _read_text(path):   # Python 3.4
    with open(str(path), 'r') as fp:
        return fp.read()


class TestSitePath(unittest.TestCase):

    def setUp(self):
        tmp_dir = tempfile.mkdtemp(prefix='test_sitepath_')

        tmp_dir = pathlib.Path(tmp_dir)

        my_project = tmp_dir / 'my_project'
        site_packages = tmp_dir / 'site-packages'
        user_site_packages = tmp_dir / 'user-site-packages'

        my_file = tmp_dir / 'my_file.py'

        stderr = io.StringIO()
        stdout = io.StringIO()

        if 0:
            stderr = sys.stderr
            stdout = sys.stdout

        site_packages.mkdir()
        user_site_packages.mkdir()
        my_project.mkdir()

        with open(str(my_project / '__init__.py'), 'w') as fp:
            print('project=True', file=fp)

        with open(str(my_file), 'w') as fp:
            fp.write('file=True')

        cwd = str(tmp_dir)

        self.top = core.SitePathTop(
            sp=[str(site_packages)],
            usp=str(user_site_packages),
            syspath=[str(site_packages), str(tmp_dir)],
            cwd=cwd,
            stdout=stdout,
            stderr=stderr,
            enable_user_site=True,
            now='1999-12-31T23:59:59.999999',
        )

        vars(self).update(locals())


    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # -- Test working cases

    def do(self, s=''):
        argv = [''] + s.split()
        core.process(argv, self.top)


    def can_symlink(self):
        tmp = str(self.tmp_dir)
        if not hasattr(self, '_can_symlink'):
            # Windows requires special permissions to be able to symlink
            with open(tmp + '/_base', 'w') as fp:
                fp.write('base')
            try:
                os.symlink(tmp + '/_base', tmp + '/_symbase')
                self._can_symlink = True
            except OSError:
                self._can_symlink = False

        return self._can_symlink

    def test_default_info(self):
        self.do()

    def test_link(self):
        if not self.can_symlink():
            raise unittest.SkipTest('platform disallows symlinks')

        self.do('symlink my_project')

        p = (self.site_packages / 'my_project')
        self.assertTrue(p.is_symlink())
        self.assertEqual(os.readlink(str(p)), str(self.my_project))

        self.do('unsymlink my_project')
        self.assertFalse((self.site_packages / 'my_project').exists())


    def test_copy(self):
        self.do('copy my_project')

        self.assertFalse((self.site_packages / 'my_project').is_symlink())
        self.assertTrue((self.site_packages / 'my_project').is_dir())

        self.do('uncopy my_project')
        self.assertFalse((self.site_packages / 'my_project').exists())

    def test_develop(self):
        self.do('develop my_project')

        sd = self.site_packages / 'my_project.sitepath.pth'
        self.assertTrue(sd.exists())
        self.assertTrue(self.cwd in _read_text(sd))

        self.do('undevelop my_project')
        self.assertFalse(sd.exists())

    @unittest.skipIf(WINDOWS, 'Windows-platform')
    def test_fall_through(self):
        # remove write permission
        self.site_packages.chmod(0o500)
        self.do('copy my_project')
        self.assertFalse((self.site_packages / 'my_project').is_dir())
        self.assertTrue((self.user_site_packages / 'my_project').is_dir())

    def test_relink(self):
        if not self.can_symlink():
            raise unittest.SkipTest('platform disallows symlinks')

        self.do('symlink my_project')
        self.do('symlink my_project')
        self.assertTrue((self.site_packages / 'my_project').is_symlink())

    def test_recopy(self):
        self.do('copy my_project')
        self.do('copy my_project')
        self.assertTrue((self.site_packages / 'my_project').is_dir())

    def test_redevelop(self):
        self.assertFalse((self.site_packages / 'my_project.sitepath.pth').exists())
        self.do('develop my_project')
        self.assertTrue((self.site_packages / 'my_project.sitepath.pth').exists())
        self.do('develop my_project')
        self.assertTrue((self.site_packages / 'my_project.sitepath.pth').exists())

    def test_file_copy(self):
        spf = (self.site_packages / 'my_file.py')
        self.do('copy my_file.py')
        self.assertTrue(spf.exists())
        self.do('uncopy my_file')
        self.assertFalse(spf.exists())

    def test_file_link(self):
        if not self.can_symlink():
            raise unittest.SkipTest('platform disallows symlinks')

        spf = (self.site_packages / 'my_file.py')
        self.do('symlink my_file.py')
        self.assertTrue(spf.exists())
        self.do('unsymlink my_file')
        self.assertFalse(spf.exists())

    def test_file_develop(self):
        spf = (self.site_packages / 'my_file.sitepath.pth')
        self.do('develop my_file.py')
        self.assertTrue(spf.exists())
        self.do('undevelop my_file')
        self.assertFalse(spf.exists())

    def test_file_develop_contents(self):
        spf = (self.site_packages / 'my_file.sitepath.pth')
        self.do('develop my_file.py')
        self.assertTrue(spf.exists())

        pth, file = sitepath.crumb.get_pth(spf)
        self.assertEqual(pth['pth'][0], str(self.tmp_dir))
        self.assertEqual(pth['from'], str(self.my_file))

    def test_list_has_develop(self):
        self.do('develop my_file.py')

        x = io.StringIO()
        self.top.stdout = x
        self.do('list develops')

        v = x.getvalue().splitlines()
        v_active = [i for i in v if i.strip() and not i.startswith('#')]
        self.assertTrue(str(self.my_file) in v_active)

    def test_help(self):
        self.do('help')
        self.do('-h')
        self.do('--help')

    def test_copy_from_list(self):
        spf = (self.site_packages / 'my_file.py')
        self.assertFalse(spf.exists())

        req_file = self.tmp_dir / 'reqs.txt'
        _write_text(req_file, str(self.my_file))

        self.do('copy -r ./reqs.txt')
        self.assertTrue(spf.exists())

    def test_develop_from_list(self):
        sdf = self.site_packages / 'my_file.sitepath.pth'
        sdd = self.site_packages / 'my_project.sitepath.pth'
        self.assertFalse(sdf.exists())
        self.assertFalse(sdd.exists())


        req_file = self.tmp_dir / 'reqs.txt'
        _write_text(req_file, '\n'.join([
            str(self.my_project),
            str(self.my_file)]))

        self.do('develop -r ./reqs.txt')
        self.assertTrue(sdd.exists())
        self.assertTrue(sdf.exists())

    def test_link_from_list(self):
        if not self.can_symlink():
            raise unittest.SkipTest('platform disallows symlinks')

        spf = (self.site_packages / 'my_file.py')
        self.assertFalse(spf.exists())

        req_file = self.tmp_dir / 'reqs.txt'
        _write_text(req_file, str(self.my_file))

        self.do('symlink -r ./reqs.txt')
        self.assertTrue(spf.is_symlink())

    def test_list_has_copy(self):
        self.do('copy my_file.py')

        x = io.StringIO()
        self.top.stdout = x
        self.do('list copies')

        v = x.getvalue()
        self.assertTrue(str(self.my_file) in v)

    def test_info(self):
        self.do('info')
        with self.assertRaises(core.SitePathFailure):
            self.do('info my_project')
        self.do('copy my_project')
        self.do('info my_project')

    # -- Test error conditions, invalid input, etc

    def test_link_copy(self):
        if not self.can_symlink():
            raise unittest.SkipTest('platform disallows symlinks')

        self.do('symlink my_project')
        with self.assertRaises(core.SitePathException):
            self.do('copy my_project')

    def test_copy_link(self):
        self.do('copy my_project')
        with self.assertRaises(core.SitePathException):
            self.do('symlink my_project')

    def test_conflict_link_existing(self):
        p = self.site_packages / 'my_project'
        p.mkdir()
        with self.assertRaises(core.SitePathFailure):
            self.do('symlink my_project')

    def test_conflict_unlink_existing(self):
        p = self.site_packages / 'my_project'
        p.mkdir()
        with self.assertRaises(core.SitePathFailure):
            self.do('unsymlink my_project')

    def test_conflict_copy_existing(self):
        p = self.site_packages / 'my_project'
        p.mkdir()
        with self.assertRaises(core.SitePathFailure):
            self.do('copy my_project')

    def test_bad_project(self):
        with self.assertRaises(core.SitePathException):
            self.do('symlink not_my_project')
        with self.assertRaises(core.SitePathException):
            self.do('copy not_my_project')
        with self.assertRaises(core.SitePathException):
            self.do('develop not_my_project')

    def test_not_found(self):
        with self.assertRaises(core.SitePathFailure):
            self.do('unsymlink not_my_project')

        with self.assertRaises(core.SitePathFailure):
            self.do('uncopy not_my_project')

        with self.assertRaises(core.SitePathFailure):
            self.do('undevelop not_my_project')

    @unittest.skipIf(WINDOWS, 'Windows-platform')
    def test_no_user_site(self):
        # disable user site
        self.top.enable_user_site = False

        # remove write permission
        self.site_packages.chmod(0o500)
        with self.assertRaises(core.SitePathFailure):
            self.do('copy my_project')

        self.assertFalse((self.site_packages / 'my_project').is_dir())
        self.assertFalse((self.user_site_packages / 'my_project').is_dir())

    def test_missing_args(self):
        with self.assertRaises(core.SitePathException):
            self.do('symlink')

        with self.assertRaises(core.SitePathException):
            self.do('unsymlink')

        with self.assertRaises(core.SitePathException):
            self.do('copy')

        with self.assertRaises(core.SitePathException):
            self.do('uncopy')

        with self.assertRaises(core.SitePathException):
            self.do('develop')

        with self.assertRaises(core.SitePathException):
            self.do('undevelop')

    def test_bad_command(self):
        with self.assertRaises(core.SitePathException):
            self.do('invalid_command')

    def test_non_identifier(self):
        with self.assertRaises(core.SitePathFailure):
            self.do('symlink not-identifier')

        with self.assertRaises(core.SitePathFailure):
            self.do('copy not-identifier')

        with self.assertRaises(core.SitePathFailure):
            self.do('develop not-identifier')


    def test_mismatch_uncopy_from_list(self):
        # create a different my_file, so that uncopy
        # catches the wrong path
        other_file = self.my_project / 'my_file.py'
        _write_text(other_file, 'x=1')

        spf = (self.site_packages / 'my_file.py')
        self.do('copy my_project/my_file.py')

        req_file = self.tmp_dir / 'reqs.txt'
        _write_text(req_file, str(self.my_file))

        with self.assertRaises(core.SitePathFailure):
            self.do('uncopy -r ./reqs.txt')

        self.do('uncopy -nr ./reqs.txt')

    def test_missing_uncopy_from_list(self):
        # create a different my_file, so that uncopy
        # catches the wrong path

        req_file = self.tmp_dir / 'reqs.txt'
        _write_text(req_file, str(self.my_file))

        with self.assertRaises(core.SitePathFailure):
            self.do('uncopy -r ./reqs.txt')

    def test_mismatch_direct(self):
        spf = (self.site_packages / 'my_file.py')
        self.do('copy my_file.py')
        self.do('uncopy my_file.py')
        self.assertFalse(spf.exists())

        self.do('copy my_file.py')
        with self.assertRaises(core.SitePathFailure):
            self.do('uncopy my_project/my_file.py')
        self.assertTrue(spf.exists())

        self.do('copy my_file.py')
        # deliberate mismatch, read as a name with -n
        self.do('uncopy -n my_project/my_file.py')
        self.assertFalse(spf.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
