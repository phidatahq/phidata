
import datetime as _datetime
import dateutil as _dateutil
import logging
import numpy as np
import pandas as pd
import time as _time

from yfinance import shared, utils
from yfinance.const import _BASE_URL_, _PRICE_COLNAMES_

class PriceHistory:
    def __init__(self, data, ticker, tz, session=None, proxy=None):
        self._data = data
        self.ticker = ticker.upper()
        self.tz = tz
        self.proxy = proxy
        self.session = session

        self._history = None
        self._history_metadata = None
        self._history_metadata_formatted = False

        # Limit recursion depth when repairing prices
        self._reconstruct_start_interval = None
        
    @utils.log_indent_decorator
    def history(self, period="1mo", interval="1d",
                start=None, end=None, prepost=False, actions=True,
                auto_adjust=True, back_adjust=False, repair=False, keepna=False,
                proxy=None, rounding=False, timeout=10,
                raise_errors=False) -> pd.DataFrame:
        """
        :Parameters:
            period : str
                Valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
                Either Use period parameter or use start and end
            interval : str
                Valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
                Intraday data cannot extend last 60 days
            start: str
                Download start date string (YYYY-MM-DD) or _datetime, inclusive.
                Default is 99 years ago
                E.g. for start="2020-01-01", the first data point will be on "2020-01-01"
            end: str
                Download end date string (YYYY-MM-DD) or _datetime, exclusive.
                Default is now
                E.g. for end="2023-01-01", the last data point will be on "2022-12-31"
            prepost : bool
                Include Pre and Post market data in results?
                Default is False
            auto_adjust: bool
                Adjust all OHLC automatically? Default is True
            back_adjust: bool
                Back-adjusted data to mimic true historical prices
            repair: bool
                Detect currency unit 100x mixups and attempt repair.
                Default is False
            keepna: bool
                Keep NaN rows returned by Yahoo?
                Default is False
            proxy: str
                Optional. Proxy server URL scheme. Default is None
            rounding: bool
                Round values to 2 decimal places?
                Optional. Default is False = precision suggested by Yahoo!
            timeout: None or float
                If not None stops waiting for a response after given number of
                seconds. (Can also be a fraction of a second e.g. 0.01)
                Default is 10 seconds.
            raise_errors: bool
                If True, then raise errors as Exceptions instead of logging.
        """
        logger = utils.get_yf_logger()
        proxy = proxy or self.proxy

        start_user = start
        end_user = end
        if start or period is None or period.lower() == "max":
            # Check can get TZ. Fail => probably delisted
            tz = self.tz
            if tz is None:
                # Every valid ticker has a timezone. Missing = problem
                err_msg = "No timezone found, symbol may be delisted"
                shared._DFS[self.ticker] = utils.empty_df()
                shared._ERRORS[self.ticker] = err_msg
                if raise_errors:
                    raise Exception(f'{self.ticker}: {err_msg}')
                else:
                    logger.error(f'{self.ticker}: {err_msg}')
                return utils.empty_df()

            if end is None:
                end = int(_time.time())
            else:
                end = utils._parse_user_dt(end, tz)
            if start is None:
                if interval == "1m":
                    start = end - 604800  # Subtract 7 days
                else:
                    max_start_datetime = pd.Timestamp.utcnow().floor("D") - _datetime.timedelta(days=99 * 365)
                    start = int(max_start_datetime.timestamp())
            else:
                start = utils._parse_user_dt(start, tz)
            params = {"period1": start, "period2": end}
        else:
            period = period.lower()
            params = {"range": period}

        params["interval"] = interval.lower()
        params["includePrePost"] = prepost

        # 1) fix weired bug with Yahoo! - returning 60m for 30m bars
        if params["interval"] == "30m":
            params["interval"] = "15m"

        # if the ticker is MUTUALFUND or ETF, then get capitalGains events
        params["events"] = "div,splits,capitalGains"

        params_pretty = dict(params)
        tz = self.tz
        for k in ["period1", "period2"]:
            if k in params_pretty:
                params_pretty[k] = str(pd.Timestamp(params[k], unit='s').tz_localize("UTC").tz_convert(tz))
        logger.debug(f'{self.ticker}: Yahoo GET parameters: {str(params_pretty)}')

        # Getting data from json
        url = f"{_BASE_URL_}/v8/finance/chart/{self.ticker}"
        data = None
        get_fn = self._data.get
        if end is not None:
            end_dt = pd.Timestamp(end, unit='s').tz_localize("UTC")
            dt_now = pd.Timestamp.utcnow()
            data_delay = _datetime.timedelta(minutes=30)
            if end_dt + data_delay <= dt_now:
                # Date range in past so safe to fetch through cache:
                get_fn = self._data.cache_get
        try:
            data = get_fn(
                url=url,
                params=params,
                proxy=proxy,
                timeout=timeout
            )
            if "Will be right back" in data.text or data is None:
                raise RuntimeError("*** YAHOO! FINANCE IS CURRENTLY DOWN! ***\n"
                                   "Our engineers are working quickly to resolve "
                                   "the issue. Thank you for your patience.")

            data = data.json()
        except Exception:
            if raise_errors:
                raise

        # Store the meta data that gets retrieved simultaneously
        try:
            self._history_metadata = data["chart"]["result"][0]["meta"]
        except Exception:
            self._history_metadata = {}

        intraday = params["interval"][-1] in ("m", 'h')
        err_msg = "No price data found, symbol may be delisted"
        if start or period is None or period.lower() == "max":
            err_msg += f' ({params["interval"]} '
            if start_user is not None:
                err_msg += f'{start_user}'
            elif not intraday:
                err_msg += f'{pd.Timestamp(start, unit="s").tz_localize("UTC").tz_convert(tz).date()}'
            else:
                err_msg += f'{pd.Timestamp(start, unit="s").tz_localize("UTC").tz_convert(tz)}'
            err_msg += ' -> '
            if end_user is not None:
                err_msg += f'{end_user})'
            elif not intraday:
                err_msg += f'{pd.Timestamp(end, unit="s").tz_localize("UTC").tz_convert(tz).date()})'
            else:
                err_msg += f'{pd.Timestamp(end, unit="s").tz_localize("UTC").tz_convert(tz)})'
        else:
            err_msg += f' (period={period})'

        fail = False
        if data is None or not isinstance(data, dict):
            fail = True
        elif isinstance(data, dict) and 'status_code' in data:
            err_msg += f"(Yahoo status_code = {data['status_code']})"
            fail = True
        elif "chart" in data and data["chart"]["error"]:
            err_msg = data["chart"]["error"]["description"]
            fail = True
        elif "chart" not in data or data["chart"]["result"] is None or not data["chart"]["result"]:
            fail = True
        elif period is not None and "timestamp" not in data["chart"]["result"][0] and period not in \
                self._history_metadata["validRanges"]:
            # User provided a bad period. The minimum should be '1d', but sometimes Yahoo accepts '1h'.
            err_msg = f"Period '{period}' is invalid, must be one of {self._history_metadata['validRanges']}"
            fail = True
        if fail:
            shared._DFS[self.ticker] = utils.empty_df()
            shared._ERRORS[self.ticker] = err_msg
            if raise_errors:
                raise Exception(f'{self.ticker}: {err_msg}')
            else:
                logger.error(f'{self.ticker}: {err_msg}')
            if self._reconstruct_start_interval is not None and self._reconstruct_start_interval == interval:
                self._reconstruct_start_interval = None
            return utils.empty_df()

        # parse quotes
        try:
            quotes = utils.parse_quotes(data["chart"]["result"][0])
            # Yahoo bug fix - it often appends latest price even if after end date
            if end and not quotes.empty:
                endDt = pd.to_datetime(_datetime.datetime.utcfromtimestamp(end))
                if quotes.index[quotes.shape[0] - 1] >= endDt:
                    quotes = quotes.iloc[0:quotes.shape[0] - 1]
        except Exception:
            shared._DFS[self.ticker] = utils.empty_df()
            shared._ERRORS[self.ticker] = err_msg
            if raise_errors:
                raise Exception(f'{self.ticker}: {err_msg}')
            else:
                logger.error(f'{self.ticker}: {err_msg}')
            if self._reconstruct_start_interval is not None and self._reconstruct_start_interval == interval:
                self._reconstruct_start_interval = None
            return shared._DFS[self.ticker]
        logger.debug(f'{self.ticker}: yfinance received OHLC data: {quotes.index[0]} -> {quotes.index[-1]}')

        # 2) fix weired bug with Yahoo! - returning 60m for 30m bars
        if interval.lower() == "30m":
            logger.debug(f'{self.ticker}: resampling 30m OHLC from 15m')
            quotes2 = quotes.resample('30T')
            quotes = pd.DataFrame(index=quotes2.last().index, data={
                'Open': quotes2['Open'].first(),
                'High': quotes2['High'].max(),
                'Low': quotes2['Low'].min(),
                'Close': quotes2['Close'].last(),
                'Adj Close': quotes2['Adj Close'].last(),
                'Volume': quotes2['Volume'].sum()
            })
            try:
                quotes['Dividends'] = quotes2['Dividends'].max()
                quotes['Stock Splits'] = quotes2['Stock Splits'].max()
            except Exception:
                pass

        # Select useful info from metadata
        quote_type = self._history_metadata["instrumentType"]
        expect_capital_gains = quote_type in ('MUTUALFUND', 'ETF')
        tz_exchange = self._history_metadata["exchangeTimezoneName"]

        # Note: ordering is important. If you change order, run the tests!
        quotes = utils.set_df_tz(quotes, params["interval"], tz_exchange)
        quotes = utils.fix_Yahoo_dst_issue(quotes, params["interval"])
        quotes = utils.fix_Yahoo_returning_live_separate(quotes, params["interval"], tz_exchange)
        intraday = params["interval"][-1] in ("m", 'h')
        if not prepost and intraday and "tradingPeriods" in self._history_metadata:
            tps = self._history_metadata["tradingPeriods"]
            if not isinstance(tps, pd.DataFrame):
                self._history_metadata = utils.format_history_metadata(self._history_metadata, tradingPeriodsOnly=True)
                tps = self._history_metadata["tradingPeriods"]
            quotes = utils.fix_Yahoo_returning_prepost_unrequested(quotes, params["interval"], tps)
        logger.debug(f'{self.ticker}: OHLC after cleaning: {quotes.index[0]} -> {quotes.index[-1]}')

        # actions
        dividends, splits, capital_gains = utils.parse_actions(data["chart"]["result"][0])
        if not expect_capital_gains:
            capital_gains = None

        if splits is not None:
            splits = utils.set_df_tz(splits, interval, tz_exchange)
        if dividends is not None:
            dividends = utils.set_df_tz(dividends, interval, tz_exchange)
        if capital_gains is not None:
            capital_gains = utils.set_df_tz(capital_gains, interval, tz_exchange)
        if start is not None:
            if not quotes.empty:
                startDt = quotes.index[0].floor('D')
                if dividends is not None:
                    dividends = dividends.loc[startDt:]
                if capital_gains is not None:
                    capital_gains = capital_gains.loc[startDt:]
                if splits is not None:
                    splits = splits.loc[startDt:]
        if end is not None:
            endDt = pd.Timestamp(end, unit='s').tz_localize(tz)
            if dividends is not None:
                dividends = dividends[dividends.index < endDt]
            if capital_gains is not None:
                capital_gains = capital_gains[capital_gains.index < endDt]
            if splits is not None:
                splits = splits[splits.index < endDt]

        # Prepare for combine
        intraday = params["interval"][-1] in ("m", 'h')
        if not intraday:
            # If localizing a midnight during DST transition hour when clocks roll back,
            # meaning clock hits midnight twice, then use the 2nd (ambiguous=True)
            quotes.index = pd.to_datetime(quotes.index.date).tz_localize(tz_exchange, ambiguous=True, nonexistent='shift_forward')
            if dividends.shape[0] > 0:
                dividends.index = pd.to_datetime(dividends.index.date).tz_localize(tz_exchange, ambiguous=True, nonexistent='shift_forward')
            if splits.shape[0] > 0:
                splits.index = pd.to_datetime(splits.index.date).tz_localize(tz_exchange, ambiguous=True, nonexistent='shift_forward')

        # Combine
        df = quotes.sort_index()
        if dividends.shape[0] > 0:
            df = utils.safe_merge_dfs(df, dividends, interval)
        if "Dividends" in df.columns:
            df.loc[df["Dividends"].isna(), "Dividends"] = 0
        else:
            df["Dividends"] = 0.0
        if splits.shape[0] > 0:
            df = utils.safe_merge_dfs(df, splits, interval)
        if "Stock Splits" in df.columns:
            df.loc[df["Stock Splits"].isna(), "Stock Splits"] = 0
        else:
            df["Stock Splits"] = 0.0
        if expect_capital_gains:
            if capital_gains.shape[0] > 0:
                df = utils.safe_merge_dfs(df, capital_gains, interval)
            if "Capital Gains" in df.columns:
                df.loc[df["Capital Gains"].isna(), "Capital Gains"] = 0
            else:
                df["Capital Gains"] = 0.0
        logger.debug(f'{self.ticker}: OHLC after combining events: {quotes.index[0]} -> {quotes.index[-1]}')

        df = df[~df.index.duplicated(keep='first')]  # must do before repair

        if repair:
            # Do this before auto/back adjust
            logger.debug(f'{self.ticker}: checking OHLC for repairs ...')
            df = self._fix_unit_mixups(df, interval, tz_exchange, prepost)
            df = self._fix_bad_stock_split(df, interval, tz_exchange)
            # Must repair 100x and split errors before price reconstruction
            df = self._fix_zeroes(df, interval, tz_exchange, prepost)
            df = self._fix_missing_div_adjust(df, interval, tz_exchange)
            df = df.sort_index()

        # Auto/back adjust
        try:
            if auto_adjust:
                df = utils.auto_adjust(df)
            elif back_adjust:
                df = utils.back_adjust(df)
        except Exception as e:
            if auto_adjust:
                err_msg = "auto_adjust failed with %s" % e
            else:
                err_msg = "back_adjust failed with %s" % e
            shared._DFS[self.ticker] = utils.empty_df()
            shared._ERRORS[self.ticker] = err_msg
            if raise_errors:
                raise Exception('%s: %s' % (self.ticker, err_msg))
            else:
                logger.error('%s: %s' % (self.ticker, err_msg))

        if rounding:
            df = np.round(df, data["chart"]["result"][0]["meta"]["priceHint"])
        df['Volume'] = df['Volume'].fillna(0).astype(np.int64)

        if intraday:
            df.index.name = "Datetime"
        else:
            df.index.name = "Date"

        self._history = df.copy()

        # missing rows cleanup
        if not actions:
            df = df.drop(columns=["Dividends", "Stock Splits", "Capital Gains"], errors='ignore')
        if not keepna:
            data_colnames = _PRICE_COLNAMES_ + ['Volume'] + ['Dividends', 'Stock Splits', 'Capital Gains']
            data_colnames = [c for c in data_colnames if c in df.columns]
            mask_nan_or_zero = (df[data_colnames].isna() | (df[data_colnames] == 0)).all(axis=1)
            df = df.drop(mask_nan_or_zero.index[mask_nan_or_zero])

        logger.debug(f'{self.ticker}: yfinance returning OHLC: {df.index[0]} -> {df.index[-1]}')

        if self._reconstruct_start_interval is not None and self._reconstruct_start_interval == interval:
            self._reconstruct_start_interval = None
        return df

    def get_history_metadata(self, proxy=None) -> dict:
        if self._history_metadata is None:
            # Request intraday data, because then Yahoo returns exchange schedule.
            self.history(period="1wk", interval="1h", prepost=True, proxy=proxy)

        if self._history_metadata_formatted is False:
            self._history_metadata = utils.format_history_metadata(self._history_metadata)
            self._history_metadata_formatted = True

        return self._history_metadata

    def get_dividends(self, proxy=None) -> pd.Series:
        if self._history is None:
            self.history(period="max", proxy=proxy)
        if self._history is not None and "Dividends" in self._history:
            dividends = self._history["Dividends"]
            return dividends[dividends != 0]
        return pd.Series()

    def get_capital_gains(self, proxy=None) -> pd.Series:
        if self._history is None:
            self.history(period="max", proxy=proxy)
        if self._history is not None and "Capital Gains" in self._history:
            capital_gains = self._history["Capital Gains"]
            return capital_gains[capital_gains != 0]
        return pd.Series()

    def get_splits(self, proxy=None) -> pd.Series:
        if self._history is None:
            self.history(period="max", proxy=proxy)
        if self._history is not None and "Stock Splits" in self._history:
            splits = self._history["Stock Splits"]
            return splits[splits != 0]
        return pd.Series()

    def get_actions(self, proxy=None) -> pd.Series:
        if self._history is None:
            self.history(period="max", proxy=proxy)
        if self._history is not None and "Dividends" in self._history and "Stock Splits" in self._history:
            action_columns = ["Dividends", "Stock Splits"]
            if "Capital Gains" in self._history:
                action_columns.append("Capital Gains")
            actions = self._history[action_columns]
            return actions[actions != 0].dropna(how='all').fillna(0)
        return pd.Series()

    @utils.log_indent_decorator
    def _reconstruct_intervals_batch(self, df, interval, prepost, tag=-1):
        # Reconstruct values in df using finer-grained price data. Delimiter marks what to reconstruct
        logger = utils.get_yf_logger()

        if not isinstance(df, pd.DataFrame):
            raise Exception("'df' must be a Pandas DataFrame not", type(df))
        if interval == "1m":
            # Can't go smaller than 1m so can't reconstruct
            return df

        if interval[1:] in ['d', 'wk', 'mo']:
            # Interday data always includes pre & post
            prepost = True
            intraday = False
        else:
            intraday = True

        price_cols = [c for c in _PRICE_COLNAMES_ if c in df]
        data_cols = price_cols + ["Volume"]

        # If interval is weekly then can construct with daily. But if smaller intervals then
        # restricted to recent times:
        intervals = ["1wk", "1d", "1h", "30m", "15m", "5m", "2m", "1m"]
        itds = {i: utils._interval_to_timedelta(interval) for i in intervals}
        nexts = {intervals[i]: intervals[i + 1] for i in range(len(intervals) - 1)}
        min_lookbacks = {"1wk": None, "1d": None, "1h": _datetime.timedelta(days=730)}
        for i in ["30m", "15m", "5m", "2m"]:
            min_lookbacks[i] = _datetime.timedelta(days=60)
        min_lookbacks["1m"] = _datetime.timedelta(days=30)
        if interval in nexts:
            sub_interval = nexts[interval]
            td_range = itds[interval]
        else:
            logger.warning(f"Have not implemented price repair for '{interval}' interval. Contact developers")
            if "Repaired?" not in df.columns:
                df["Repaired?"] = False
            return df

        # Limit max reconstruction depth to 2:
        if self._reconstruct_start_interval is None:
            self._reconstruct_start_interval = interval
        if interval != self._reconstruct_start_interval and interval != nexts[self._reconstruct_start_interval]:
            logger.debug(f"{self.ticker}: Price repair has hit max depth of 2 ('%s'->'%s'->'%s')", self._reconstruct_start_interval, nexts[self._reconstruct_start_interval], interval)
            return df

        df = df.sort_index()

        f_repair = df[data_cols].to_numpy() == tag
        f_repair_rows = f_repair.any(axis=1)

        # Ignore old intervals for which Yahoo won't return finer data:
        m = min_lookbacks[sub_interval]
        if m is None:
            min_dt = None
        else:
            m -= _datetime.timedelta(days=1)  # allow space for 1-day padding
            min_dt = pd.Timestamp.utcnow() - m
            min_dt = min_dt.tz_convert(df.index.tz).ceil("D")
        logger.debug(f"min_dt={min_dt} interval={interval} sub_interval={sub_interval}")
        if min_dt is not None:
            f_recent = df.index >= min_dt
            f_repair_rows = f_repair_rows & f_recent
            if not f_repair_rows.any():
                logger.info("Data too old to repair")
                if "Repaired?" not in df.columns:
                    df["Repaired?"] = False
                return df

        dts_to_repair = df.index[f_repair_rows]

        if len(dts_to_repair) == 0:
            logger.info("Nothing needs repairing (dts_to_repair[] empty)")
            if "Repaired?" not in df.columns:
                df["Repaired?"] = False
            return df

        df_v2 = df.copy()
        if "Repaired?" not in df_v2.columns:
            df_v2["Repaired?"] = False
        f_good = ~(df[price_cols].isna().any(axis=1))
        f_good = f_good & (df[price_cols].to_numpy() != tag).all(axis=1)
        df_good = df[f_good]

        # Group nearby NaN-intervals together to reduce number of Yahoo fetches
        dts_groups = [[dts_to_repair[0]]]
        # Note on setting max size: have to allow space for adding good data
        if sub_interval == "1mo":
            grp_max_size = _dateutil.relativedelta.relativedelta(years=2)
        elif sub_interval == "1wk":
            grp_max_size = _dateutil.relativedelta.relativedelta(years=2)
        elif sub_interval == "1d":
            grp_max_size = _dateutil.relativedelta.relativedelta(years=2)
        elif sub_interval == "1h":
            grp_max_size = _dateutil.relativedelta.relativedelta(years=1)
        elif sub_interval == "1m":
            grp_max_size = _datetime.timedelta(days=5)  # allow 2 days for buffer below
        else:
            grp_max_size = _datetime.timedelta(days=30)
        logger.debug(f"grp_max_size = {grp_max_size}")
        for i in range(1, len(dts_to_repair)):
            dt = dts_to_repair[i]
            if dt.date() < dts_groups[-1][0].date() + grp_max_size:
                dts_groups[-1].append(dt)
            else:
                dts_groups.append([dt])

        logger.debug("Repair groups:")
        for g in dts_groups:
            logger.debug(f"- {g[0]} -> {g[-1]}")

        # Add some good data to each group, so can calibrate prices later:
        for i in range(len(dts_groups)):
            g = dts_groups[i]
            g0 = g[0]
            i0 = df_good.index.get_indexer([g0], method="nearest")[0]
            if i0 > 0:
                if (min_dt is None or df_good.index[i0 - 1] >= min_dt) and \
                        ((not intraday) or df_good.index[i0 - 1].date() == g0.date()):
                    i0 -= 1
            gl = g[-1]
            il = df_good.index.get_indexer([gl], method="nearest")[0]
            if il < len(df_good) - 1:
                if (not intraday) or df_good.index[il + 1].date() == gl.date():
                    il += 1
            good_dts = df_good.index[i0:il + 1]
            dts_groups[i] += good_dts.to_list()
            dts_groups[i].sort()

        n_fixed = 0
        for g in dts_groups:
            df_block = df[df.index.isin(g)]
            logger.debug("df_block:\n" + str(df_block))

            start_dt = g[0]
            start_d = start_dt.date()
            reject = False
            if sub_interval == "1h" and (_datetime.date.today() - start_d) > _datetime.timedelta(days=729):
                reject = True
            elif sub_interval in ["30m", "15m"] and (_datetime.date.today() - start_d) > _datetime.timedelta(days=59):
                reject = True
            if reject:
                # Don't bother requesting more price data, Yahoo will reject
                msg = f"Cannot reconstruct {interval} block starting"
                if intraday:
                    msg += f" {start_dt}"
                else:
                    msg += f" {start_d}"
                msg += ", too old, Yahoo will reject request for finer-grain data"
                logger.info(msg)
                continue

            td_1d = _datetime.timedelta(days=1)
            end_dt = g[-1]
            end_d = end_dt.date() + td_1d
            if interval in "1wk":
                fetch_start = start_d - td_range  # need previous week too
                fetch_end = g[-1].date() + td_range
            elif interval == "1d":
                fetch_start = start_d
                fetch_end = g[-1].date() + td_range
            else:
                fetch_start = g[0]
                fetch_end = g[-1] + td_range

            # The first and last day returned by Yahoo can be slightly wrong, so add buffer:
            fetch_start -= td_1d
            fetch_end += td_1d
            if intraday:
                fetch_start = fetch_start.date()
                fetch_end = fetch_end.date() + td_1d
            if min_dt is not None:
                fetch_start = max(min_dt.date(), fetch_start)
            logger.debug(f"Fetching {sub_interval} prepost={prepost} {fetch_start}->{fetch_end}")
            df_fine = self.history(start=fetch_start, end=fetch_end, interval=sub_interval, auto_adjust=False, actions=True, prepost=prepost, repair=True, keepna=True)
            if df_fine is None or df_fine.empty:
                msg = f"Cannot reconstruct {interval} block starting"
                if intraday:
                    msg += f" {start_dt}"
                else:
                    msg += f" {start_d}"
                msg += ", too old, Yahoo is rejecting request for finer-grain data"
                logger.debug(msg)
                continue
            # Discard the buffer
            df_fine = df_fine.loc[g[0]: g[-1] + itds[sub_interval] - _datetime.timedelta(milliseconds=1)].copy()
            if df_fine.empty:
                msg = f"Cannot reconstruct {interval} block range"
                if intraday:
                    msg += f" {start_dt}->{end_dt}"
                else:
                    msg += f" {start_d}->{end_d}"
                msg += ", Yahoo not returning finer-grain data within range"
                logger.debug(msg)
                continue

            df_fine["ctr"] = 0
            if interval == "1wk":
                weekdays = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
                week_end_day = weekdays[(df_block.index[0].weekday() + 7 - 1) % 7]
                df_fine["Week Start"] = df_fine.index.tz_localize(None).to_period("W-" + week_end_day).start_time
                grp_col = "Week Start"
            elif interval == "1d":
                df_fine["Day Start"] = pd.to_datetime(df_fine.index.date)
                grp_col = "Day Start"
            else:
                df_fine.loc[df_fine.index.isin(df_block.index), "ctr"] = 1
                df_fine["intervalID"] = df_fine["ctr"].cumsum()
                df_fine = df_fine.drop("ctr", axis=1)
                grp_col = "intervalID"
            df_fine = df_fine[~df_fine[price_cols + ['Dividends']].isna().all(axis=1)]

            df_fine_grp = df_fine.groupby(grp_col)
            df_new = df_fine_grp.agg(
                Open=("Open", "first"),
                Close=("Close", "last"),
                AdjClose=("Adj Close", "last"),
                Low=("Low", "min"),
                High=("High", "max"),
                Dividends=("Dividends", "sum"),
                Volume=("Volume", "sum")).rename(columns={"AdjClose": "Adj Close"})
            if grp_col in ["Week Start", "Day Start"]:
                df_new.index = df_new.index.tz_localize(df_fine.index.tz)
            else:
                df_fine["diff"] = df_fine["intervalID"].diff()
                new_index = np.append([df_fine.index[0]], df_fine.index[df_fine["intervalID"].diff() > 0])
                df_new.index = new_index
            logger.debug('df_new:' + '\n' + str(df_new))

            # Calibrate!
            common_index = np.intersect1d(df_block.index, df_new.index)
            if len(common_index) == 0:
                # Can't calibrate so don't attempt repair
                logger.info(f"Can't calibrate {interval} block starting {start_d} so aborting repair")
                continue
            # First, attempt to calibrate the 'Adj Close' column. OK if cannot.
            # Only necessary for 1d interval, because the 1h data is not div-adjusted.
            if interval == '1d':
                df_new_calib = df_new[df_new.index.isin(common_index)]
                df_block_calib = df_block[df_block.index.isin(common_index)]
                f_tag = df_block_calib['Adj Close'] == tag
                if f_tag.any():
                    div_adjusts = df_block_calib['Adj Close'] / df_block_calib['Close']
                    # The loop below assumes each 1d repair is isolated, i.e. surrounded by
                    # good data. Which is case most of time.
                    # But in case are repairing a chunk of bad 1d data, back/forward-fill the
                    # good div-adjustments - not perfect, but a good backup.
                    div_adjusts[f_tag] = np.nan
                    div_adjusts = div_adjusts.ffill().bfill()
                    for idx in np.where(f_tag)[0]:
                        dt = df_new_calib.index[idx]
                        n = len(div_adjusts)
                        if df_new.loc[dt, "Dividends"] != 0:
                            if idx < n - 1:
                                # Easy, take div-adjustment from next-day
                                div_adjusts.iloc[idx] = div_adjusts.iloc[idx + 1]
                            else:
                                # Take previous-day div-adjustment and reverse todays adjustment
                                div_adj = 1.0 - df_new_calib["Dividends"].iloc[idx] / df_new_calib['Close'].iloc[
                                    idx - 1]
                                div_adjusts.iloc[idx] = div_adjusts.iloc[idx - 1] / div_adj
                        else:
                            if idx > 0:
                                # Easy, take div-adjustment from previous-day
                                div_adjusts.iloc[idx] = div_adjusts.iloc[idx - 1]
                            else:
                                # Must take next-day div-adjustment
                                div_adjusts.iloc[idx] = div_adjusts.iloc[idx + 1]
                                if df_new_calib["Dividends"].iloc[idx + 1] != 0:
                                    div_adjusts.iloc[idx] *= 1.0 - df_new_calib["Dividends"].iloc[idx + 1] / \
                                                        df_new_calib['Close'].iloc[idx]
                    f_close_bad = df_block_calib['Close'] == tag
                    div_adjusts = div_adjusts.reindex(df_block.index, fill_value=np.nan).ffill().bfill()
                    df_new['Adj Close'] = df_block['Close'] * div_adjusts
                    if f_close_bad.any():
                        f_close_bad_new = f_close_bad.reindex(df_new.index, fill_value=False)
                        div_adjusts_new = div_adjusts.reindex(df_new.index, fill_value=np.nan).ffill().bfill()
                        div_adjusts_new_np = f_close_bad_new.to_numpy()
                        df_new.loc[div_adjusts_new_np, 'Adj Close'] = df_new['Close'][div_adjusts_new_np] * div_adjusts_new[div_adjusts_new_np]

            # Check whether 'df_fine' has different split-adjustment.
            # If different, then adjust to match 'df'
            calib_cols = ['Open', 'Close']
            df_new_calib = df_new[df_new.index.isin(common_index)][calib_cols].to_numpy()
            df_block_calib = df_block[df_block.index.isin(common_index)][calib_cols].to_numpy()
            calib_filter = (df_block_calib != tag)
            if not calib_filter.any():
                # Can't calibrate so don't attempt repair
                logger.info(f"Can't calibrate {interval} block starting {start_d} so aborting repair")
                continue
            # Avoid divide-by-zero warnings:
            for j in range(len(calib_cols)):
                f = ~calib_filter[:, j]
                if f.any():
                    df_block_calib[f, j] = 1
                    df_new_calib[f, j] = 1
            ratios = df_block_calib[calib_filter] / df_new_calib[calib_filter]
            weights = df_fine_grp.size()
            weights.index = df_new.index
            weights = weights[weights.index.isin(common_index)].to_numpy().astype(float)
            weights = weights[:, None]  # transpose
            weights = np.tile(weights, len(calib_cols))  # 1D -> 2D
            weights = weights[calib_filter]  # flatten
            not1 = ~np.isclose(ratios, 1.0, rtol=0.00001)
            if np.sum(not1) == len(calib_cols):
                # Only 1 calibration row in df_new is different to df_block so ignore
                ratio = 1.0
            else:
                ratio = np.average(ratios, weights=weights)
            logger.debug(f"Price calibration ratio (raw) = {ratio:6f}")
            ratio_rcp = round(1.0 / ratio, 1)
            ratio = round(ratio, 1)
            if ratio == 1 and ratio_rcp == 1:
                # Good!
                pass
            else:
                if ratio > 1:
                    # data has different split-adjustment than fine-grained data
                    # Adjust fine-grained to match
                    df_new[price_cols] *= ratio
                    df_new["Volume"] /= ratio
                elif ratio_rcp > 1:
                    # data has different split-adjustment than fine-grained data
                    # Adjust fine-grained to match
                    df_new[price_cols] *= 1.0 / ratio_rcp
                    df_new["Volume"] *= ratio_rcp

            # Repair!
            bad_dts = df_block.index[(df_block[price_cols + ["Volume"]] == tag).to_numpy().any(axis=1)]

            no_fine_data_dts = []
            for idx in bad_dts:
                if idx not in df_new.index:
                    # Yahoo didn't return finer-grain data for this interval,
                    # so probably no trading happened.
                    no_fine_data_dts.append(idx)
            if len(no_fine_data_dts) > 0:
                logger.debug("Yahoo didn't return finer-grain data for these intervals: " + str(no_fine_data_dts))
            for idx in bad_dts:
                if idx not in df_new.index:
                    # Yahoo didn't return finer-grain data for this interval,
                    # so probably no trading happened.
                    continue
                df_new_row = df_new.loc[idx]

                if interval == "1wk":
                    df_last_week = df_new.iloc[df_new.index.get_loc(idx) - 1]
                    df_fine = df_fine.loc[idx:]

                df_bad_row = df.loc[idx]
                bad_fields = df_bad_row.index[df_bad_row == tag].to_numpy()
                if "High" in bad_fields:
                    df_v2.loc[idx, "High"] = df_new_row["High"]
                if "Low" in bad_fields:
                    df_v2.loc[idx, "Low"] = df_new_row["Low"]
                if "Open" in bad_fields:
                    if interval == "1wk" and idx != df_fine.index[0]:
                        # Exchange closed Monday. In this case, Yahoo sets Open to last week close
                        df_v2.loc[idx, "Open"] = df_last_week["Close"]
                        df_v2.loc[idx, "Low"] = min(df_v2.loc[idx, "Open"], df_v2.loc[idx, "Low"])
                    else:
                        df_v2.loc[idx, "Open"] = df_new_row["Open"]
                if "Close" in bad_fields:
                    df_v2.loc[idx, "Close"] = df_new_row["Close"]
                    # Assume 'Adj Close' also corrupted, easier than detecting whether true
                    df_v2.loc[idx, "Adj Close"] = df_new_row["Adj Close"]
                elif "Adj Close" in bad_fields:
                    df_v2.loc[idx, "Adj Close"] = df_new_row["Adj Close"]
                if "Volume" in bad_fields:
                    df_v2.loc[idx, "Volume"] = df_new_row["Volume"]
                df_v2.loc[idx, "Repaired?"] = True
                n_fixed += 1

        return df_v2

    @utils.log_indent_decorator
    def _fix_unit_mixups(self, df, interval, tz_exchange, prepost):
        if df.empty:
            return df
        df2 = self._fix_unit_switch(df, interval, tz_exchange)
        df3 = self._fix_unit_random_mixups(df2, interval, tz_exchange, prepost)
        return df3

    @utils.log_indent_decorator
    def _fix_unit_random_mixups(self, df, interval, tz_exchange, prepost):
        # Sometimes Yahoo returns few prices in cents/pence instead of $/£
        # I.e. 100x bigger
        # 2 ways this manifests:
        # - random 100x errors spread throughout table
        # - a sudden switch between $<->cents at some date
        # This function fixes the first.

        if df.empty:
            return df

        # Easy to detect and fix, just look for outliers = ~100x local median
        logger = utils.get_yf_logger()

        if df.shape[0] == 0:
            if "Repaired?" not in df.columns:
                df["Repaired?"] = False
            return df
        if df.shape[0] == 1:
            # Need multiple rows to confidently identify outliers
            logger.info("price-repair-100x: Cannot check single-row table for 100x price errors")
            if "Repaired?" not in df.columns:
                df["Repaired?"] = False
            return df

        df2 = df.copy()

        if df2.index.tz is None:
            df2.index = df2.index.tz_localize(tz_exchange)
        elif df2.index.tz != tz_exchange:
            df2.index = df2.index.tz_convert(tz_exchange)

        # Only import scipy if users actually want function. To avoid
        # adding it to dependencies.
        from scipy import ndimage as _ndimage

        data_cols = ["High", "Open", "Low", "Close", "Adj Close"]  # Order important, separate High from Low
        data_cols = [c for c in data_cols if c in df2.columns]
        f_zeroes = (df2[data_cols] == 0).any(axis=1).to_numpy()
        if f_zeroes.any():
            df2_zeroes = df2[f_zeroes]
            df2 = df2[~f_zeroes]
            df = df[~f_zeroes]  # all row slicing must be applied to both df and df2
        else:
            df2_zeroes = None
        if df2.shape[0] <= 1:
            logger.info("price-repair-100x: Insufficient good data for detecting 100x price errors")
            if "Repaired?" not in df.columns:
                df["Repaired?"] = False
            return df
        df2_data = df2[data_cols].to_numpy()
        median = _ndimage.median_filter(df2_data, size=(3, 3), mode="wrap")
        ratio = df2_data / median
        ratio_rounded = (ratio / 20).round() * 20  # round ratio to nearest 20
        f = ratio_rounded == 100
        ratio_rcp = 1.0/ratio
        ratio_rcp_rounded = (ratio_rcp / 20).round() * 20  # round ratio to nearest 20
        f_rcp = (ratio_rounded == 100) | (ratio_rcp_rounded == 100)
        f_either = f | f_rcp
        if not f_either.any():
            logger.info("price-repair-100x: No sporadic 100x errors")
            if "Repaired?" not in df.columns:
                df["Repaired?"] = False
            return df

        # Mark values to send for repair
        tag = -1.0
        for i in range(len(data_cols)):
            fi = f_either[:, i]
            c = data_cols[i]
            df2.loc[fi, c] = tag

        n_before = (df2_data == tag).sum()
        df2 = self._reconstruct_intervals_batch(df2, interval, prepost, tag)
        df2_tagged = df2[data_cols].to_numpy() == tag
        n_after = (df2[data_cols].to_numpy() == tag).sum()

        if n_after > 0:
            # This second pass will *crudely* "fix" any remaining errors in High/Low
            # simply by ensuring they don't contradict e.g. Low = 100x High.
            f = (df2[data_cols].to_numpy() == tag) & f
            for i in range(f.shape[0]):
                fi = f[i, :]
                if not fi.any():
                    continue
                idx = df2.index[i]

                for c in ['Open', 'Close']:
                    j = data_cols.index(c)
                    if fi[j]:
                        df2.loc[idx, c] = df.loc[idx, c] * 0.01

                c = "High"
                j = data_cols.index(c)
                if fi[j]:
                    df2.loc[idx, c] = df2.loc[idx, ["Open", "Close"]].max()

                c = "Low"
                j = data_cols.index(c)
                if fi[j]:
                    df2.loc[idx, c] = df2.loc[idx, ["Open", "Close"]].min()

            f_rcp = (df2[data_cols].to_numpy() == tag) & f_rcp
            for i in range(f_rcp.shape[0]):
                fi = f_rcp[i, :]
                if not fi.any():
                    continue
                idx = df2.index[i]

                for c in ['Open', 'Close']:
                    j = data_cols.index(c)
                    if fi[j]:
                        df2.loc[idx, c] = df.loc[idx, c] * 100.0

                c = "High"
                j = data_cols.index(c)
                if fi[j]:
                    df2.loc[idx, c] = df2.loc[idx, ["Open", "Close"]].max()

                c = "Low"
                j = data_cols.index(c)
                if fi[j]:
                    df2.loc[idx, c] = df2.loc[idx, ["Open", "Close"]].min()

            df2_tagged = df2[data_cols].to_numpy() == tag
            n_after_crude = df2_tagged.sum()
        else:
            n_after_crude = n_after

        n_fixed = n_before - n_after_crude
        n_fixed_crudely = n_after - n_after_crude
        if n_fixed > 0:
            report_msg = f"{self.ticker}: fixed {n_fixed}/{n_before} currency unit mixups "
            if n_fixed_crudely > 0:
                report_msg += f"({n_fixed_crudely} crudely) "
            report_msg += f"in {interval} price data"
            logger.info('price-repair-100x: ' + report_msg)

        # Restore original values where repair failed
        f_either = df2[data_cols].to_numpy() == tag
        for j in range(len(data_cols)):
            fj = f_either[:, j]
            if fj.any():
                c = data_cols[j]
                df2.loc[fj, c] = df.loc[fj, c]
        if df2_zeroes is not None:
            if "Repaired?" not in df2_zeroes.columns:
                df2_zeroes["Repaired?"] = False
            df2 = pd.concat([df2, df2_zeroes]).sort_index()
            df2.index = pd.to_datetime(df2.index)

        return df2

    @utils.log_indent_decorator
    def _fix_unit_switch(self, df, interval, tz_exchange):
        # Sometimes Yahoo returns few prices in cents/pence instead of $/£
        # I.e. 100x bigger
        # 2 ways this manifests:
        # - random 100x errors spread throughout table
        # - a sudden switch between $<->cents at some date
        # This function fixes the second.
        # Eventually Yahoo fixes but could take them 2 weeks.

        return self._fix_prices_sudden_change(df, interval, tz_exchange, 100.0)

    @utils.log_indent_decorator
    def _fix_zeroes(self, df, interval, tz_exchange, prepost):
        # Sometimes Yahoo returns prices=0 or NaN when trades occurred.
        # But most times when prices=0 or NaN returned is because no trades.
        # Impossible to distinguish, so only attempt repair if few or rare.

        if df.empty:
            return df

        logger = utils.get_yf_logger()

        if df.shape[0] == 0:
            if "Repaired?" not in df.columns:
                df["Repaired?"] = False
            return df

        intraday = interval[-1] in ("m", 'h')

        df = df.sort_index()  # important!
        df2 = df.copy()

        if df2.index.tz is None:
            df2.index = df2.index.tz_localize(tz_exchange)
        elif df2.index.tz != tz_exchange:
            df2.index = df2.index.tz_convert(tz_exchange)

        price_cols = [c for c in _PRICE_COLNAMES_ if c in df2.columns]
        f_prices_bad = (df2[price_cols] == 0.0) | df2[price_cols].isna()
        df2_reserve = None
        if intraday:
            # Ignore days with >50% intervals containing NaNs
            grp = pd.Series(f_prices_bad.any(axis=1), name="nan").groupby(f_prices_bad.index.date)
            nan_pct = grp.sum() / grp.count()
            dts = nan_pct.index[nan_pct > 0.5]
            f_zero_or_nan_ignore = np.isin(f_prices_bad.index.date, dts)
            df2_reserve = df2[f_zero_or_nan_ignore]
            df2 = df2[~f_zero_or_nan_ignore]
            f_prices_bad = (df2[price_cols] == 0.0) | df2[price_cols].isna()

        f_high_low_good = (~df2["High"].isna().to_numpy()) & (~df2["Low"].isna().to_numpy())
        f_change = df2["High"].to_numpy() != df2["Low"].to_numpy()
        f_vol_bad = (df2["Volume"] == 0).to_numpy() & f_high_low_good & f_change

        # If stock split occurred, then trading must have happened.
        # I should probably rename the function, because prices aren't zero ...
        if 'Stock Splits' in df2.columns:
            f_split = (df2['Stock Splits'] != 0.0).to_numpy()
            if f_split.any():
                f_change_expected_but_missing = f_split & ~f_change
                if f_change_expected_but_missing.any():
                    f_prices_bad[f_change_expected_but_missing] = True

        # Check whether worth attempting repair
        f_prices_bad = f_prices_bad.to_numpy()
        f_bad_rows = f_prices_bad.any(axis=1) | f_vol_bad
        if not f_bad_rows.any():
            logger.info("price-repair-missing: No price=0 errors to repair")
            if "Repaired?" not in df.columns:
                df["Repaired?"] = False
            return df
        if f_prices_bad.sum() == len(price_cols) * len(df2):
            # Need some good data to calibrate
            logger.info("price-repair-missing: No good data for calibration so cannot fix price=0 bad data")
            if "Repaired?" not in df.columns:
                df["Repaired?"] = False
            return df

        data_cols = price_cols + ["Volume"]

        # Mark values to send for repair
        tag = -1.0
        for i in range(len(price_cols)):
            c = price_cols[i]
            df2.loc[f_prices_bad[:, i], c] = tag
        df2.loc[f_vol_bad, "Volume"] = tag
        # If volume=0 or NaN for bad prices, then tag volume for repair
        f_vol_zero_or_nan = (df2["Volume"].to_numpy() == 0) | (df2["Volume"].isna().to_numpy())
        df2.loc[f_prices_bad.any(axis=1) & f_vol_zero_or_nan, "Volume"] = tag
        # If volume=0 or NaN but price moved in interval, then tag volume for repair
        df2.loc[f_change & f_vol_zero_or_nan, "Volume"] = tag

        df2_tagged = df2[data_cols].to_numpy() == tag
        n_before = df2_tagged.sum()
        dts_tagged = df2.index[df2_tagged.any(axis=1)]
        df2 = self._reconstruct_intervals_batch(df2, interval, prepost, tag)
        df2_tagged = df2[data_cols].to_numpy() == tag
        n_after = df2_tagged.sum()
        dts_not_repaired = df2.index[df2_tagged.any(axis=1)]
        n_fixed = n_before - n_after
        if n_fixed > 0:
            msg = f"{self.ticker}: fixed {n_fixed}/{n_before} value=0 errors in {interval} price data"
            if n_fixed < 4:
                dts_repaired = sorted(list(set(dts_tagged).difference(dts_not_repaired)))
                msg += f": {dts_repaired}"
            logger.info('price-repair-missing: ' + msg)

        if df2_reserve is not None:
            if "Repaired?" not in df2_reserve.columns:
                df2_reserve["Repaired?"] = False
            df2 = pd.concat([df2, df2_reserve]).sort_index()

        # Restore original values where repair failed (i.e. remove tag values)
        f = df2[data_cols].to_numpy() == tag
        for j in range(len(data_cols)):
            fj = f[:, j]
            if fj.any():
                c = data_cols[j]
                df2.loc[fj, c] = df.loc[fj, c]

        return df2

    @utils.log_indent_decorator
    def _fix_missing_div_adjust(self, df, interval, tz_exchange):
        # Sometimes, if a dividend occurred today, then Yahoo has not adjusted historic data.
        # Easy to detect and correct BUT ONLY IF the data 'df' includes today's dividend.
        # E.g. if fetching historic prices before todays dividend, then cannot fix.

        if df.empty:
            return df

        logger = utils.get_yf_logger()

        if df is None or df.empty:
            return df
        interday = interval in ['1d', '1wk', '1mo', '3mo']
        if not interday:
            return df

        df = df.sort_index()

        f_div = (df["Dividends"] != 0.0).to_numpy()
        if not f_div.any():
            logger.debug('div-adjust-repair: No dividends to check')
            return df

        df2 = df.copy()
        if df2.index.tz is None:
            df2.index = df2.index.tz_localize(tz_exchange)
        elif df2.index.tz != tz_exchange:
            df2.index = df2.index.tz_convert(tz_exchange)

        div_indices = np.where(f_div)[0]
        last_div_idx = div_indices[-1]
        if last_div_idx == 0:
            # Not enough data to recalculate the div-adjustment,
            # because need close day before
            logger.debug('div-adjust-repair: Insufficient data to recalculate div-adjustment')
            return df

        # To determine if Yahoo messed up, analyse price data between today's dividend and
        # the previous dividend
        if len(div_indices) == 1:
            # No other divs in data
            prev_idx = 0
            prev_dt = None
        else:
            prev_idx = div_indices[-2]
            prev_dt = df2.index[prev_idx]
        f_no_adj = (df2['Close'] == df2['Adj Close']).to_numpy()[prev_idx:last_div_idx]
        threshold_pct = 0.5
        Yahoo_failed = (np.sum(f_no_adj) / len(f_no_adj)) > threshold_pct

        # Fix Yahoo
        if Yahoo_failed:
            last_div_dt = df2.index[last_div_idx]
            last_div_row = df2.loc[last_div_dt]
            close_day_before = df2['Close'].iloc[last_div_idx - 1]
            adj = 1.0 - df2['Dividends'].iloc[last_div_idx] / close_day_before
            div = last_div_row['Dividends']
            msg = f'Correcting missing div-adjustment preceding div = {div} @ {last_div_dt.date()} (prev_dt={prev_dt})'
            logger.debug('div-adjust-repair: ' + msg)

            if interval == '1d':
                # exclusive
                df2.loc[:last_div_dt - _datetime.timedelta(seconds=1), 'Adj Close'] *= adj
            else:
                # inclusive
                df2.loc[:last_div_dt, 'Adj Close'] *= adj

        return df2

    @utils.log_indent_decorator
    def _fix_bad_stock_split(self, df, interval, tz_exchange):
        # Repair idea is to look for BIG daily price changes that closely match the
        # most recent stock split ratio. This indicates Yahoo failed to apply a new
        # stock split to old price data.
        #
        # There is a slight complication, because Yahoo does another stupid thing.
        # Sometimes the old data is adjusted twice. So cannot simply assume
        # which direction to reverse adjustment - have to analyse prices and detect.
        # Not difficult.

        if df.empty:
            return df

        logger = utils.get_yf_logger()

        interday = interval in ['1d', '1wk', '1mo', '3mo']
        if not interday:
            return df

        # Find the most recent stock split
        df = df.sort_index(ascending=False)
        split_f = df['Stock Splits'].to_numpy() != 0
        if not split_f.any():
            logger.debug('price-repair-split: No splits in data')
            return df
        most_recent_split_day = df.index[split_f].max()
        split = df.loc[most_recent_split_day, 'Stock Splits']
        if most_recent_split_day == df.index[0]:
            logger.info(
                "price-repair-split: Need 1+ day of price data after split to determine true price. Won't repair")
            return df

        logger.debug(f'price-repair-split: Most recent split = {split:.4f} @ {most_recent_split_day.date()}')

        return self._fix_prices_sudden_change(df, interval, tz_exchange, split, correct_volume=True)

    @utils.log_indent_decorator
    def _fix_prices_sudden_change(self, df, interval, tz_exchange, change, correct_volume=False):
        if df.empty:
            return df

        logger = utils.get_yf_logger()

        split = change
        split_rcp = 1.0 / split
        interday = interval in ['1d', '1wk', '1mo', '3mo']

        if change in [100.0, 0.01]:
            fix_type = '100x error'
            start_min = None
        else:
            fix_type = 'bad split'
            # start_min = 1 year before oldest split
            f = df['Stock Splits'].to_numpy() != 0.0
            start_min = (df.index[f].min() - _dateutil.relativedelta.relativedelta(years=1)).date()
            logger.debug(f'price-repair-split: start_min={start_min}')

        OHLC = ['Open', 'High', 'Low', 'Close']

        # Do not attempt repair of the split is small,
        # could be mistaken for normal price variance
        if 0.8 < split < 1.25:
            logger.info("price-repair-split: Split ratio too close to 1. Won't repair")
            return df

        df2 = df.copy().sort_index(ascending=False)
        if df2.index.tz is None:
            df2.index = df2.index.tz_localize(tz_exchange)
        elif df2.index.tz != tz_exchange:
            df2.index = df2.index.tz_convert(tz_exchange)
        n = df2.shape[0]

        # If stock is currently suspended and not in USA, then usually Yahoo introduces
        # 100x errors into suspended intervals. Clue is no price change and 0 volume.
        # Better to use last active trading interval as baseline.
        f_no_activity = (df2['Low'] == df2['High']) & (df2['Volume']==0)
        f_no_activity = f_no_activity | df2[OHLC].isna().all(axis=1)
        appears_suspended = f_no_activity.any() and np.where(f_no_activity)[0][0]==0
        f_active = ~f_no_activity
        idx_latest_active = np.where(f_active & np.roll(f_active, 1))[0]
        if len(idx_latest_active) == 0:
            idx_latest_active = None
        else:
            idx_latest_active = int(idx_latest_active[0])
        log_msg = f'price-repair-split: appears_suspended={appears_suspended}, idx_latest_active={idx_latest_active}'
        if idx_latest_active is not None:
            log_msg += f' ({df2.index[idx_latest_active].date()})'
        logger.debug(log_msg)

        if logger.isEnabledFor(logging.DEBUG):
            df_debug = df2.copy()
            df_debug = df_debug.drop(['Adj Close', 'Volume', 'Dividends', 'Repaired?'], axis=1, errors='ignore')
            debug_cols = ['Low', 'High']
            df_debug = df_debug.drop([c for c in OHLC if c not in debug_cols], axis=1, errors='ignore')
        else:
            debug_cols = []

        # Calculate daily price % change. To reduce effect of price volatility,
        # calculate change for each OHLC column.
        if interday and interval != '1d' and split not in [100.0, 100, 0.001]:
            # Avoid using 'Low' and 'High'. For multiday intervals, these can be
            # very volatile so reduce ability to detect genuine stock split errors
            _1d_change_x = np.full((n, 2), 1.0)
            price_data = df2[['Open','Close']].to_numpy()
            f_zero = price_data == 0.0
        else:
            _1d_change_x = np.full((n, 4), 1.0)
            price_data = df2[OHLC].to_numpy()
            f_zero = price_data == 0.0
        if f_zero.any():
            price_data[f_zero] = 1.0

        # Update: if a VERY large dividend is paid out, then can be mistaken for a 1:2 stock split.
        # Fix = use adjusted prices
        adj = df2['Adj Close'].to_numpy() / df2['Close'].to_numpy()
        df_dtype = price_data.dtype
        if df_dtype == np.int64:
            price_data = price_data.astype('float')
        for j in range(price_data.shape[1]):
            price_data[:,j] *= adj
        if df_dtype == np.int64:
            price_data = price_data.astype('int')

        _1d_change_x[1:] = price_data[1:, ] / price_data[:-1, ]
        f_zero_num_denom = f_zero | np.roll(f_zero, 1, axis=0)
        if f_zero_num_denom.any():
            _1d_change_x[f_zero_num_denom] = 1.0
        if interday and interval != '1d':
            # average change
            _1d_change_minx = np.average(_1d_change_x, axis=1)
        else:
            # change nearest to 1.0
            diff = np.abs(_1d_change_x - 1.0)
            j_indices = np.argmin(diff, axis=1)
            _1d_change_minx = _1d_change_x[np.arange(n), j_indices]
        f_na = np.isnan(_1d_change_minx)
        if f_na.any():
            # Possible if data was too old for reconstruction.
            _1d_change_minx[f_na] = 1.0
        if logger.isEnabledFor(logging.DEBUG):
            df_debug['1D change X'] = _1d_change_minx
            df_debug['1D change X'] = df_debug['1D change X'].round(2).astype('str')

        # If all 1D changes are closer to 1.0 than split, exit
        split_max = max(split, split_rcp)
        if np.max(_1d_change_minx) < (split_max - 1) * 0.5 + 1 and np.min(_1d_change_minx) > 1.0 / ((split_max - 1) * 0.5 + 1):
            logger.info(f"price-repair-split: No {fix_type}s detected")
            return df

        # Calculate the true price variance, i.e. remove effect of bad split-adjustments.
        # Key = ignore 1D changes outside of interquartile range
        q1, q3 = np.percentile(_1d_change_minx, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        f = (_1d_change_minx >= lower_bound) & (_1d_change_minx <= upper_bound)
        avg = np.mean(_1d_change_minx[f])
        sd = np.std(_1d_change_minx[f])
        # Now can calculate SD as % of mean
        sd_pct = sd / avg
        logger.debug(f"price-repair-split: Estimation of true 1D change stats: mean = {avg:.2f}, StdDev = {sd:.4f} ({sd_pct*100.0:.1f}% of mean)")

        # Only proceed if split adjustment far exceeds normal 1D changes
        largest_change_pct = 5 * sd_pct
        if interday and interval != '1d':
            largest_change_pct *= 3
            if interval in ['1mo', '3mo']:
                largest_change_pct *= 2
        if max(split, split_rcp) < 1.0 + largest_change_pct:
            logger.info("price-repair-split: Split ratio too close to normal price volatility. Won't repair")
            logger.debug(f"sd_pct = {sd_pct:.4f}  largest_change_pct = {largest_change_pct:.4f}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"sd_pct = {sd_pct:.4f}  largest_change_pct = {largest_change_pct:.4f}")
            return df

        # Now can detect bad split adjustments
        # Set threshold to halfway between split ratio and largest expected normal price change
        r = _1d_change_minx / split_rcp
        split_max = max(split, split_rcp)
        logger.debug(f"price-repair-split: split_max={split_max:.3f} largest_change_pct={largest_change_pct:.4f}")
        threshold = (split_max + 1.0 + largest_change_pct) * 0.5
        logger.debug(f"price-repair-split: threshold={threshold:.3f}")

        if 'Repaired?' not in df2.columns:
            df2['Repaired?'] = False

        if interday and interval != '1d':
            # Yahoo creates multi-day intervals using potentiall corrupt data, e.g.
            # the Close could be 100x Open. This means have to correct each OHLC column
            # individually
            correct_columns_individually = True
        else:
            correct_columns_individually = False

        if correct_columns_individually:
            _1d_change_x = np.full((n, 4), 1.0)
            price_data = df2[OHLC].replace(0.0, 1.0).to_numpy()
            _1d_change_x[1:] = price_data[1:, ] / price_data[:-1, ]
        else:
            _1d_change_x = _1d_change_minx

        r = _1d_change_x / split_rcp
        f_down = _1d_change_x < 1.0 / threshold
        f_up = _1d_change_x > threshold
        f = f_down | f_up
        if logger.isEnabledFor(logging.DEBUG):
            if not correct_columns_individually:
                df_debug['r'] = r
                df_debug['f_down'] = f_down
                df_debug['f_up'] = f_up
                df_debug['r'] = df_debug['r'].round(2).astype('str')
            else:
                for j in range(len(OHLC)):
                    c = OHLC[j]
                    if c in debug_cols:
                        df_debug[c + '_r'] = r[:, j]
                        df_debug[c + '_f_down'] = f_down[:, j]
                        df_debug[c + '_f_up'] = f_up[:, j]
                        df_debug[c + '_r'] = df_debug[c + '_r'].round(2).astype('str')


        if not f.any():
            logger.info(f'price-repair-split: No {fix_type}s detected')
            return df

        # Update: if any 100x changes are soon after a stock split, so could be confused with split error, then abort
        threshold_days = 30
        f_splits = df2['Stock Splits'].to_numpy() != 0.0
        if change in [100.0, 0.01] and f_splits.any():
            indices_A = np.where(f_splits)[0]
            indices_B = np.where(f)[0]
            if not len(indices_A) or not len(indices_B):
                return None
            gaps = indices_B[:, None] - indices_A
            # Because data is sorted in DEscending order, need to flip gaps
            gaps *= -1
            f_pos = gaps > 0
            if f_pos.any():
                gap_min = gaps[f_pos].min()
                gap_td = utils._interval_to_timedelta(interval) * gap_min
                if isinstance(gap_td, _dateutil.relativedelta.relativedelta):
                    threshold = _dateutil.relativedelta.relativedelta(days=threshold_days)
                else:
                    threshold = _datetime.timedelta(days=threshold_days)
                if gap_td < threshold:
                    logger.info('price-repair-split: 100x changes are too soon after stock split events, aborting')
                    return df

        # if logger.isEnabledFor(logging.DEBUG):
        #     df_debug['i'] = list(range(0, df_debug.shape[0]))
        #     df_debug['i_rev'] = df_debug.shape[0]-1 - df_debug['i']
        #     with pd.option_context('display.max_rows', None, 'display.max_columns', 10, 'display.width', 1000):  # more options can be specified also
        #         logger.debug(f"price-repair-split: my workings:" + '\n' + str(df_debug))

        def map_signals_to_ranges(f, f_up, f_down):
            # Ensure 0th element is False, because True is nonsense
            if f[0]:
                f = np.copy(f)
                f[0] = False
                f_up = np.copy(f_up)
                f_up[0] = False
                f_down = np.copy(f_down)
                f_down[0] = False

            if not f.any():
                return []

            true_indices = np.where(f)[0]
            ranges = []

            for i in range(len(true_indices) - 1):
                if i % 2 == 0:
                    if split > 1.0:
                        adj = 'split' if f_down[true_indices[i]] else '1.0/split'
                    else:
                        adj = '1.0/split' if f_down[true_indices[i]] else 'split'
                    ranges.append((true_indices[i], true_indices[i + 1], adj))

            if len(true_indices) % 2 != 0:
                if split > 1.0:
                    adj = 'split' if f_down[true_indices[-1]] else '1.0/split'
                else:
                    adj = '1.0/split' if f_down[true_indices[-1]] else 'split'
                ranges.append((true_indices[-1], len(f), adj))

            return ranges

        if idx_latest_active is not None:
            idx_rev_latest_active = df.shape[0] - 1 - idx_latest_active
            logger.debug(f'price-repair-split: idx_latest_active={idx_latest_active}, idx_rev_latest_active={idx_rev_latest_active}')
        if correct_columns_individually:
            f_corrected = np.full(n, False)
            if correct_volume:
                # If Open or Close is repaired but not both,
                # then this means the interval has a mix of correct
                # and errors. A problem for correcting Volume,
                # so use a heuristic:
                # - if both Open & Close were Nx bad => Volume is Nx bad
                # - if only one of Open & Close are Nx bad => Volume is 0.5*Nx bad
                f_open_fixed = np.full(n, False)
                f_close_fixed = np.full(n, False)

            OHLC_correct_ranges = [None, None, None, None]
            for j in range(len(OHLC)):
                c = OHLC[j]
                idx_first_f = np.where(f)[0][0]
                if appears_suspended and (idx_latest_active is not None and idx_latest_active >= idx_first_f):
                    # Suspended midway during data date range.
                    # 1: process data before suspension in index-ascending (date-descending) order.
                    # 2: process data after suspension in index-descending order. Requires signals to be reversed,
                    #    then returned ranges to also be reversed, because this logic was originally written for
                    #    index-ascending (date-descending) order.
                    fj = f[:, j]
                    f_upj = f_up[:, j]
                    f_downj = f_down[:, j]
                    ranges_before = map_signals_to_ranges(fj[idx_latest_active:], f_upj[idx_latest_active:], f_downj[idx_latest_active:])
                    if len(ranges_before) > 0:
                        # Shift each range back to global indexing
                        for i in range(len(ranges_before)):
                            r = ranges_before[i]
                            ranges_before[i] = (r[0] + idx_latest_active, r[1] + idx_latest_active, r[2])
                    f_rev_downj = np.flip(np.roll(f_upj, -1))  # correct
                    f_rev_upj = np.flip(np.roll(f_downj, -1))  # correct
                    f_revj = f_rev_upj | f_rev_downj
                    ranges_after = map_signals_to_ranges(f_revj[idx_rev_latest_active:], f_rev_upj[idx_rev_latest_active:], f_rev_downj[idx_rev_latest_active:])
                    if len(ranges_after) > 0:
                        # Shift each range back to global indexing:
                        for i in range(len(ranges_after)):
                            r = ranges_after[i]
                            ranges_after[i] = (r[0] + idx_rev_latest_active, r[1] + idx_rev_latest_active, r[2])
                        # Flip range to normal ordering
                        for i in range(len(ranges_after)):
                            r = ranges_after[i]
                            ranges_after[i] = (n-r[1], n-r[0], r[2])
                    ranges = ranges_before
                    ranges.extend(ranges_after)
                else:
                    ranges = map_signals_to_ranges(f[:, j], f_up[:, j], f_down[:, j])
                logger.debug(f"column '{c}' ranges: {ranges}")
                if start_min is not None:
                    # Prune ranges that are older than start_min
                    for i in range(len(ranges)-1, -1, -1):
                        r = ranges[i]
                        if df2.index[r[0]].date() < start_min:
                            logger.debug(f'price-repair-split: Pruning {c} range {df2.index[r[0]]}->{df2.index[r[1]-1]} because too old.')
                            del ranges[i]

                if len(ranges) > 0:
                    OHLC_correct_ranges[j] = ranges

            count = sum([1 if x is not None else 0 for x in OHLC_correct_ranges])
            if count == 0:
                pass
            elif count == 1:
                # If only 1 column then assume false positive
                idxs = [i if OHLC_correct_ranges[i] else -1 for i in range(len(OHLC))]
                idx = np.where(np.array(idxs) != -1)[0][0]
                col = OHLC[idx]
                logger.debug(f'price-repair-split: Potential {fix_type} detected only in column {col}, so treating as false positive (ignore)')
            else:
                # Only correct if at least 2 columns require correction.
                for j in range(len(OHLC)):
                    c = OHLC[j]
                    ranges = OHLC_correct_ranges[j]
                    if ranges is None:
                        ranges = []
                    for r in ranges:
                        if r[2] == 'split':
                            m = split
                            m_rcp = split_rcp
                        else:
                            m = split_rcp
                            m_rcp = split
                        if interday:
                            logger.info(f"price-repair-split: Corrected {fix_type} on col={c} range=[{df2.index[r[1]-1].date()}:{df2.index[r[0]].date()}] m={m:.4f}")
                        else:
                            logger.info(f"price-repair-split: Corrected {fix_type} on col={c} range=[{df2.index[r[1]-1]}:{df2.index[r[0]]}] m={m:.4f}")
                        df2.iloc[r[0]:r[1], df2.columns.get_loc(c)] *= m
                        if c == 'Close':
                            df2.iloc[r[0]:r[1], df2.columns.get_loc('Adj Close')] *= m
                        if correct_volume:
                            if c == 'Open':
                                f_open_fixed[r[0]:r[1]] = True
                            elif c == 'Close':
                                f_close_fixed[r[0]:r[1]] = True
                        f_corrected[r[0]:r[1]] = True

            if correct_volume:
                f_open_and_closed_fixed = f_open_fixed & f_close_fixed
                f_open_xor_closed_fixed = np.logical_xor(f_open_fixed, f_close_fixed)
                if f_open_and_closed_fixed.any():
                    df2.loc[f_open_and_closed_fixed, "Volume"] *= m_rcp
                if f_open_xor_closed_fixed.any():
                    df2.loc[f_open_xor_closed_fixed, "Volume"] *= 0.5 * m_rcp

            df2.loc[f_corrected, 'Repaired?'] = True

        else:
            idx_first_f = np.where(f)[0][0]
            if appears_suspended and (idx_latest_active is not None and idx_latest_active >= idx_first_f):
                # Suspended midway during data date range.
                # 1: process data before suspension in index-ascending (date-descending) order.
                # 2: process data after suspension in index-descending order. Requires signals to be reversed,
                #    then returned ranges to also be reversed, because this logic was originally written for
                #    index-ascending (date-descending) order.
                ranges_before = map_signals_to_ranges(f[idx_latest_active:], f_up[idx_latest_active:], f_down[idx_latest_active:])
                if len(ranges_before) > 0:
                    # Shift each range back to global indexing
                    for i in range(len(ranges_before)):
                        r = ranges_before[i]
                        ranges_before[i] = (r[0] + idx_latest_active, r[1] + idx_latest_active, r[2])
                f_rev_down = np.flip(np.roll(f_up, -1))
                f_rev_up = np.flip(np.roll(f_down, -1))
                f_rev = f_rev_up | f_rev_down
                ranges_after = map_signals_to_ranges(f_rev[idx_rev_latest_active:], f_rev_up[idx_rev_latest_active:], f_rev_down[idx_rev_latest_active:])
                if len(ranges_after) > 0:
                    # Shift each range back to global indexing:
                    for i in range(len(ranges_after)):
                        r = ranges_after[i]
                        ranges_after[i] = (r[0] + idx_rev_latest_active, r[1] + idx_rev_latest_active, r[2])
                    # Flip range to normal ordering
                    for i in range(len(ranges_after)):
                        r = ranges_after[i]
                        ranges_after[i] = (n-r[1], n-r[0], r[2])
                ranges = ranges_before
                ranges.extend(ranges_after)
            else:
                ranges = map_signals_to_ranges(f, f_up, f_down)
            if start_min is not None:
                # Prune ranges that are older than start_min
                for i in range(len(ranges)-1, -1, -1):
                    r = ranges[i]
                    if df2.index[r[0]].date() < start_min:
                        logger.debug(f'price-repair-split: Pruning range {df2.index[r[0]]}->{df2.index[r[1]-1]} because too old.')
                        del ranges[i]
            for r in ranges:
                if r[2] == 'split':
                    m = split
                    m_rcp = split_rcp
                else:
                    m = split_rcp
                    m_rcp = split
                logger.debug(f"price-repair-split: range={r} m={m}")
                for c in ['Open', 'High', 'Low', 'Close', 'Adj Close']:
                    df2.iloc[r[0]:r[1], df2.columns.get_loc(c)] *= m
                if correct_volume:
                    df2.iloc[r[0]:r[1], df2.columns.get_loc("Volume")] *= m_rcp
                df2.iloc[r[0]:r[1], df2.columns.get_loc('Repaired?')] = True
                if r[0] == r[1] - 1:
                    if interday:
                        msg = f"price-repair-split: Corrected {fix_type} on interval {df2.index[r[0]].date()}"
                    else:
                        msg = f"price-repair-split: Corrected {fix_type} on interval {df2.index[r[0]]}"
                else:
                    # Note: df2 sorted with index descending
                    start = df2.index[r[1] - 1]
                    end = df2.index[r[0]]
                    if interday:
                        msg = f"price-repair-split: Corrected {fix_type} across intervals {start.date()} -> {end.date()} (inclusive)"
                    else:
                        msg = f"price-repair-split: Corrected {fix_type} across intervals {start} -> {end} (inclusive)"
                logger.info(msg)

        if correct_volume:
            f_na = df2['Volume'].isna()
            if f_na.any():
                df2.loc[~f_na,'Volume'] = df2['Volume'][~f_na].round(0).astype('int')
            else:
                df2['Volume'] = df2['Volume'].round(0).astype('int')

        return df2.sort_index()
