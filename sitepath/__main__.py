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


import sys

from . import core

argv = sys.argv[:]

top = core.SitePathTop()

try:
    core.process(argv, top)
except core.SitePathException as err:
    print('\nError:', err, file=sys.stderr)
    sys.exit(1)
except core.SitePathFailure as err:
    print('\nFailure:', err, file=sys.stderr)
    sys.exit(2)
