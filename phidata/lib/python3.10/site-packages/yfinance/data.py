import functools
from functools import lru_cache

import requests as requests
from bs4 import BeautifulSoup
import datetime

from frozendict import frozendict

from . import utils, cache
import threading

cache_maxsize = 64


def lru_cache_freezeargs(func):
    """
    Decorator transforms mutable dictionary and list arguments into immutable types
    Needed so lru_cache can cache method calls what has dict or list arguments.
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        args = tuple([frozendict(arg) if isinstance(arg, dict) else arg for arg in args])
        kwargs = {k: frozendict(v) if isinstance(v, dict) else v for k, v in kwargs.items()}
        args = tuple([tuple(arg) if isinstance(arg, list) else arg for arg in args])
        kwargs = {k: tuple(v) if isinstance(v, list) else v for k, v in kwargs.items()}
        return func(*args, **kwargs)

    # copy over the lru_cache extra methods to this wrapper to be able to access them
    # after this decorator has been applied
    wrapped.cache_info = func.cache_info
    wrapped.cache_clear = func.cache_clear
    return wrapped


class SingletonMeta(type):
    """
    Metaclass that creates a Singleton instance.
    """
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
            else:
                cls._instances[cls]._set_session(*args, **kwargs)
            return cls._instances[cls]


class YfData(metaclass=SingletonMeta):
    """
    Have one place to retrieve data from Yahoo API in order to ease caching and speed up operations.
    Singleton means one session one cookie shared by all threads.
    """
    user_agent_headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

    def __init__(self, session=None):
        self._session = session or requests.Session()

        try:
            self._session.cache
        except AttributeError:
            # Not caching
            self._session_is_caching = False
        else:
            # Is caching. This is annoying.
            # Can't simply use a non-caching session to fetch cookie & crumb,
            # because then the caching-session won't have cookie.
            self._session_is_caching = True
            from requests_cache import DO_NOT_CACHE
            self._expire_after = DO_NOT_CACHE
        self._crumb = None
        self._cookie = None
        if self._session_is_caching and self._cookie is None:
            utils.print_once("WARNING: cookie & crumb does not work well with requests_cache. Am experimenting with 'expire_after=DO_NOT_CACHE', but you need to help stress-test.")

        # Default to using 'basic' strategy
        self._cookie_strategy = 'basic'
        # If it fails, then fallback method is 'csrf'
        # self._cookie_strategy = 'csrf'

        self._cookie_lock = threading.Lock()

    def _set_session(self, session):
        if session is None:
            return
        with self._cookie_lock:
            self._session = session

    def _set_cookie_strategy(self, strategy, have_lock=False):
        if strategy == self._cookie_strategy:
            return
        if not have_lock:
            self._cookie_lock.acquire()

        try:
            if self._cookie_strategy == 'csrf':
                utils.get_yf_logger().debug(f'toggling cookie strategy {self._cookie_strategy} -> basic')
                self._session.cookies.clear()
                self._cookie_strategy = 'basic'
            else:
                utils.get_yf_logger().debug(f'toggling cookie strategy {self._cookie_strategy} -> csrf')
                self._cookie_strategy = 'csrf'
            self._cookie = None
            self._crumb = None
        except Exception:
            self._cookie_lock.release()
            raise

        if not have_lock:
            self._cookie_lock.release()

    def _save_session_cookies(self):
        try:
            cache.get_cookie_cache().store('csrf', self._session.cookies)
        except Exception:
            return False
        return True

    def _load_session_cookies(self):
        cookie_dict = cache.get_cookie_cache().lookup('csrf')
        if cookie_dict is None:
            return False
        # Periodically refresh, 24 hours seems fair.
        if cookie_dict['age'] > datetime.timedelta(days=1):
            return False
        self._session.cookies.update(cookie_dict['cookie'])
        utils.get_yf_logger().debug('loaded persistent cookie')

    def _save_cookie_basic(self, cookie):
        try:
            cache.get_cookie_cache().store('basic', cookie)
        except Exception:
            return False
        return True
    def _load_cookie_basic(self):
        cookie_dict = cache.get_cookie_cache().lookup('basic')
        if cookie_dict is None:
            return None
        # Periodically refresh, 24 hours seems fair.
        if cookie_dict['age'] > datetime.timedelta(days=1):
            return None
        utils.get_yf_logger().debug('loaded persistent cookie')
        return cookie_dict['cookie']

    def _get_cookie_basic(self, proxy=None, timeout=30):
        if self._cookie is not None:
            utils.get_yf_logger().debug('reusing cookie')
            return self._cookie

        self._cookie = self._load_cookie_basic()
        if self._cookie is not None:
            return self._cookie

        # To avoid infinite recursion, do NOT use self.get()
        # - 'allow_redirects' copied from @psychoz971 solution - does it help USA?
        response = self._session.get(
            url='https://fc.yahoo.com',
            headers=self.user_agent_headers,
            proxies=proxy,
            timeout=timeout,
            allow_redirects=True)

        if not response.cookies:
            utils.get_yf_logger().debug("response.cookies = None")
            return None
        self._cookie = list(response.cookies)[0]
        if self._cookie == '':
            utils.get_yf_logger().debug("list(response.cookies)[0] = ''")
            return None
        self._save_cookie_basic(self._cookie)
        utils.get_yf_logger().debug(f"fetched basic cookie = {self._cookie}")
        return self._cookie

    def _get_crumb_basic(self, proxy=None, timeout=30):
        if self._crumb is not None:
            utils.get_yf_logger().debug('reusing crumb')
            return self._crumb

        cookie = self._get_cookie_basic()
        if cookie is None:
            return None

        # - 'allow_redirects' copied from @psychoz971 solution - does it help USA?
        get_args = {
            'url': "https://query1.finance.yahoo.com/v1/test/getcrumb",
            'headers': self.user_agent_headers,
            'cookies': {cookie.name: cookie.value},
            'proxies': proxy,
            'timeout': timeout,
            'allow_redirects': True
        }
        if self._session_is_caching:
            get_args['expire_after'] = self._expire_after
            crumb_response = self._session.get(**get_args)
        else:
            crumb_response = self._session.get(**get_args)
        self._crumb = crumb_response.text
        if self._crumb is None or '<html>' in self._crumb:
            utils.get_yf_logger().debug("Didn't receive crumb")
            return None

        utils.get_yf_logger().debug(f"crumb = '{self._crumb}'")
        return self._crumb

    @utils.log_indent_decorator
    def _get_cookie_and_crumb_basic(self, proxy, timeout):
        cookie = self._get_cookie_basic(proxy, timeout)
        crumb = self._get_crumb_basic(proxy, timeout)
        return cookie, crumb

    def _get_cookie_csrf(self, proxy, timeout):
        if self._cookie is not None:
            utils.get_yf_logger().debug('reusing cookie')
            return True

        elif self._load_session_cookies():
            utils.get_yf_logger().debug('reusing persistent cookie')
            self._cookie = True
            return True

        base_args = {
            'headers': self.user_agent_headers,
            'proxies': proxy,
            'timeout': timeout}

        get_args = {**base_args, 'url': 'https://guce.yahoo.com/consent'}
        if self._session_is_caching:
            get_args['expire_after'] = self._expire_after
            response = self._session.get(**get_args)
        else:
            response = self._session.get(**get_args)

        soup = BeautifulSoup(response.content, 'html.parser')
        csrfTokenInput = soup.find('input', attrs={'name': 'csrfToken'})
        if csrfTokenInput is None:
            utils.get_yf_logger().debug('Failed to find "csrfToken" in response')
            return False
        csrfToken = csrfTokenInput['value']
        utils.get_yf_logger().debug(f'csrfToken = {csrfToken}')
        sessionIdInput = soup.find('input', attrs={'name': 'sessionId'})
        sessionId = sessionIdInput['value']
        utils.get_yf_logger().debug(f"sessionId='{sessionId}")

        originalDoneUrl = 'https://finance.yahoo.com/'
        namespace = 'yahoo'
        data = {
            'agree': ['agree', 'agree'],
            'consentUUID': 'default',
            'sessionId': sessionId,
            'csrfToken': csrfToken,
            'originalDoneUrl': originalDoneUrl,
            'namespace': namespace,
        }
        post_args = {**base_args,
            'url': f'https://consent.yahoo.com/v2/collectConsent?sessionId={sessionId}',
            'data': data}
        get_args = {**base_args,
            'url': f'https://guce.yahoo.com/copyConsent?sessionId={sessionId}',
            'data': data}
        if self._session_is_caching:
            post_args['expire_after'] = self._expire_after
            get_args['expire_after'] = self._expire_after
            self._session.post(**post_args)
            self._session.get(**get_args)
        else:
            self._session.post(**post_args)
            self._session.get(**get_args)
        self._cookie = True
        self._save_session_cookies()
        return True

    @utils.log_indent_decorator
    def _get_crumb_csrf(self, proxy=None, timeout=30):
        # Credit goes to @bot-unit #1729

        if self._crumb is not None:
            utils.get_yf_logger().debug('reusing crumb')
            return self._crumb

        if not self._get_cookie_csrf(proxy, timeout):
            # This cookie stored in session
            return None

        get_args = {
            'url': 'https://query2.finance.yahoo.com/v1/test/getcrumb',
            'headers': self.user_agent_headers,
            'proxies': proxy,
            'timeout': timeout}
        if self._session_is_caching:
            get_args['expire_after'] = self._expire_after
            r = self._session.get(**get_args)
        else:
            r = self._session.get(**get_args)
        self._crumb = r.text

        if self._crumb is None or '<html>' in self._crumb or self._crumb == '':
            utils.get_yf_logger().debug("Didn't receive crumb")
            return None

        utils.get_yf_logger().debug(f"crumb = '{self._crumb}'")
        return self._crumb

    @utils.log_indent_decorator
    def _get_cookie_and_crumb(self, proxy=None, timeout=30):
        cookie, crumb, strategy = None, None, None

        utils.get_yf_logger().debug(f"cookie_mode = '{self._cookie_strategy}'")

        with self._cookie_lock:
            if self._cookie_strategy == 'csrf':
                crumb = self._get_crumb_csrf()
                if crumb is None:
                    # Fail
                    self._set_cookie_strategy('basic', have_lock=True)
                    cookie, crumb = self._get_cookie_and_crumb_basic(proxy, timeout)
            else:
                # Fallback strategy
                cookie, crumb = self._get_cookie_and_crumb_basic(proxy, timeout)
                if cookie is None or crumb is None:
                    # Fail
                    self._set_cookie_strategy('csrf', have_lock=True)
                    crumb = self._get_crumb_csrf()
            strategy = self._cookie_strategy
        return cookie, crumb, strategy

    @utils.log_indent_decorator
    def get(self, url, user_agent_headers=None, params=None, proxy=None, timeout=30):
        # Important: treat input arguments as immutable.

        if len(url) > 200:
            utils.get_yf_logger().debug(f'url={url[:200]}...')
        else:
            utils.get_yf_logger().debug(f'url={url}')
        utils.get_yf_logger().debug(f'params={params}')
        proxy = self._get_proxy(proxy)

        if params is None:
            params = {}
        if 'crumb' in params:
            raise Exception("Don't manually add 'crumb' to params dict, let data.py handle it")

        cookie, crumb, strategy = self._get_cookie_and_crumb()
        if crumb is not None:
            crumbs = {'crumb': crumb}
        else:
            crumbs = {}
        if strategy == 'basic' and cookie is not None:
            # Basic cookie strategy adds cookie to GET parameters
            cookies = {cookie.name: cookie.value}
        else:
            cookies = None

        request_args = {
            'url': url,
            'params': {**params, **crumbs},
            'cookies': cookies,
            'proxies': proxy,
            'timeout': timeout,
            'headers': user_agent_headers or self.user_agent_headers
        }
        response = self._session.get(**request_args)
        utils.get_yf_logger().debug(f'response code={response.status_code}')
        if response.status_code >= 400:
            # Retry with other cookie strategy
            if strategy == 'basic':
                self._set_cookie_strategy('csrf')
            else:
                self._set_cookie_strategy('basic')
            cookie, crumb, strategy = self._get_cookie_and_crumb(proxy, timeout)
            request_args['params']['crumb'] = crumb
            if strategy == 'basic':
                request_args['cookies'] = {cookie.name: cookie.value}
            response = self._session.get(**request_args)
            utils.get_yf_logger().debug(f'response code={response.status_code}')

        return response

    @lru_cache_freezeargs
    @lru_cache(maxsize=cache_maxsize)
    def cache_get(self, url, user_agent_headers=None, params=None, proxy=None, timeout=30):
        return self.get(url, user_agent_headers, params, proxy, timeout)

    def _get_proxy(self, proxy):
        # setup proxy in requests format
        if proxy is not None:
            if isinstance(proxy, (dict, frozendict)) and "https" in proxy:
                proxy = proxy["https"]
            proxy = {"https": proxy}
        return proxy

    def get_raw_json(self, url, user_agent_headers=None, params=None, proxy=None, timeout=30):
        utils.get_yf_logger().debug(f'get_raw_json(): {url}')
        response = self.get(url, user_agent_headers=user_agent_headers, params=params, proxy=proxy, timeout=timeout)
        response.raise_for_status()
        return response.json()
