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
            asp=[str(site_packages)],
            usp=str(user_site_packages),
            syspath=[str(site_packages), str(tmp_dir)],
            cwd=cwd,
            stdout=stdout,
            stderr=stderr,
            enable_user_site=True,
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

    def test_info(self):
        self.do()

    def test_link(self):
        if not self.can_symlink():
            raise unittest.SkipTest('platform disallows symlinks')

        self.do('link my_project')

        self.assertTrue((self.site_packages / 'my_project').is_symlink())

        self.do('unlink my_project')
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
        self.assertTrue(self.cwd in sd.read_text())

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

        self.do('link my_project')
        self.do('link my_project')
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
        self.do('link my_file.py')
        self.assertTrue(spf.exists())
        self.do('unlink my_file')
        self.assertFalse(spf.exists())

    def test_file_develop(self):
        spf = (self.site_packages / 'my_file.sitepath.pth')
        self.do('develop my_file.py')
        self.assertTrue(spf.exists())
        self.do('undevelop my_file')
        self.assertFalse(spf.exists())

    # -- Test error conditions, invalid input, etc

    def test_link_copy(self):
        if not self.can_symlink():
            raise unittest.SkipTest('platform disallows symlinks')

        self.do('link my_project')
        with self.assertRaises(core.SitePathException):
            self.do('copy my_project')

    def test_copy_link(self):
        self.do('copy my_project')
        with self.assertRaises(core.SitePathException):
            self.do('link my_project')

    def test_conflict_link_existing(self):
        p = self.site_packages / 'my_project'
        p.mkdir()
        with self.assertRaises(core.SitePathException):
            self.do('link my_project')

    def test_conflict_unlink_existing(self):
        p = self.site_packages / 'my_project'
        p.mkdir()
        with self.assertRaises(core.SitePathFailure):
            self.do('unlink my_project')

    def test_conflict_copy_existing(self):
        p = self.site_packages / 'my_project'
        p.mkdir()
        with self.assertRaises(core.SitePathException):
            self.do('copy my_project')

    def test_bad_project(self):
        with self.assertRaises(core.SitePathException):
            self.do('link not_my_project')
        with self.assertRaises(core.SitePathException):
            self.do('copy not_my_project')
        with self.assertRaises(core.SitePathException):
            self.do('develop not_my_project')

    def test_not_found(self):
        with self.assertRaises(core.SitePathFailure):
            self.do('unlink not_my_project')

        with self.assertRaises(core.SitePathFailure):
            self.do('uncopy not_my_project')

        with self.assertRaises(core.SitePathFailure):
            self.do('undevelop not_my_project')

    @unittest.skipIf(WINDOWS, 'Windows-platform')
    def test_no_user_site(self):
        # disable user site
        self.top.asp.remove(self.top.usp)
        self.top.enable_user_site = False

        # remove write permission
        self.site_packages.chmod(0o500)
        with self.assertRaises(core.SitePathFailure):
            self.do('copy my_project')

        self.assertFalse((self.site_packages / 'my_project').is_dir())
        self.assertFalse((self.user_site_packages / 'my_project').is_dir())

    def test_missing_args(self):
        with self.assertRaises(core.SitePathException):
            self.do('link')

        with self.assertRaises(core.SitePathException):
            self.do('unlink')

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
