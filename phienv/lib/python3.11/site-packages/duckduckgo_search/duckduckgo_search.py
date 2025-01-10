from __future__ import annotations

import logging
import os
import warnings
from datetime import datetime, timezone
from functools import cached_property
from itertools import cycle
from random import choice, shuffle
from time import sleep, time
from types import TracebackType

import primp
from lxml.etree import _Element
from lxml.html import HTMLParser as LHTMLParser
from lxml.html import document_fromstring

from .exceptions import ConversationLimitException, DuckDuckGoSearchException, RatelimitException, TimeoutException
from .utils import (
    _expand_proxy_tb_alias,
    _extract_vqd,
    _normalize,
    _normalize_url,
    json_loads,
)

logger = logging.getLogger("duckduckgo_search.DDGS")


class DDGS:
    """DuckDuckgo_search class to get search results from duckduckgo.com."""

    _impersonates = (
        "chrome_100", "chrome_101", "chrome_104", "chrome_105", "chrome_106", "chrome_107",
        "chrome_108", "chrome_109", "chrome_114", "chrome_116", "chrome_117", "chrome_118",
        "chrome_119", "chrome_120", "chrome_123", "chrome_124", "chrome_126", "chrome_127",
        "chrome_128", "chrome_129", "chrome_130", "chrome_131",
        "safari_ios_16.5", "safari_ios_17.2", "safari_ios_17.4.1", "safari_ios_18.1.1",
        "safari_15.3", "safari_15.5", "safari_15.6.1", "safari_16", "safari_16.5",
        "safari_17.0", "safari_17.2.1", "safari_17.4.1", "safari_17.5",
        "safari_18", "safari_18.2",
        "safari_ipad_18",
        "edge_101", "edge_122", "edge_127", "edge_131",
        "firefox_109", "firefox_117", "firefox_128", "firefox_133",
    )  # fmt: skip

    def __init__(
        self,
        headers: dict[str, str] | None = None,
        proxy: str | None = None,
        proxies: dict[str, str] | str | None = None,  # deprecated
        timeout: int | None = 10,
        verify: bool = True,
    ) -> None:
        """Initialize the DDGS object.

        Args:
            headers (dict, optional): Dictionary of headers for the HTTP client. Defaults to None.
            proxy (str, optional): proxy for the HTTP client, supports http/https/socks5 protocols.
                example: "http://user:pass@example.com:3128". Defaults to None.
            timeout (int, optional): Timeout value for the HTTP client. Defaults to 10.
            verify (bool): SSL verification when making the request. Defaults to True.
        """
        ddgs_proxy: str | None = os.environ.get("DDGS_PROXY")
        self.proxy: str | None = ddgs_proxy if ddgs_proxy else _expand_proxy_tb_alias(proxy)
        assert self.proxy is None or isinstance(self.proxy, str), "proxy must be a str"
        if not proxy and proxies:
            warnings.warn("'proxies' is deprecated, use 'proxy' instead.", stacklevel=1)
            self.proxy = proxies.get("http") or proxies.get("https") if isinstance(proxies, dict) else proxies
        self.headers = headers if headers else {}
        self.headers["Referer"] = "https://duckduckgo.com/"
        self.client = primp.Client(
            headers=self.headers,
            proxy=self.proxy,
            timeout=timeout,
            cookie_store=True,
            referer=True,
            impersonate=choice(self._impersonates),  # type: ignore
            follow_redirects=False,
            verify=verify,
        )
        self._chat_messages: list[dict[str, str]] = []
        self._chat_tokens_count = 0
        self._chat_vqd: str = ""
        self.sleep_timestamp = 0.0

    def __enter__(self) -> DDGS:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> None:
        pass

    @cached_property
    def parser(self) -> LHTMLParser:
        """Get HTML parser."""
        return LHTMLParser(remove_blank_text=True, remove_comments=True, remove_pis=True, collect_ids=False)

    def _sleep(self, sleeptime: float = 0.75) -> None:
        """Sleep between API requests."""
        delay = 0.0 if not self.sleep_timestamp else 0.0 if time() - self.sleep_timestamp >= 20 else sleeptime
        self.sleep_timestamp = time()
        sleep(delay)

    def _get_url(
        self,
        method: str,
        url: str,
        params: dict[str, str] | None = None,
        content: bytes | None = None,
        data: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> bytes:
        self._sleep()
        try:
            resp = self.client.request(method, url, params=params, content=content, data=data, cookies=cookies)
        except Exception as ex:
            if "time" in str(ex).lower():
                raise TimeoutException(f"{url} {type(ex).__name__}: {ex}") from ex
            raise DuckDuckGoSearchException(f"{url} {type(ex).__name__}: {ex}") from ex
        logger.debug(f"_get_url() {resp.url} {resp.status_code} {len(resp.content)}")
        if resp.status_code == 200:
            return resp.content
        elif resp.status_code in (202, 301, 403):
            raise RatelimitException(f"{resp.url} {resp.status_code} Ratelimit")
        raise DuckDuckGoSearchException(f"{resp.url} return None. {params=} {content=} {data=}")

    def _get_vqd(self, keywords: str) -> str:
        """Get vqd value for a search query."""
        resp_content = self._get_url("GET", "https://duckduckgo.com", params={"q": keywords})
        return _extract_vqd(resp_content, keywords)

    def chat(self, keywords: str, model: str = "gpt-4o-mini", timeout: int = 30) -> str:
        """Initiates a chat session with DuckDuckGo AI.

        Args:
            keywords (str): The initial message or question to send to the AI.
            model (str): The model to use: "gpt-4o-mini", "claude-3-haiku", "llama-3.1-70b", "mixtral-8x7b".
                Defaults to "gpt-4o-mini".
            timeout (int): Timeout value for the HTTP client. Defaults to 20.

        Returns:
            str: The response from the AI.
        """
        models_deprecated = {
            "gpt-3.5": "gpt-4o-mini",
            "llama-3-70b": "llama-3.1-70b",
        }
        if model in models_deprecated:
            logger.info(f"{model=} is deprecated, using {models_deprecated[model]}")
            model = models_deprecated[model]
        models = {
            "claude-3-haiku": "claude-3-haiku-20240307",
            "gpt-4o-mini": "gpt-4o-mini",
            "llama-3.1-70b": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            "mixtral-8x7b": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        }
        # vqd
        if not self._chat_vqd:
            resp = self.client.get("https://duckduckgo.com/duckchat/v1/status", headers={"x-vqd-accept": "1"})
            self._chat_vqd = resp.headers.get("x-vqd-4", "")

        self._chat_messages.append({"role": "user", "content": keywords})
        self._chat_tokens_count += len(keywords) // 4 if len(keywords) >= 4 else 1  # approximate number of tokens

        json_data = {
            "model": models[model],
            "messages": self._chat_messages,
        }
        resp = self.client.post(
            "https://duckduckgo.com/duckchat/v1/chat",
            headers={"x-vqd-4": self._chat_vqd},
            json=json_data,
            timeout=timeout,
        )
        self._chat_vqd = resp.headers.get("x-vqd-4", "")

        data = ",".join(x for line in resp.text.rstrip("[DONE]LIMT_CVRSA\n").split("data:") if (x := line.strip()))
        data = json_loads("[" + data + "]")

        results: list[str] = []
        for x in data:
            if isinstance(x, dict):
                if x.get("action") == "error":
                    err_message = x.get("type", "")
                    if x.get("status") == 429:
                        raise (
                            ConversationLimitException(err_message)
                            if err_message == "ERR_CONVERSATION_LIMIT"
                            else RatelimitException(err_message)
                        )
                    raise DuckDuckGoSearchException(err_message)
                elif message := x.get("message"):
                    results.append(message)
        result = "".join(results)

        self._chat_messages.append({"role": "assistant", "content": result})
        self._chat_tokens_count += len(results)
        return result

    def text(
        self,
        keywords: str,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        timelimit: str | None = None,
        backend: str = "auto",
        max_results: int | None = None,
    ) -> list[dict[str, str]]:
        """DuckDuckGo text search. Query params: https://duckduckgo.com/params.

        Args:
            keywords: keywords for query.
            region: wt-wt, us-en, uk-en, ru-ru, etc. Defaults to "wt-wt".
            safesearch: on, moderate, off. Defaults to "moderate".
            timelimit: d, w, m, y. Defaults to None.
            backend: auto, html, lite. Defaults to auto.
                auto - try all backends in random order,
                html - collect data from https://html.duckduckgo.com,
                lite - collect data from https://lite.duckduckgo.com.
            max_results: max number of results. If None, returns results only from the first response. Defaults to None.

        Returns:
            List of dictionaries with search results, or None if there was an error.

        Raises:
            DuckDuckGoSearchException: Base exception for duckduckgo_search errors.
            RatelimitException: Inherits from DuckDuckGoSearchException, raised for exceeding API request rate limits.
            TimeoutException: Inherits from DuckDuckGoSearchException, raised for API request timeouts.
        """
        if backend in ("api", "ecosia"):
            warnings.warn(f"{backend=} is deprecated, using backend='auto'", stacklevel=2)
            backend = "auto"
        backends = ["html", "lite"] if backend == "auto" else [backend]
        shuffle(backends)

        results, err = [], None
        for b in backends:
            try:
                if b == "html":
                    results = self._text_html(keywords, region, timelimit, max_results)
                elif b == "lite":
                    results = self._text_lite(keywords, region, timelimit, max_results)
                return results
            except Exception as ex:
                logger.info(f"Error to search using {b} backend: {ex}")
                err = ex

        raise DuckDuckGoSearchException(err)

    def _text_html(
        self,
        keywords: str,
        region: str = "wt-wt",
        timelimit: str | None = None,
        max_results: int | None = None,
    ) -> list[dict[str, str]]:
        assert keywords, "keywords is mandatory"

        payload = {
            "q": keywords,
            "s": "0",
            "o": "json",
            "api": "d.js",
            "vqd": "",
            "kl": region,
            "bing_market": region,
        }
        if timelimit:
            payload["df"] = timelimit

        cache = set()
        results: list[dict[str, str]] = []

        for _ in range(5):
            resp_content = self._get_url("POST", "https://html.duckduckgo.com/html", data=payload)
            if b"No  results." in resp_content:
                return results

            tree = document_fromstring(resp_content, self.parser)
            elements = tree.xpath("//div[h2]")
            if not isinstance(elements, list):
                return results

            for e in elements:
                if isinstance(e, _Element):
                    hrefxpath = e.xpath("./a/@href")
                    href = str(hrefxpath[0]) if hrefxpath and isinstance(hrefxpath, list) else None
                    if (
                        href
                        and href not in cache
                        and not href.startswith(
                            ("http://www.google.com/search?q=", "https://duckduckgo.com/y.js?ad_domain")
                        )
                    ):
                        cache.add(href)
                        titlexpath = e.xpath("./h2/a/text()")
                        title = str(titlexpath[0]) if titlexpath and isinstance(titlexpath, list) else ""
                        bodyxpath = e.xpath("./a//text()")
                        body = "".join(str(x) for x in bodyxpath) if bodyxpath and isinstance(bodyxpath, list) else ""
                        results.append(
                            {
                                "title": _normalize(title),
                                "href": _normalize_url(href),
                                "body": _normalize(body),
                            }
                        )
                        if max_results and len(results) >= max_results:
                            return results

            npx = tree.xpath('.//div[@class="nav-link"]')
            if not npx or not max_results:
                return results
            next_page = npx[-1] if isinstance(npx, list) else None
            if isinstance(next_page, _Element):
                names = next_page.xpath('.//input[@type="hidden"]/@name')
                values = next_page.xpath('.//input[@type="hidden"]/@value')
                if isinstance(names, list) and isinstance(values, list):
                    payload = {str(n): str(v) for n, v in zip(names, values)}

        return results

    def _text_lite(
        self,
        keywords: str,
        region: str = "wt-wt",
        timelimit: str | None = None,
        max_results: int | None = None,
    ) -> list[dict[str, str]]:
        assert keywords, "keywords is mandatory"

        payload = {
            "q": keywords,
            "s": "0",
            "o": "json",
            "api": "d.js",
            "vqd": "",
            "kl": region,
            "bing_market": region,
        }
        if timelimit:
            payload["df"] = timelimit

        cache = set()
        results: list[dict[str, str]] = []

        for _ in range(5):
            resp_content = self._get_url("POST", "https://lite.duckduckgo.com/lite/", data=payload)
            if b"No more results." in resp_content:
                return results

            tree = document_fromstring(resp_content, self.parser)
            elements = tree.xpath("//table[last()]//tr")
            if not isinstance(elements, list):
                return results

            data = zip(cycle(range(1, 5)), elements)
            for i, e in data:
                if isinstance(e, _Element):
                    if i == 1:
                        hrefxpath = e.xpath(".//a//@href")
                        href = str(hrefxpath[0]) if hrefxpath and isinstance(hrefxpath, list) else None
                        if (
                            href is None
                            or href in cache
                            or href.startswith(
                                ("http://www.google.com/search?q=", "https://duckduckgo.com/y.js?ad_domain")
                            )
                        ):
                            [next(data, None) for _ in range(3)]  # skip block(i=1,2,3,4)
                        else:
                            cache.add(href)
                            titlexpath = e.xpath(".//a//text()")
                            title = str(titlexpath[0]) if titlexpath and isinstance(titlexpath, list) else ""
                    elif i == 2:
                        bodyxpath = e.xpath(".//td[@class='result-snippet']//text()")
                        body = (
                            "".join(str(x) for x in bodyxpath).strip()
                            if bodyxpath and isinstance(bodyxpath, list)
                            else ""
                        )
                        if href:
                            results.append(
                                {
                                    "title": _normalize(title),
                                    "href": _normalize_url(href),
                                    "body": _normalize(body),
                                }
                            )
                            if max_results and len(results) >= max_results:
                                return results

            next_page_s = tree.xpath("//form[./input[contains(@value, 'ext')]]/input[@name='s']/@value")
            if not next_page_s or not max_results:
                return results
            elif isinstance(next_page_s, list):
                payload["s"] = str(next_page_s[0])

        return results

    def images(
        self,
        keywords: str,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        timelimit: str | None = None,
        size: str | None = None,
        color: str | None = None,
        type_image: str | None = None,
        layout: str | None = None,
        license_image: str | None = None,
        max_results: int | None = None,
    ) -> list[dict[str, str]]:
        """DuckDuckGo images search. Query params: https://duckduckgo.com/params.

        Args:
            keywords: keywords for query.
            region: wt-wt, us-en, uk-en, ru-ru, etc. Defaults to "wt-wt".
            safesearch: on, moderate, off. Defaults to "moderate".
            timelimit: Day, Week, Month, Year. Defaults to None.
            size: Small, Medium, Large, Wallpaper. Defaults to None.
            color: color, Monochrome, Red, Orange, Yellow, Green, Blue,
                Purple, Pink, Brown, Black, Gray, Teal, White. Defaults to None.
            type_image: photo, clipart, gif, transparent, line.
                Defaults to None.
            layout: Square, Tall, Wide. Defaults to None.
            license_image: any (All Creative Commons), Public (PublicDomain),
                Share (Free to Share and Use), ShareCommercially (Free to Share and Use Commercially),
                Modify (Free to Modify, Share, and Use), ModifyCommercially (Free to Modify, Share, and
                Use Commercially). Defaults to None.
            max_results: max number of results. If None, returns results only from the first response. Defaults to None.

        Returns:
            List of dictionaries with images search results.

        Raises:
            DuckDuckGoSearchException: Base exception for duckduckgo_search errors.
            RatelimitException: Inherits from DuckDuckGoSearchException, raised for exceeding API request rate limits.
            TimeoutException: Inherits from DuckDuckGoSearchException, raised for API request timeouts.
        """
        assert keywords, "keywords is mandatory"

        vqd = self._get_vqd(keywords)

        safesearch_base = {"on": "1", "moderate": "1", "off": "-1"}
        timelimit = f"time:{timelimit}" if timelimit else ""
        size = f"size:{size}" if size else ""
        color = f"color:{color}" if color else ""
        type_image = f"type:{type_image}" if type_image else ""
        layout = f"layout:{layout}" if layout else ""
        license_image = f"license:{license_image}" if license_image else ""
        payload = {
            "l": region,
            "o": "json",
            "q": keywords,
            "vqd": vqd,
            "f": f"{timelimit},{size},{color},{type_image},{layout},{license_image}",
            "p": safesearch_base[safesearch.lower()],
        }

        cache = set()
        results: list[dict[str, str]] = []

        for _ in range(5):
            resp_content = self._get_url("GET", "https://duckduckgo.com/i.js", params=payload)
            resp_json = json_loads(resp_content)
            page_data = resp_json.get("results", [])

            for row in page_data:
                image_url = row.get("image")
                if image_url and image_url not in cache:
                    cache.add(image_url)
                    result = {
                        "title": row["title"],
                        "image": _normalize_url(image_url),
                        "thumbnail": _normalize_url(row["thumbnail"]),
                        "url": _normalize_url(row["url"]),
                        "height": row["height"],
                        "width": row["width"],
                        "source": row["source"],
                    }
                    results.append(result)
                    if max_results and len(results) >= max_results:
                        return results
            next = resp_json.get("next")
            if next is None or not max_results:
                return results
            payload["s"] = next.split("s=")[-1].split("&")[0]

        return results

    def videos(
        self,
        keywords: str,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        timelimit: str | None = None,
        resolution: str | None = None,
        duration: str | None = None,
        license_videos: str | None = None,
        max_results: int | None = None,
    ) -> list[dict[str, str]]:
        """DuckDuckGo videos search. Query params: https://duckduckgo.com/params.

        Args:
            keywords: keywords for query.
            region: wt-wt, us-en, uk-en, ru-ru, etc. Defaults to "wt-wt".
            safesearch: on, moderate, off. Defaults to "moderate".
            timelimit: d, w, m. Defaults to None.
            resolution: high, standart. Defaults to None.
            duration: short, medium, long. Defaults to None.
            license_videos: creativeCommon, youtube. Defaults to None.
            max_results: max number of results. If None, returns results only from the first response. Defaults to None.

        Returns:
            List of dictionaries with videos search results.

        Raises:
            DuckDuckGoSearchException: Base exception for duckduckgo_search errors.
            RatelimitException: Inherits from DuckDuckGoSearchException, raised for exceeding API request rate limits.
            TimeoutException: Inherits from DuckDuckGoSearchException, raised for API request timeouts.
        """
        assert keywords, "keywords is mandatory"

        vqd = self._get_vqd(keywords)

        safesearch_base = {"on": "1", "moderate": "-1", "off": "-2"}
        timelimit = f"publishedAfter:{timelimit}" if timelimit else ""
        resolution = f"videoDefinition:{resolution}" if resolution else ""
        duration = f"videoDuration:{duration}" if duration else ""
        license_videos = f"videoLicense:{license_videos}" if license_videos else ""
        payload = {
            "l": region,
            "o": "json",
            "q": keywords,
            "vqd": vqd,
            "f": f"{timelimit},{resolution},{duration},{license_videos}",
            "p": safesearch_base[safesearch.lower()],
        }

        cache = set()
        results: list[dict[str, str]] = []

        for _ in range(8):
            resp_content = self._get_url("GET", "https://duckduckgo.com/v.js", params=payload)
            resp_json = json_loads(resp_content)
            page_data = resp_json.get("results", [])

            for row in page_data:
                if row["content"] not in cache:
                    cache.add(row["content"])
                    results.append(row)
                    if max_results and len(results) >= max_results:
                        return results
            next = resp_json.get("next")
            if next is None or not max_results:
                return results
            payload["s"] = next.split("s=")[-1].split("&")[0]

        return results

    def news(
        self,
        keywords: str,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        timelimit: str | None = None,
        max_results: int | None = None,
    ) -> list[dict[str, str]]:
        """DuckDuckGo news search. Query params: https://duckduckgo.com/params.

        Args:
            keywords: keywords for query.
            region: wt-wt, us-en, uk-en, ru-ru, etc. Defaults to "wt-wt".
            safesearch: on, moderate, off. Defaults to "moderate".
            timelimit: d, w, m. Defaults to None.
            max_results: max number of results. If None, returns results only from the first response. Defaults to None.

        Returns:
            List of dictionaries with news search results.

        Raises:
            DuckDuckGoSearchException: Base exception for duckduckgo_search errors.
            RatelimitException: Inherits from DuckDuckGoSearchException, raised for exceeding API request rate limits.
            TimeoutException: Inherits from DuckDuckGoSearchException, raised for API request timeouts.
        """
        assert keywords, "keywords is mandatory"

        vqd = self._get_vqd(keywords)

        safesearch_base = {"on": "1", "moderate": "-1", "off": "-2"}
        payload = {
            "l": region,
            "o": "json",
            "noamp": "1",
            "q": keywords,
            "vqd": vqd,
            "p": safesearch_base[safesearch.lower()],
        }
        if timelimit:
            payload["df"] = timelimit

        cache = set()
        results: list[dict[str, str]] = []

        for _ in range(5):
            resp_content = self._get_url("GET", "https://duckduckgo.com/news.js", params=payload)
            resp_json = json_loads(resp_content)
            page_data = resp_json.get("results", [])

            for row in page_data:
                if row["url"] not in cache:
                    cache.add(row["url"])
                    image_url = row.get("image", None)
                    result = {
                        "date": datetime.fromtimestamp(row["date"], timezone.utc).isoformat(),
                        "title": row["title"],
                        "body": _normalize(row["excerpt"]),
                        "url": _normalize_url(row["url"]),
                        "image": _normalize_url(image_url),
                        "source": row["source"],
                    }
                    results.append(result)
                    if max_results and len(results) >= max_results:
                        return results

            next = resp_json.get("next")
            if next is None or not max_results:
                return results
            payload["s"] = next.split("s=")[-1].split("&")[0]

        return results
