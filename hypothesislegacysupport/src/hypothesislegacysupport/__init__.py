# coding=utf-8
#
# This file is part of Hypothesis Legacy Support, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Hypothesis Legacy Support is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.

# Hypothesis Legacy Support is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with Hypothesis Legacy Support.
# If not, see <http://www.gnu.org/licenses/>.

from hypothesislegacysupport.version import __version__, __version_info__
from hypothesislegacysupport.compat import *  # noqa
import sys

__all__ = [
    '__version__', '__version_info__', 'GzipFile', 'bit_length',
    'sha1', 'b64encode', 'b64decode'
]

if sys.version_info[:2] != (2, 6):
    raise ImportError('hypothesislegacysupport is only for use on Python 2.6')
