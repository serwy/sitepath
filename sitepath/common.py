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

def fprint(file, *args, **kw):
    print(*args, file=file, **kw)


class result:
    def __init__(self, *E, **F):
        vars(self).update(dict(*E, **F))

    @classmethod
    def _using(cls, spec, *E, **F):
        d = dict(*E, **F)
        u = {}
        for item in spec.split(','):
            item = item.strip()
            key, sep, value = item.partition('=')
            if sep == '=':
                u[key] = d[value]
            else:
                u[key] = d[key]
        return cls(u)


class SitePathException(ValueError):
    pass


class SitePathFailure(RuntimeError):
    # everything has been tried, nothing succeeded
    pass
