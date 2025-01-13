import pandas as pd
import requests

from yfinance import utils
from yfinance.data import YfData
from yfinance.const import quote_summary_valid_modules
from yfinance.scrapers.quote import _QUOTE_SUMMARY_URL_
from yfinance.exceptions import YFException


class Analysis:

    def __init__(self, data: YfData, symbol: str, proxy=None):
        self._data = data
        self._symbol = symbol
        self.proxy = proxy

        # In quoteSummary the 'earningsTrend' module contains most of the data below.
        # The format of data is not optimal so each function will process it's part of the data.
        # This variable works as a cache.
        self._earnings_trend = None

        self._analyst_price_targets = None
        self._earnings_estimate = None
        self._revenue_estimate = None
        self._earnings_history = None
        self._eps_trend = None
        self._eps_revisions = None
        self._growth_estimates = None

    @property
    def analyst_price_targets(self) -> dict:
        if self._analyst_price_targets is not None:
            return self._analyst_price_targets

        try:
            data = self._fetch(['financialData'])
            data = data['quoteSummary']['result'][0]['financialData']
        except (TypeError, KeyError):
            self._analyst_price_targets = {}
            return self._analyst_price_targets

        keys = [
            ('currentPrice', 'current'),
            ('targetLowPrice', 'low'),
            ('targetHighPrice', 'high'),
            ('targetMeanPrice', 'mean'),
            ('targetMedianPrice', 'median'),
        ]

        self._analyst_price_targets = {newKey: data.get(oldKey, None) for oldKey, newKey in keys}
        return self._analyst_price_targets

    @property
    def earnings_estimate(self) -> pd.DataFrame:
        if self._earnings_estimate is not None:
            return self._earnings_estimate

        if self._earnings_trend is None:
            self._fetch_earnings_trend()

        data_dict = {
            'numberOfAnalysts': [],
            'avg': [],
            'low': [],
            'high': [],
            'yearAgoEps': [],
            'growth': []
        }
        periods = []

        for item in self._earnings_trend[:4]:
            periods.append(item['period'])
            earnings_estimate = item.get('earningsEstimate', {})

            for key in data_dict.keys():
                data_dict[key].append(earnings_estimate.get(key, {}).get('raw', None))

        self._earnings_estimate = pd.DataFrame(data_dict, index=periods)
        return self._earnings_estimate

    @property
    def revenue_estimate(self) -> pd.DataFrame:
        if self._revenue_estimate is not None:
            return self._revenue_estimate

        if self._earnings_trend is None:
            self._fetch_earnings_trend()

        data_dict = {
            'numberOfAnalysts': [],
            'avg': [],
            'low': [],
            'high': [],
            'yearAgoRevenue': [],
            'growth': []
        }
        periods = []

        for item in self._earnings_trend[:4]:
            periods.append(item['period'])
            revenue_estimate = item.get('revenueEstimate', {})

            for key in data_dict.keys():
                data_dict[key].append(revenue_estimate.get(key, {}).get('raw', None))

        self._revenue_estimate = pd.DataFrame(data_dict, index=periods)
        return self._revenue_estimate

    @property
    def earnings_history(self) -> pd.DataFrame:
        if self._earnings_history is not None:
            return self._earnings_history

        try:
            data = self._fetch(['earningsHistory'])
            data = data['quoteSummary']['result'][0]['earningsHistory']['history']
        except (TypeError, KeyError):
            self._earnings_history = pd.DataFrame()
            return self._earnings_history

        data_dict = {
            'epsEstimate': [],
            'epsActual': [],
            'epsDifference': [],
            'surprisePercent': []
        }
        quarters = []

        for item in data:
            quarters.append(item.get('quarter', {}).get('fmt', None))

            for key in data_dict.keys():
                data_dict[key].append(item.get(key, {}).get('raw', None))
        
        datetime_index = pd.to_datetime(quarters, format='%Y-%m-%d')
        self._earnings_history = pd.DataFrame(data_dict, index=datetime_index)
        return self._earnings_history

    @property
    def eps_trend(self) -> pd.DataFrame:
        if self._eps_trend is not None:
            return self._eps_trend

        if self._earnings_trend is None:
            self._fetch_earnings_trend()

        data_dict = {
            'current': [],
            '7daysAgo': [],
            '30daysAgo': [],
            '60daysAgo': [],
            '90daysAgo': []
        }
        periods = []

        for item in self._earnings_trend[:4]:
            periods.append(item['period'])
            eps_trend = item.get('epsTrend', {})

            for key in data_dict.keys():
                data_dict[key].append(eps_trend.get(key, {}).get('raw', None))

        self._eps_trend = pd.DataFrame(data_dict, index=periods)
        return self._eps_trend

    @property
    def eps_revisions(self) -> pd.DataFrame:
        if self._eps_revisions is not None:
            return self._eps_revisions

        if self._earnings_trend is None:
            self._fetch_earnings_trend()

        data_dict = {
            'upLast7days': [],
            'upLast30days': [],
            'downLast7days': [],
            'downLast30days': []
        }
        periods = []

        for item in self._earnings_trend[:4]:
            periods.append(item['period'])
            eps_revisions = item.get('epsRevisions', {})

            for key in data_dict.keys():
                data_dict[key].append(eps_revisions.get(key, {}).get('raw', None))

        self._eps_revisions = pd.DataFrame(data_dict, index=periods)
        return self._eps_revisions

    @property
    def growth_estimates(self) -> pd.DataFrame:
        if self._growth_estimates is not None:
            return self._growth_estimates

        if self._earnings_trend is None:
            self._fetch_earnings_trend()

        try:
            trends = self._fetch(['industryTrend', 'sectorTrend', 'indexTrend'])
            trends = trends['quoteSummary']['result'][0]
        except (TypeError, KeyError):
            self._growth_estimates = pd.DataFrame()
            return self._growth_estimates

        # LTG is not defined in yahoo finance front-end as at 2024-11-14.
        # But its addition is breaking the retrieval of growth estimates.
        # Also, support for 5 year seem to have dropped.
        # TODO: Revisit this change and consider permanently removing these keys.
        data_dict = {
            '0q': [],
            '+1q': [],
            '0y': [],
            '+1y': [],
            # 'LTG': [],
            # '+5y': [],
            # '-5y': []
        }

        # make sure no column is empty
        dummy_trend = [{'period': key, 'growth': None} for key in data_dict.keys()]
        industry_trend = trends['industryTrend']['estimates'] or dummy_trend
        sector_trend = trends['sectorTrend']['estimates'] or dummy_trend
        index_trend = trends['indexTrend']['estimates'] or dummy_trend

        for item in self._earnings_trend:
            period = item['period']
            if period in data_dict:
                data_dict[period].append(item.get('growth', {}).get('raw', None))

        for item in industry_trend:
            period = item['period']
            if period in data_dict:
                data_dict[period].append(item.get('growth', None))

        for item in sector_trend:
            period = item['period']
            if period in data_dict:
                data_dict[period].append(item.get('growth', None))

        for item in index_trend:
            period = item['period']
            if period in data_dict:
                data_dict[period].append(item.get('growth', None))

        cols = ['stock', 'industry', 'sector', 'index']
        self._growth_estimates = pd.DataFrame(data_dict, index=cols).T
        return self._growth_estimates

    # modified version from quote.py
    def _fetch(self, modules: list):
        if not isinstance(modules, list):
            raise YFException("Should provide a list of modules, see available modules using `valid_modules`")

        modules = ','.join([m for m in modules if m in quote_summary_valid_modules])
        if len(modules) == 0:
            raise YFException("No valid modules provided, see available modules using `valid_modules`")
        params_dict = {"modules": modules, "corsDomain": "finance.yahoo.com", "formatted": "false", "symbol": self._symbol}
        try:
            result = self._data.get_raw_json(_QUOTE_SUMMARY_URL_ + f"/{self._symbol}", user_agent_headers=self._data.user_agent_headers, params=params_dict, proxy=self.proxy)
        except requests.exceptions.HTTPError as e:
            utils.get_yf_logger().error(str(e))
            return None
        return result

    def _fetch_earnings_trend(self) -> None:
        try:
            data = self._fetch(['earningsTrend'])
            self._earnings_trend = data['quoteSummary']['result'][0]['earningsTrend']['trend']
        except (TypeError, KeyError):
            self._earnings_trend = []
