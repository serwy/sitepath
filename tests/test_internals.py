import unittest
import os
import sys
import shutil
import tempfile
import pathlib

import sitepath.core

class TestInternals(unittest.TestCase):
    def setUp(self):
        tmp_dir = tempfile.mkdtemp(prefix='test_sitepath_')

        vars(self).update(locals())

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_top(self):
        top = sitepath.core.SitePathTop()
        self.assertEqual(top.syspath, sys.path)
        self.assertEqual(top.cwd, os.getcwd())

    def test_top2(self):
        sp =['/sys_a', '/sys_b']
        usp = self.tmp_dir

        top = sitepath.core.SitePathTop(
            sp=sp,
            usp=usp,
            enable_user_site=False,
            )

        self.assertEqual(top.orig_asp, sp)
        self.assertEqual(top.asp, sp)

        top.enable_user_site = True
        esp = sp + [usp]
        self.assertEqual(top.orig_asp, esp)

    def test_prefer_venv_sites(self):
        # fake a virtual environment

        v = pathlib.Path(self.tmp_dir)
        vsp = v / 'lib'/ 'site-packages'
        os.makedirs(str(vsp))
        sp = [str(v), str(vsp)]  # how venv works
        usp = self.tmp_dir
        top = sitepath.core.SitePathTop(
            sp=sp,
            usp=usp,
            enable_user_site=False,
            )
        top.env['VIRTUAL_ENV'] = str(v)


        orig = top.orig_asp
        a = top.asp

        self.assertGreater(orig.index(str(vsp)), orig.index(str(v)))
        self.assertLess(a.index(str(vsp)), a.index(str(v)))

    def test_sysdef(self):
        s = sitepath.core.SystemDefault()
        self.assertEqual(repr(s), '<system default>')


if __name__ == '__main__':
    unittest.main(verbosity=2)
