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

from io import StringIO
import json as _json
import warnings
from typing import Optional, Union
from urllib.parse import quote as urlencode

import pandas as pd
import requests
from datetime import date

from . import utils, cache
from .data import YfData
from .exceptions import YFEarningsDateMissing
from .scrapers.analysis import Analysis
from .scrapers.fundamentals import Fundamentals
from .scrapers.holders import Holders
from .scrapers.quote import Quote, FastInfo
from .scrapers.history import PriceHistory
from .scrapers.funds import FundsData

from .const import _BASE_URL_, _ROOT_URL_


class TickerBase:
    def __init__(self, ticker, session=None, proxy=None):
        self.ticker = ticker.upper()
        self.proxy = proxy
        self.session = session
        self._tz = None

        self._isin = None
        self._news = []
        self._shares = None

        self._earnings_dates = {}

        self._earnings = None
        self._financials = None

        # accept isin as ticker
        if utils.is_isin(self.ticker):
            self.ticker = utils.get_ticker_by_isin(self.ticker, None, session)

        self._data: YfData = YfData(session=session)

        # self._price_history = PriceHistory(self._data, self.ticker)
        self._price_history = None  # lazy-load
        self._analysis = Analysis(self._data, self.ticker)
        self._holders = Holders(self._data, self.ticker)
        self._quote = Quote(self._data, self.ticker)
        self._fundamentals = Fundamentals(self._data, self.ticker)
        self._funds_data = None

        self._fast_info = None

    @utils.log_indent_decorator
    def history(self, *args, **kwargs) -> pd.DataFrame:
        return self._lazy_load_price_history().history(*args, **kwargs)

    # ------------------------

    def _lazy_load_price_history(self):
        if self._price_history is None:
            self._price_history = PriceHistory(self._data, self.ticker, self._get_ticker_tz(self.proxy, timeout=10))
        return self._price_history

    def _get_ticker_tz(self, proxy, timeout):
        proxy = proxy or self.proxy
        if self._tz is not None:
            return self._tz
        c = cache.get_tz_cache()
        tz = c.lookup(self.ticker)

        if tz and not utils.is_valid_timezone(tz):
            # Clear from cache and force re-fetch
            c.store(self.ticker, None)
            tz = None

        if tz is None:
            tz = self._fetch_ticker_tz(proxy, timeout)

            if utils.is_valid_timezone(tz):
                # info fetch is relatively slow so cache timezone
                c.store(self.ticker, tz)
            else:
                tz = None

        self._tz = tz
        return tz

    @utils.log_indent_decorator
    def _fetch_ticker_tz(self, proxy, timeout):
        # Query Yahoo for fast price data just to get returned timezone
        proxy = proxy or self.proxy
        logger = utils.get_yf_logger()

        params = {"range": "1d", "interval": "1d"}

        # Getting data from json
        url = f"{_BASE_URL_}/v8/finance/chart/{self.ticker}"

        try:
            data = self._data.cache_get(url=url, params=params, proxy=proxy, timeout=timeout)
            data = data.json()
        except Exception as e:
            logger.error(f"Failed to get ticker '{self.ticker}' reason: {e}")
            return None
        else:
            error = data.get('chart', {}).get('error', None)
            if error:
                # explicit error from yahoo API
                logger.debug(f"Got error from yahoo api for ticker {self.ticker}, Error: {error}")
            else:
                try:
                    return data["chart"]["result"][0]["meta"]["exchangeTimezoneName"]
                except Exception as err:
                    logger.error(f"Could not get exchangeTimezoneName for ticker '{self.ticker}' reason: {err}")
                    logger.debug("Got response: ")
                    logger.debug("-------------")
                    logger.debug(f" {data}")
                    logger.debug("-------------")
        return None

    def get_recommendations(self, proxy=None, as_dict=False):
        """
        Returns a DataFrame with the recommendations
        Columns: period  strongBuy  buy  hold  sell  strongSell
        """
        self._quote.proxy = proxy or self.proxy
        data = self._quote.recommendations
        if as_dict:
            return data.to_dict()
        return data

    def get_recommendations_summary(self, proxy=None, as_dict=False):
        return self.get_recommendations(proxy=proxy, as_dict=as_dict)

    def get_upgrades_downgrades(self, proxy=None, as_dict=False):
        """
        Returns a DataFrame with the recommendations changes (upgrades/downgrades)
        Index: date of grade
        Columns: firm toGrade fromGrade action
        """
        self._quote.proxy = proxy or self.proxy
        data = self._quote.upgrades_downgrades
        if as_dict:
            return data.to_dict()
        return data

    def get_calendar(self, proxy=None) -> dict:
        self._quote.proxy = proxy or self.proxy
        return self._quote.calendar

    def get_sec_filings(self, proxy=None) -> dict:
        self._quote.proxy = proxy or self.proxy
        return self._quote.sec_filings

    def get_major_holders(self, proxy=None, as_dict=False):
        self._holders.proxy = proxy or self.proxy
        data = self._holders.major
        if as_dict:
            return data.to_dict()
        return data

    def get_institutional_holders(self, proxy=None, as_dict=False):
        self._holders.proxy = proxy or self.proxy
        data = self._holders.institutional
        if data is not None:
            if as_dict:
                return data.to_dict()
            return data

    def get_mutualfund_holders(self, proxy=None, as_dict=False):
        self._holders.proxy = proxy or self.proxy
        data = self._holders.mutualfund
        if data is not None:
            if as_dict:
                return data.to_dict()
            return data

    def get_insider_purchases(self, proxy=None, as_dict=False):
        self._holders.proxy = proxy or self.proxy
        data = self._holders.insider_purchases
        if data is not None:
            if as_dict:
                return data.to_dict()
            return data

    def get_insider_transactions(self, proxy=None, as_dict=False):
        self._holders.proxy = proxy or self.proxy
        data = self._holders.insider_transactions
        if data is not None:
            if as_dict:
                return data.to_dict()
            return data

    def get_insider_roster_holders(self, proxy=None, as_dict=False):
        self._holders.proxy = proxy or self.proxy
        data = self._holders.insider_roster
        if data is not None:
            if as_dict:
                return data.to_dict()
            return data

    def get_info(self, proxy=None) -> dict:
        self._quote.proxy = proxy or self.proxy
        data = self._quote.info
        return data

    def get_fast_info(self, proxy=None):
        if self._fast_info is None:
            self._fast_info = FastInfo(self, proxy=proxy)
        return self._fast_info

    @property
    def basic_info(self):
        warnings.warn("'Ticker.basic_info' is deprecated and will be removed in future, Switch to 'Ticker.fast_info'", DeprecationWarning)
        return self.fast_info

    def get_sustainability(self, proxy=None, as_dict=False):
        self._quote.proxy = proxy or self.proxy
        data = self._quote.sustainability
        if as_dict:
            return data.to_dict()
        return data

    def get_analyst_price_targets(self, proxy=None) -> dict:
        """
        Keys:   current  low  high  mean  median
        """
        self._analysis.proxy = proxy or self.proxy
        data = self._analysis.analyst_price_targets
        return data

    def get_earnings_estimate(self, proxy=None, as_dict=False):
        """
        Index:      0q  +1q  0y  +1y
        Columns:    numberOfAnalysts  avg  low  high  yearAgoEps  growth
        """
        self._analysis.proxy = proxy or self.proxy
        data = self._analysis.earnings_estimate
        return data.to_dict() if as_dict else data

    def get_revenue_estimate(self, proxy=None, as_dict=False):
        """
        Index:      0q  +1q  0y  +1y
        Columns:    numberOfAnalysts  avg  low  high  yearAgoRevenue  growth
        """
        self._analysis.proxy = proxy or self.proxy
        data = self._analysis.revenue_estimate
        return data.to_dict() if as_dict else data

    def get_earnings_history(self, proxy=None, as_dict=False):
        """
        Index:      pd.DatetimeIndex
        Columns:    epsEstimate  epsActual  epsDifference  surprisePercent
        """
        self._analysis.proxy = proxy or self.proxy
        data = self._analysis.earnings_history
        return data.to_dict() if as_dict else data

    def get_eps_trend(self, proxy=None, as_dict=False):
        """
        Index:      0q  +1q  0y  +1y
        Columns:    current  7daysAgo  30daysAgo  60daysAgo  90daysAgo
        """
        self._analysis.proxy = proxy or self.proxy
        data = self._analysis.eps_trend
        return data.to_dict() if as_dict else data

    def get_eps_revisions(self, proxy=None, as_dict=False):
        """
        Index:      0q  +1q  0y  +1y
        Columns:    upLast7days  upLast30days  downLast7days  downLast30days
        """
        self._analysis.proxy = proxy or self.proxy
        data = self._analysis.eps_revisions
        return data.to_dict() if as_dict else data

    def get_growth_estimates(self, proxy=None, as_dict=False):
        """
        Index:      0q  +1q  0y  +1y +5y -5y
        Columns:    stock  industry  sector  index
        """
        self._analysis.proxy = proxy or self.proxy
        data = self._analysis.growth_estimates
        return data.to_dict() if as_dict else data

    def get_earnings(self, proxy=None, as_dict=False, freq="yearly"):
        """
        :Parameters:
            as_dict: bool
                Return table as Python dict
                Default is False
            freq: str
                "yearly" or "quarterly"
                Default is "yearly"
            proxy: str
                Optional. Proxy server URL scheme
                Default is None
        """
        self._fundamentals.proxy = proxy or self.proxy
        if self._fundamentals.earnings is None:
            return None
        data = self._fundamentals.earnings[freq]
        if as_dict:
            dict_data = data.to_dict()
            dict_data['financialCurrency'] = 'USD' if 'financialCurrency' not in self._earnings else self._earnings[
                'financialCurrency']
            return dict_data
        return data

    def get_income_stmt(self, proxy=None, as_dict=False, pretty=False, freq="yearly"):
        """
        :Parameters:
            as_dict: bool
                Return table as Python dict
                Default is False
            pretty: bool
                Format row names nicely for readability
                Default is False
            freq: str
                "yearly" or "quarterly"
                Default is "yearly"
            proxy: str
                Optional. Proxy server URL scheme
                Default is None
        """
        self._fundamentals.proxy = proxy or self.proxy

        data = self._fundamentals.financials.get_income_time_series(freq=freq, proxy=proxy)

        if pretty:
            data = data.copy()
            data.index = utils.camel2title(data.index, sep=' ', acronyms=["EBIT", "EBITDA", "EPS", "NI"])
        if as_dict:
            return data.to_dict()
        return data

    def get_incomestmt(self, proxy=None, as_dict=False, pretty=False, freq="yearly"):
        return self.get_income_stmt(proxy, as_dict, pretty, freq)

    def get_financials(self, proxy=None, as_dict=False, pretty=False, freq="yearly"):
        return self.get_income_stmt(proxy, as_dict, pretty, freq)

    def get_balance_sheet(self, proxy=None, as_dict=False, pretty=False, freq="yearly"):
        """
        :Parameters:
            as_dict: bool
                Return table as Python dict
                Default is False
            pretty: bool
                Format row names nicely for readability
                Default is False
            freq: str
                "yearly" or "quarterly"
                Default is "yearly"
            proxy: str
                Optional. Proxy server URL scheme
                Default is None
        """
        self._fundamentals.proxy = proxy or self.proxy

        data = self._fundamentals.financials.get_balance_sheet_time_series(freq=freq, proxy=proxy)

        if pretty:
            data = data.copy()
            data.index = utils.camel2title(data.index, sep=' ', acronyms=["PPE"])
        if as_dict:
            return data.to_dict()
        return data

    def get_balancesheet(self, proxy=None, as_dict=False, pretty=False, freq="yearly"):
        return self.get_balance_sheet(proxy, as_dict, pretty, freq)

    def get_cash_flow(self, proxy=None, as_dict=False, pretty=False, freq="yearly") -> Union[pd.DataFrame, dict]:
        """
        :Parameters:
            as_dict: bool
                Return table as Python dict
                Default is False
            pretty: bool
                Format row names nicely for readability
                Default is False
            freq: str
                "yearly" or "quarterly"
                Default is "yearly"
            proxy: str
                Optional. Proxy server URL scheme
                Default is None
        """
        self._fundamentals.proxy = proxy or self.proxy

        data = self._fundamentals.financials.get_cash_flow_time_series(freq=freq, proxy=proxy)

        if pretty:
            data = data.copy()
            data.index = utils.camel2title(data.index, sep=' ', acronyms=["PPE"])
        if as_dict:
            return data.to_dict()
        return data

    def get_cashflow(self, proxy=None, as_dict=False, pretty=False, freq="yearly"):
        return self.get_cash_flow(proxy, as_dict, pretty, freq)

    def get_dividends(self, proxy=None) -> pd.Series:
        return self._lazy_load_price_history().get_dividends(proxy)

    def get_capital_gains(self, proxy=None) -> pd.Series:
        return self._lazy_load_price_history().get_capital_gains(proxy)

    def get_splits(self, proxy=None) -> pd.Series:
        return self._lazy_load_price_history().get_splits(proxy)

    def get_actions(self, proxy=None) -> pd.Series:
        return self._lazy_load_price_history().get_actions(proxy)

    def get_shares(self, proxy=None, as_dict=False) -> Union[pd.DataFrame, dict]:
        self._fundamentals.proxy = proxy or self.proxy
        data = self._fundamentals.shares
        if as_dict:
            return data.to_dict()
        return data

    @utils.log_indent_decorator
    def get_shares_full(self, start=None, end=None, proxy=None):
        logger = utils.get_yf_logger()

        # Process dates
        tz = self._get_ticker_tz(proxy=proxy, timeout=10)
        dt_now = pd.Timestamp.utcnow().tz_convert(tz)
        if start is not None:
            start_ts = utils._parse_user_dt(start, tz)
            start = pd.Timestamp.fromtimestamp(start_ts).tz_localize("UTC").tz_convert(tz)
        if end is not None:
            end_ts = utils._parse_user_dt(end, tz)
            end = pd.Timestamp.fromtimestamp(end_ts).tz_localize("UTC").tz_convert(tz)
        if end is None:
            end = dt_now
        if start is None:
            start = end - pd.Timedelta(days=548)  # 18 months
        if start >= end:
            logger.error("Start date must be before end")
            return None
        start = start.floor("D")
        end = end.ceil("D")

        # Fetch
        ts_url_base = f"https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{self.ticker}?symbol={self.ticker}"
        shares_url = f"{ts_url_base}&period1={int(start.timestamp())}&period2={int(end.timestamp())}"
        try:
            json_data = self._data.cache_get(url=shares_url, proxy=proxy)
            json_data = json_data.json()
        except (_json.JSONDecodeError, requests.exceptions.RequestException):
            logger.error(f"{self.ticker}: Yahoo web request for share count failed")
            return None
        try:
            fail = json_data["finance"]["error"]["code"] == "Bad Request"
        except KeyError:
            fail = False
        if fail:
            logger.error(f"{self.ticker}: Yahoo web request for share count failed")
            return None

        shares_data = json_data["timeseries"]["result"]
        if "shares_out" not in shares_data[0]:
            return None
        try:
            df = pd.Series(shares_data[0]["shares_out"], index=pd.to_datetime(shares_data[0]["timestamp"], unit="s"))
        except Exception as e:
            logger.error(f"{self.ticker}: Failed to parse shares count data: {e}")
            return None

        df.index = df.index.tz_localize(tz)
        df = df.sort_index()
        return df

    def get_isin(self, proxy=None) -> Optional[str]:
        # *** experimental ***
        if self._isin is not None:
            return self._isin

        ticker = self.ticker.upper()

        if "-" in ticker or "^" in ticker:
            self._isin = '-'
            return self._isin

        q = ticker

        self._quote.proxy = proxy or self.proxy
        if self._quote.info is None:
            # Don't print error message cause self._quote.info will print one
            return None
        if "shortName" in self._quote.info:
            q = self._quote.info['shortName']

        url = f'https://markets.businessinsider.com/ajax/SearchController_Suggest?max_results=25&query={urlencode(q)}'
        data = self._data.cache_get(url=url, proxy=proxy).text

        search_str = f'"{ticker}|'
        if search_str not in data:
            if q.lower() in data.lower():
                search_str = '"|'
                if search_str not in data:
                    self._isin = '-'
                    return self._isin
            else:
                self._isin = '-'
                return self._isin

        self._isin = data.split(search_str)[1].split('"')[0].split('|')[0]
        return self._isin

    def get_news(self, count=10, tab="news", proxy=None) -> list:
        """Allowed options for tab: "news", "all", "press releases"""
        if self._news:
            return self._news

        logger = utils.get_yf_logger()

        tab_queryrefs = {
            "all": "newsAll",
            "news": "latestNews",
            "press releases": "pressRelease",
        }

        query_ref = tab_queryrefs.get(tab.lower())
        if not query_ref:
            raise ValueError(f"Invalid tab name '{tab}'. Choose from: {', '.join(tab_queryrefs.keys())}")

        url = f"{_ROOT_URL_}/xhr/ncp?queryRef={query_ref}&serviceKey=ncp_fin"
        payload = {
            "serviceConfig": {
                "snippetCount": count,
                "s": [self.ticker]
            }
        }

        data = self._data.post(url, body=payload, proxy=proxy)
        if data is None or "Will be right back" in data.text:
            raise RuntimeError("*** YAHOO! FINANCE IS CURRENTLY DOWN! ***\n"
                               "Our engineers are working quickly to resolve "
                               "the issue. Thank you for your patience.")
        try:
            data = data.json()
        except _json.JSONDecodeError:
            logger.error(f"{self.ticker}: Failed to retrieve the news and received faulty response instead.")
            data = {}

        news = data.get("data", {}).get("tickerStream", {}).get("stream", [])

        self._news = [article for article in news if not article.get('ad', [])]
        return self._news

    @utils.log_indent_decorator
    def get_earnings_dates(self, limit=12, proxy=None) -> Optional[pd.DataFrame]:
        """
        Get earning dates (future and historic)
        
        Args:
            limit (int): max amount of upcoming and recent earnings dates to return.
                Default value 12 should return next 4 quarters and last 8 quarters.
                Increase if more history is needed.
            proxy: requests proxy to use.
        
        Returns:
            pd.DataFrame
        """
        if self._earnings_dates and limit in self._earnings_dates:
            return self._earnings_dates[limit]

        logger = utils.get_yf_logger()

        page_size = min(limit, 100)  # YF caps at 100, don't go higher
        page_offset = 0
        dates = None
        while True:
            url = f"{_ROOT_URL_}/calendar/earnings?day={date.today()}&symbol={self.ticker}&offset={page_offset}&size={page_size}"
            data = self._data.cache_get(url=url, proxy=proxy).text

            if "Will be right back" in data:
                raise RuntimeError("*** YAHOO! FINANCE IS CURRENTLY DOWN! ***\n"
                                   "Our engineers are working quickly to resolve "
                                   "the issue. Thank you for your patience.")

            try:
                data = pd.read_html(StringIO(data))[0]
            except ValueError:
                if page_offset == 0:
                    # Should not fail on first page
                    if "Showing Earnings for:" in data:
                        # Actually YF was successful, problem is company doesn't have earnings history
                        dates = utils.empty_earnings_dates_df()
                break
            if dates is None:
                dates = data
            else:
                dates = pd.concat([dates, data], axis=0)

            page_offset += page_size
            # got less data then we asked for or already fetched all we requested, no need to fetch more pages
            if len(data) < page_size or len(dates) >= limit:
                dates = dates.iloc[:limit]
                break
            else:
                # do not fetch more than needed next time
                page_size = min(limit - len(dates), page_size)

        if dates is None or dates.shape[0] == 0:
            _exception = YFEarningsDateMissing(self.ticker)
            err_msg = str(_exception)
            logger.error(f'{self.ticker}: {err_msg}')
            return None
        dates = dates.reset_index(drop=True)

        # Drop redundant columns
        dates = dates.drop(["Symbol", "Company"], axis=1)

        # Compatibility
        dates = dates.rename(columns={'Surprise (%)': 'Surprise(%)'})

        # Drop empty rows
        for i in range(len(dates)-1, -1, -1):
            if dates.iloc[i].isna().all():
                dates = dates.drop(i)

        # Convert types
        for cn in ["EPS Estimate", "Reported EPS", "Surprise(%)"]:
            dates.loc[dates[cn] == '-', cn] = float("nan")
            dates[cn] = dates[cn].astype(float)

        # Parse earnings date string
        cn = "Earnings Date"
        try:
            dates_backup = dates.copy()
            # - extract timezone because Yahoo stopped returning in UTC
            tzy = dates[cn].str.split(' ').str.get(-1)
            tzy[tzy.isin(['EDT', 'EST'])] = 'US/Eastern'
            # - tidy date string
            dates[cn] = dates[cn].str.split(' ').str[:-1].str.join(' ')
            dates[cn] = dates[cn].replace(' at', ',', regex=True)
            # - parse
            dates[cn] = pd.to_datetime(dates[cn], format="%B %d, %Y, %I %p")
            # - convert to exchange timezone
            self._quote.proxy = proxy or self.proxy
            tz = self._get_ticker_tz(proxy=proxy, timeout=30)
            dates[cn] = [dates[cn].iloc[i].tz_localize(tzy.iloc[i], ambiguous=True).tz_convert(tz) for i in range(len(dates))]

            dates = dates.set_index("Earnings Date")
        except Exception as e:
            utils.get_yf_logger().info(f"{self.ticker}: Problem parsing earnings_dates: {str(e)}")
            dates = dates_backup

        self._earnings_dates[limit] = dates

        return dates

    def get_history_metadata(self, proxy=None) -> dict:
        return self._lazy_load_price_history().get_history_metadata(proxy)

    def get_funds_data(self, proxy=None) -> Optional[FundsData]:
        if not self._funds_data:
            self._funds_data = FundsData(self._data, self.ticker)
        
        return self._funds_data
