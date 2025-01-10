#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# yfinance - market data downloader
# https://github.com/ranaroussi/yfinance
#
# Copyright 2017-2019 Ran Aroussi
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from . import version
from .search import Search
from .ticker import Ticker
from .tickers import Tickers
from .multi import download
from .utils import enable_debug_mode
from .cache import set_tz_cache_location
from .domain.sector import Sector
from .domain.industry import Industry
from .screener.screener import Screener
from .screener.screener_query import EquityQuery

__version__ = version.version
__author__ = "Ran Aroussi"

import warnings
warnings.filterwarnings('default', category=DeprecationWarning, module='^yfinance')

__all__ = ['download', 'Search', 'Ticker', 'Tickers', 'enable_debug_mode', 'set_tz_cache_location', 'Sector',
           'Industry', 'EquityQuery', 'Screener']
