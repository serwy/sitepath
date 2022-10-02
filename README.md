# sitepath - the anti-packaging system

When making an importable Python library, there needs to be a middle ground between:

1. writing some code, and
2. packaging that can publish to PyPI.

Your code's directory is a package already. No extra packaging is required.

Using `sitepath` along with `pip` can allow locally developed code to coexist with PyPI-available libraries.

## Examples

The directory `my_project` has your Python code. Let's make it importable, work within virtual environments, and not need setup.py.

    python -m sitepath link my_project/

Done. It symlinked the directory to a user-writable site-packages directory.

If you don't want it importable anymore:

    python -m sitepath unlink my_project

Done.

On Windows, you might get an error because symlinks are not supported unless you have [special permissions.](https://docs.python.org/3/library/os.html#os.symlink)  Instead, you can use:

    python -m sitepath copy my_project/

This creates a separate copy of your code in a user-writable site-packages directory.

If you want to remove it:

    python -m sitepath uncopy my_project

If you like the using `python setup.py develop` or editable installs with `pip install -e` for development:

    python -m sitepath develop my_project/

This will add the given project path to `my_project.sitepath.pth` in a user-writeable site-packages directory.

If you want to stop developing:

    python -m sitepath undevelop my_project

which will remove its `.pth` file from site-packages.


## Installing

The `sitepath` anti-packaging system can bootstrap itself (assuming you have `sitepath/` in your current working directory).

    python -m sitepath copy sitepath

But if you really want it from PyPI:

    pip install sitepath


## Useful Features

Calling `python -m sitepath` prints out a useful information about your Python (virtual) environment:

- virtual environment variables
- sys.executable
- sys.path
- user site-packages path
- active site-packages
- active `.pth` files
- `sitepath` symlinks/copies/develops

```
------------------------------------------------------------
sitepath 0.3.0
------------------------------------------------------------

VIRTUAL_ENV=/home/serwy/venv-py/iso
sys.executable = '/home/serwy/venv-py/iso/bin/python'
sys.path = [
    '/home/serwy',
    '/usr/lib/python310.zip',
    '/usr/lib/python3.10',
    '/usr/lib/python3.10/lib-dynload',
    '/home/serwy/venv-py/iso/lib/python3.10/site-packages',
]
USER_SITE: '/home/serwy/.local/lib/python3.10/site-packages' (exists)
ENABLE_USER_SITE: False

Active site-packages:
    /home/serwy/venv-py/iso/lib/python3.10/site-packages

Active .pth files:
    /home/serwy/venv-py/iso/lib/python3.10/site-packages/distutils-precedence.pth

sitepath-symlinked packages: 1 found
    /home/serwy/venv-py/iso/lib/python3.10/site-packages/sitepath --> /home/serwy/gitea/my-sitepath/sitepath
sitepath-copied packages:    0 found
sitepath-developed packages: 0 found

```

### Available Commands

To see the list of commands:

    python -m sitepath help

They are:
- `link [directory]`
- `unlink [name]`
- `copy [directory]`
- `uncopy [name]`
- `develop [directory]`
- `undevelop [name]`
- `mvp [name]`
- `help`

### Minimum Viable Packaging

If you want to have an initial setup.py, use the `mvp` command:

    python -m sitepath mvp my_project > setup.py

__This `setup.py` file should NOT be used to distribute the project on PyPI.__ It's missing many required fields.

## Commentary

### Developing with .pth files
The `develop` command takes its name from the setuptools interface.
It adds the project directory to `sys.path` automatically, by
placing the path in `site-packages/easy-install.pth`.

The downside of using `develop` (from setup.py and from sitepath) is that everything in the path is potentially top-level importable, since the path is added to `sys.path`. This is a consequence of using `.pth` files.

The preferred method is to use `link` instead of `develop`, if your platform permits it.

### Modifying site-packages

Commands that modify a site-packages directory leave a `[package].sitepath` crumb file for each package it copies/links, and this crumb is needed to modify or remove an existing package. This crumb distinguishes sitepath packages from everything else.

### Packaging and Distribution

Using `sitepath` removes the need of dealing with the tedious minutia of PyPA packaging requirements from early development stages. In time, more packaging may be needed, or sitepath may be adequate for your needs, especially for internally developed code without an internal package repository.

### Symbolic Links

Unix, Linux, and MacOS have had symbolic links for decades, available without needing special privileges. While Windows has support for symbolic links, using them requires privileged permissions because of the implications of that platform's legacy design choices.

## See Also:
- Standard Library:
    - https://docs.python.org/3/library/site.html
        - For information about `.pth` files during Python initialization
- Packaging:
    - https://packaging.python.org/en/latest/tutorials/packaging-projects/
    - https://docs.python.org/3/distributing/index.html#publishing-python-packages
    - https://packaging.python.org/en/latest/guides/tool-recommendations/#packaging-tool-recommendations
- Symlinks on Windows:
    - https://learn.microsoft.com/en-us/windows/security/threat-protection/security-policy-settings/create-symbolic-links
    - https://docs.python.org/3/library/os.html#os.symlink
