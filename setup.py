from setuptools import setup
import sitepath

setup(
    name='sitepath',
    version=sitepath.__version__,
    author='Roger D. Serwy',
    author_email='roger.serwy@gmail.com',
    license='Apache v2.0',
    url="https://github.com/serwy/sitepath",
    packages=['sitepath'],
    description='the anti-packaging system',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    classifiers=[
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities',
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: Apache Software License',
    ],
)
