import pandas as pd

from yfinance.data import YfData
from yfinance.exceptions import YFNotImplementedError


class Analysis:

    def __init__(self, data: YfData, symbol: str, proxy=None):
        self._data = data
        self._symbol = symbol
        self.proxy = proxy

        self._earnings_trend = None
        self._analyst_trend_details = None
        self._analyst_price_target = None
        self._rev_est = None
        self._eps_est = None
        self._already_scraped = False

    @property
    def earnings_trend(self) -> pd.DataFrame:
        if self._earnings_trend is None:
            raise YFNotImplementedError('earnings_trend')
        return self._earnings_trend

    @property
    def analyst_trend_details(self) -> pd.DataFrame:
        if self._analyst_trend_details is None:
            raise YFNotImplementedError('analyst_trend_details')
        return self._analyst_trend_details

    @property
    def analyst_price_target(self) -> pd.DataFrame:
        if self._analyst_price_target is None:
            raise YFNotImplementedError('analyst_price_target')
        return self._analyst_price_target

    @property
    def rev_est(self) -> pd.DataFrame:
        if self._rev_est is None:
            raise YFNotImplementedError('rev_est')
        return self._rev_est

    @property
    def eps_est(self) -> pd.DataFrame:
        if self._eps_est is None:
            raise YFNotImplementedError('eps_est')
        return self._eps_est
