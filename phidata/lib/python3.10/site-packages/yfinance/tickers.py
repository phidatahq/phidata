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

from __future__ import print_function

from . import Ticker, multi


# from collections import namedtuple as _namedtuple


class Tickers:

    def __repr__(self):
        return f"yfinance.Tickers object <{','.join(self.symbols)}>"

    def __init__(self, tickers, session=None):
        tickers = tickers if isinstance(
            tickers, list) else tickers.replace(',', ' ').split()
        self.symbols = [ticker.upper() for ticker in tickers]
        self.tickers = {ticker: Ticker(ticker, session=session) for ticker in self.symbols}

        # self.tickers = _namedtuple(
        #     "Tickers", ticker_objects.keys(), rename=True
        # )(*ticker_objects.values())

    def history(self, period="1mo", interval="1d",
                start=None, end=None, prepost=False,
                actions=True, auto_adjust=True, repair=False,
                proxy=None,
                threads=True, group_by='column', progress=True,
                timeout=10, **kwargs):

        return self.download(
            period, interval,
            start, end, prepost,
            actions, auto_adjust, repair, 
            proxy,
            threads, group_by, progress,
            timeout, **kwargs)

    def download(self, period="1mo", interval="1d",
                 start=None, end=None, prepost=False,
                 actions=True, auto_adjust=True, repair=False, 
                 proxy=None,
                 threads=True, group_by='column', progress=True,
                 timeout=10, **kwargs):

        data = multi.download(self.symbols,
                              start=start, end=end,
                              actions=actions,
                              auto_adjust=auto_adjust,
                              repair=repair,
                              period=period,
                              interval=interval,
                              prepost=prepost,
                              proxy=proxy,
                              group_by='ticker',
                              threads=threads,
                              progress=progress,
                              timeout=timeout,
                              **kwargs)

        for symbol in self.symbols:
            self.tickers.get(symbol, {})._history = data[symbol]

        if group_by == 'column':
            data.columns = data.columns.swaplevel(0, 1)
            data.sort_index(level=0, axis=1, inplace=True)

        return data

    def news(self):
        return {ticker: [item for item in Ticker(ticker).news] for ticker in self.symbols}
