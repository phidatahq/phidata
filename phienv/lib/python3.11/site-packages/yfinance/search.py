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

import json as _json

from . import utils
from .const import _BASE_URL_
from .data import YfData


class Search:
    def __init__(self, query, max_results=8, news_count=8, enable_fuzzy_query=False,
                 session=None, proxy=None, timeout=30, raise_errors=True):
        """
        Fetches and organizes search results from Yahoo Finance, including stock quotes and news articles.

        Args:
            query: The search query (ticker symbol or company name).
            max_results: Maximum number of stock quotes to return (default 8).
            news_count: Number of news articles to include (default 8).
            enable_fuzzy_query: Enable fuzzy search for typos (default False).
            session: Custom HTTP session for requests (default None).
            proxy: Proxy settings for requests (default None).
            timeout: Request timeout in seconds (default 30).
            raise_errors: Raise exceptions on error (default True).
        """
        self.query = query
        self.max_results = max_results
        self.enable_fuzzy_query = enable_fuzzy_query
        self.news_count = news_count
        self.session = session
        self.proxy = proxy
        self.timeout = timeout
        self.raise_errors = raise_errors

        self._data = YfData(session=self.session)
        self._logger = utils.get_yf_logger()

        self._response = self._fetch_results()
        self._quotes = self._response.get("quotes", [])
        self._news = self._response.get("news", [])

    def _fetch_results(self):
        url = f"{_BASE_URL_}/v1/finance/search"
        params = {
            "q": self.query,
            "quotesCount": self.max_results,
            "enableFuzzyQuery": self.enable_fuzzy_query,
            "newsCount": self.news_count,
            "quotesQueryId": "tss_match_phrase_query",
            "newsQueryId": "news_cie_vespa"
        }

        self._logger.debug(f'{self.query}: Yahoo GET parameters: {str(dict(params))}')

        data = self._data.cache_get(url=url, params=params, proxy=self.proxy, timeout=self.timeout)
        if data is None or "Will be right back" in data.text:
            raise RuntimeError("*** YAHOO! FINANCE IS CURRENTLY DOWN! ***\n"
                               "Our engineers are working quickly to resolve "
                               "the issue. Thank you for your patience.")
        try:
            data = data.json()
        except _json.JSONDecodeError:
            self._logger.error(f"{self.query}: Failed to retrieve the news and received faulty response instead.")
            data = {}

        return data

    @property
    def quotes(self):
        """Get the quotes from the search results."""
        return self._quotes

    @property
    def news(self):
        """Get the news from the search results."""
        return self._news
