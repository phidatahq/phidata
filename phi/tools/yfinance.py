import json

from phi.tools import Toolkit

try:
    import yfinance as yf
except ImportError:
    raise ImportError("`yfinance` not installed. Please install using `pip install yfinance`.")


class YFinanceTools(Toolkit):
    def __init__(
        self,
        stock_price: bool = True,
        stock_fundamentals: bool = False,
        income_statements: bool = False,
        key_financial_ratios: bool = False,
        analyst_recommendations: bool = False,
        company_news: bool = False,
        technical_indicators: bool = False,
        company_profile: bool = False,
    ):
        super().__init__(name="yfinance_tools")

        if stock_price:
            self.register(self.get_current_stock_price)
        if stock_fundamentals:
            self.register(self.get_stock_fundamentals)
        if income_statements:
            self.register(self.get_income_statements)
        if key_financial_ratios:
            self.register(self.get_key_financial_ratios)
        if analyst_recommendations:
            self.register(self.get_analyst_recommendations)
        if company_news:
            self.register(self.get_company_news)
        if technical_indicators:
            self.register(self.get_technical_indicators)
        if company_profile:
            self.register(self.get_company_profile)

    def get_current_stock_price(self, symbol: str) -> str:
        """
        Get the current stock price for a given symbol.

        Args:
          symbol (str): The stock symbol.

        Returns:
          str: The current stock price or error message.
        """
        try:
            stock = yf.Ticker(symbol)
            # Use "regularMarketPrice" for regular market hours, or "currentPrice" for pre/post market
            current_price = stock.info.get("regularMarketPrice", stock.info.get("currentPrice"))
            return f"{current_price:.4f}" if current_price else f"Could not fetch current price for {symbol}"
        except Exception as e:
            return f"Error fetching current price for {symbol}: {e}"

    def get_stock_fundamentals(self, symbol: str) -> str:
        """
        Get fundamental data for a given stock symbol yfinance API.

        Args:
            symbol (str): The stock symbol.

        Returns:
            str: A JSON string containing fundamental data or an error message.
                Keys:
                    - 'symbol': The stock symbol.
                    - 'company_name': The long name of the company.
                    - 'sector': The sector to which the company belongs.
                    - 'industry': The industry to which the company belongs.
                    - 'market_cap': The market capitalization of the company.
                    - 'pe_ratio': The forward price-to-earnings ratio.
                    - 'pb_ratio': The price-to-book ratio.
                    - 'dividend_yield': The dividend yield.
                    - 'eps': The trailing earnings per share.
                    - 'beta': The beta value of the stock.
                    - '52_week_high': The 52-week high price of the stock.
                    - '52_week_low': The 52-week low price of the stock.
        """
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            fundamentals = {
                "symbol": symbol,
                "company_name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", "N/A"),
                "pe_ratio": info.get("forwardPE", "N/A"),
                "pb_ratio": info.get("priceToBook", "N/A"),
                "dividend_yield": info.get("dividendYield", "N/A"),
                "eps": info.get("trailingEps", "N/A"),
                "beta": info.get("beta", "N/A"),
                "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
                "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
            }
            return json.dumps(fundamentals, indent=2)
        except Exception as e:
            return f"Error getting fundamentals for {symbol}: {e}"

    def get_income_statements(self, symbol: str) -> str:
        """
        Get income statements for a given stock symbol.

        Args:
        symbol (str): The stock symbol.

        Returns:
        dict: JSON containing income statements or an empty dictionary.
        """
        try:
            stock = yf.Ticker(symbol)
            financials = stock.financials
            return financials.to_json(orient="index")
        except Exception as e:
            return f"Error fetching income statements for {symbol}: {e}"

    def get_key_financial_ratios(self, symbol: str) -> str:
        """
        Get key financial ratios for a given stock symbol.

        Args:
        symbol (str): The stock symbol.

        Returns:
        dict: JSON containing key financial ratios.
        """
        try:
            stock = yf.Ticker(symbol)
            key_ratios = stock.info
            return json.dumps(key_ratios, indent=2)
        except Exception as e:
            return f"Error fetching key financial ratios for {symbol}: {e}"

    def get_analyst_recommendations(self, symbol: str) -> str:
        """
        Get analyst recommendations for a given stock symbol.

        Args:
        symbol (str): The stock symbol.

        Returns:
        str: JSON containing analyst recommendations.
        """
        try:
            stock = yf.Ticker(symbol)
            recommendations = stock.recommendations
            return recommendations.to_json(orient="index")
        except Exception as e:
            return f"Error fetching analyst recommendations for {symbol}: {e}"

    def get_company_news(self, symbol: str, num_stories: int = 3) -> str:
        """
        Get company news and press releases for a given stock symbol.

        Args:
        symbol (str): The stock symbol.
        num_stories (int): The number of news stories to return. Defaults to 3.

        Returns:
        str: JSON containing company news and press releases.
        """
        try:
            news = yf.Ticker(symbol).news
            return json.dumps(news[:num_stories], indent=2)
        except Exception as e:
            return f"Error fetching company news for {symbol}: {e}"

    def get_technical_indicators(self, symbol: str, period: str = "3mo") -> str:
        """
        Get technical indicators for a given stock symbol.

        Args:
        symbol (str): The stock symbol.
        period (str): The time period for which to retrieve technical indicators.
            Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max. Defaults to 3mo.

        Returns:
        str: JSON containing technical indicators.
        """
        try:
            indicators = yf.Ticker(symbol).history(period=period)
            return indicators.to_json(orient="index")
        except Exception as e:
            return f"Error fetching technical indicators for {symbol}: {e}"

    def get_company_profile(self, symbol: str) -> str:
        """
        Get company profile and overview for a given stock symbol.

        Args:
        symbol (str): The stock symbol.

        Returns:
        str: JSON containing company profile and overview.
        """
        try:
            profile = yf.Ticker(symbol).info
            return json.dumps(profile, indent=2)
        except Exception as e:
            return f"Error fetching company profile for {symbol}: {e}"
