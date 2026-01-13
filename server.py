#!/usr/bin/env python3
"""
CCXT Public API MCP Server - FastMCP with D402 Transport Wrapper

Uses FastMCP from official MCP SDK with D402MCPTransport wrapper for HTTP 402.

Architecture:
- FastMCP for tool decorators and Context objects
- D402MCPTransport wraps the /mcp route for HTTP 402 interception
- Proper HTTP 402 status codes (not JSON-RPC wrapped)

Generated from OpenAPI: https://docs.ccxt.com

Environment Variables:
- SERVER_ADDRESS: Payment address (IATP wallet contract)
- MCP_OPERATOR_PRIVATE_KEY: Operator signing key
- D402_TESTING_MODE: Skip facilitator (default: true)
"""

import os
import logging
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union
from datetime import datetime

import requests
from retry import retry
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ccxt-public-api_mcp')

# FastMCP from official SDK
from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

# D402 payment protocol - using Starlette middleware
from traia_iatp.d402.starlette_middleware import D402PaymentMiddleware
from traia_iatp.d402.mcp_middleware import require_payment_for_tool, get_active_api_key
from traia_iatp.d402.payment_introspection import extract_payment_configs_from_mcp
from traia_iatp.d402.types import TokenAmount, TokenAsset, EIP712Domain

# Configuration
STAGE = os.getenv("STAGE", "MAINNET").upper()
PORT = int(os.getenv("PORT", "8000"))
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS")
if not SERVER_ADDRESS:
    raise ValueError("SERVER_ADDRESS required for payment protocol")

API_KEY = None

logger.info("="*80)
logger.info(f"CCXT Public API MCP Server (FastMCP + D402 Wrapper)")
logger.info(f"API: https://api.ccxt.com")
logger.info(f"Payment: {SERVER_ADDRESS}")
logger.info("="*80)

# Create FastMCP server
mcp = FastMCP("CCXT Public API MCP Server", host="0.0.0.0")

logger.info(f"✅ FastMCP server created")

# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================
# Tool implementations will be added here by endpoint_implementer_crew
# Each tool will use the @mcp.tool() and @require_payment_for_tool() decorators


# D402 Payment Middleware
# The HTTP 402 payment protocol middleware is already configured in the server initialization.
# It's imported from traia_iatp.d402.mcp_middleware and auto-detects configuration from:
# - PAYMENT_ADDRESS or EVM_ADDRESS: Where to receive payments
# - EVM_NETWORK: Blockchain network (default: base-sepolia)
# - DEFAULT_PRICE_USD: Price per request (default: $0.001)
# - CCXT_PUBLIC_API_API_KEY: Server's internal API key for payment mode
#
# All payment verification logic is handled by the traia_iatp.d402 module.
# No custom implementation needed!


# API Endpoint Tool Implementations

@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="List all supported cryptocurrency exchanges. Retur"

)
async def list_exchanges(
    context: Context
) -> Dict[str, Any]:
    """
    List all supported cryptocurrency exchanges. Returns exchange IDs that can be used with other CCXT endpoints.

    Generated from OpenAPI endpoint: GET /exchanges

    Args:
        context: MCP context (auto-injected by framework, not user-provided)


    Returns:
        Dictionary with API response

    Example Usage:
        await list_exchanges()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/exchanges"
        params = {}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in list_exchanges: {e}")
        return {"error": str(e), "endpoint": "/exchanges"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch all trading markets/pairs for a specific exc"

)
async def fetch_markets(
    context: Context,
    exchange: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch all trading markets/pairs for a specific exchange. Returns detailed market information including symbols, base/quote currencies, precision, and trading limits.

    Generated from OpenAPI endpoint: GET /markets

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID (e.g., 'binance', 'coinbase', 'kraken', 'bybit', 'okx') (optional) Examples: "binance", "coinbase", "kraken"

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_markets(exchange="binance")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/markets"
        params = {
            "exchange": exchange
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_markets: {e}")
        return {"error": str(e), "endpoint": "/markets"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch current ticker data for a trading pair inclu"

)
async def fetch_ticker(
    context: Context,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch current ticker data for a trading pair including last price, bid, ask, volume, and price change statistics.

    Generated from OpenAPI endpoint: GET /ticker

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID (e.g., 'binance', 'coinbase', 'kraken') (optional) Examples: "binance", "coinbase", "kraken"
        symbol: Trading pair symbol in CCXT unified format (e.g., 'BTC/USDT', 'ETH/BTC') (optional) Examples: "BTC/USDT", "ETH/USDT", "ETH/BTC"

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_ticker(exchange="binance", symbol="BTC/USDT")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/ticker"
        params = {
            "exchange": exchange,
            "symbol": symbol
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_ticker: {e}")
        return {"error": str(e), "endpoint": "/ticker"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch ticker data for multiple trading pairs at on"

)
async def fetch_tickers(
    context: Context,
    exchange: Optional[str] = None,
    symbols: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch ticker data for multiple trading pairs at once. If symbols not specified, returns all available tickers.

    Generated from OpenAPI endpoint: GET /tickers

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID (e.g., 'binance', 'coinbase', 'kraken') (optional) Examples: "binance", "coinbase", "kraken"
        symbols: Comma-separated list of trading pair symbols (optional). If not provided, returns all tickers. (optional) Examples: "BTC/USDT,ETH/USDT", "BTC/USDT,ETH/USDT,SOL/USDT"

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_tickers(exchange="binance")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/tickers"
        params = {
            "exchange": exchange,
            "symbols": symbols
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_tickers: {e}")
        return {"error": str(e), "endpoint": "/tickers"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch the order book (market depth) for a trading "

)
async def fetch_order_book(
    context: Context,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Fetch the order book (market depth) for a trading pair showing bids and asks with prices and amounts.

    Generated from OpenAPI endpoint: GET /orderbook

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID (e.g., 'binance', 'coinbase', 'kraken') (optional) Examples: "binance", "coinbase", "kraken"
        symbol: Trading pair symbol (e.g., 'BTC/USDT') (optional) Examples: "BTC/USDT", "ETH/USDT", "ETH/BTC"
        limit: Number of order book entries to return (default: 20) (optional, default: 20)

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_order_book(exchange="binance", symbol="BTC/USDT")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/orderbook"
        params = {
            "exchange": exchange,
            "symbol": symbol,
            "limit": limit
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_order_book: {e}")
        return {"error": str(e), "endpoint": "/orderbook"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch OHLCV (candlestick) data for charting and te"

)
async def fetch_ohlcv(
    context: Context,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None,
    timeframe: str = "1h",
    limit: int = 100,
    since: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch OHLCV (candlestick) data for charting and technical analysis. Returns open, high, low, close, volume for each candle.

    Generated from OpenAPI endpoint: GET /ohlcv

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID (e.g., 'binance', 'coinbase', 'kraken') (optional) Examples: "binance", "coinbase", "kraken"
        symbol: Trading pair symbol (e.g., 'BTC/USDT') (optional) Examples: "BTC/USDT", "ETH/USDT", "SOL/USDT"
        timeframe: Candlestick timeframe (optional, default: "1h")
        limit: Number of candles to return (default: 100) (optional, default: 100)
        since: Timestamp in milliseconds for the oldest candle (optional) (optional)

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_ohlcv(exchange="binance", symbol="BTC/USDT")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/ohlcv"
        params = {
            "exchange": exchange,
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": limit,
            "since": since
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_ohlcv: {e}")
        return {"error": str(e), "endpoint": "/ohlcv"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch recent public trades for a trading pair. Ret"

)
async def fetch_trades(
    context: Context,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 50,
    since: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch recent public trades for a trading pair. Returns trade history with price, amount, side, and timestamp.

    Generated from OpenAPI endpoint: GET /trades

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID (e.g., 'binance', 'coinbase', 'kraken') (optional) Examples: "binance", "coinbase", "kraken"
        symbol: Trading pair symbol (e.g., 'BTC/USDT') (optional) Examples: "BTC/USDT", "ETH/USDT"
        limit: Number of trades to return (default: 50) (optional, default: 50)
        since: Timestamp in milliseconds for the oldest trade (optional) (optional)

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_trades(exchange="binance", symbol="BTC/USDT")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/trades"
        params = {
            "exchange": exchange,
            "symbol": symbol,
            "limit": limit,
            "since": since
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_trades: {e}")
        return {"error": str(e), "endpoint": "/trades"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch all currencies supported by an exchange incl"

)
async def fetch_currencies(
    context: Context,
    exchange: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch all currencies supported by an exchange including deposit/withdrawal info, precision, and network details.

    Generated from OpenAPI endpoint: GET /currencies

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID (e.g., 'binance', 'coinbase', 'kraken') (optional) Examples: "binance", "coinbase", "kraken"

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_currencies(exchange="binance")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/currencies"
        params = {
            "exchange": exchange
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_currencies: {e}")
        return {"error": str(e), "endpoint": "/currencies"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch the current operational status of an exchang"

)
async def fetch_status(
    context: Context,
    exchange: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch the current operational status of an exchange including maintenance info and system status.

    Generated from OpenAPI endpoint: GET /exchange_status

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID (e.g., 'binance', 'coinbase', 'kraken') (optional) Examples: "binance", "coinbase", "kraken"

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_status(exchange="binance")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/exchange_status"
        params = {
            "exchange": exchange
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_status: {e}")
        return {"error": str(e), "endpoint": "/exchange_status"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch the current server time of an exchange. Usef"

)
async def fetch_time(
    context: Context,
    exchange: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch the current server time of an exchange. Useful for timestamp synchronization.

    Generated from OpenAPI endpoint: GET /exchange_time

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID (e.g., 'binance', 'coinbase', 'kraken') (optional) Examples: "binance", "coinbase", "kraken"

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_time(exchange="binance")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/exchange_time"
        params = {
            "exchange": exchange
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_time: {e}")
        return {"error": str(e), "endpoint": "/exchange_time"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch the best bid and ask prices for multiple sym"

)
async def fetch_bids_asks(
    context: Context,
    exchange: Optional[str] = None,
    symbols: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch the best bid and ask prices for multiple symbols. More efficient than fetching full order books when only top-of-book is needed.

    Generated from OpenAPI endpoint: GET /bids_asks

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID (e.g., 'binance', 'coinbase', 'kraken') (optional) Examples: "binance", "coinbase", "kraken"
        symbols: Comma-separated list of trading pair symbols (optional). If not provided, returns all. (optional) Examples: "BTC/USDT,ETH/USDT"

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_bids_asks(exchange="binance")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/bids_asks"
        params = {
            "exchange": exchange,
            "symbols": symbols
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_bids_asks: {e}")
        return {"error": str(e), "endpoint": "/bids_asks"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch the current funding rate for a perpetual fut"

)
async def fetch_funding_rate(
    context: Context,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch the current funding rate for a perpetual futures contract. Only available on exchanges with derivatives trading.

    Generated from OpenAPI endpoint: GET /funding_rate

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID supporting perpetual futures (e.g., 'binance', 'bybit', 'okx') (optional) Examples: "binance", "bybit", "okx"
        symbol: Perpetual futures symbol (e.g., 'BTC/USDT:USDT') (optional) Examples: "BTC/USDT:USDT", "ETH/USDT:USDT"

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_funding_rate(exchange="binance", symbol="BTC/USDT:USDT")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/funding_rate"
        params = {
            "exchange": exchange,
            "symbol": symbol
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_funding_rate: {e}")
        return {"error": str(e), "endpoint": "/funding_rate"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch funding rates for multiple perpetual futures"

)
async def fetch_funding_rates(
    context: Context,
    exchange: Optional[str] = None,
    symbols: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch funding rates for multiple perpetual futures contracts at once.

    Generated from OpenAPI endpoint: GET /funding_rates

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID supporting perpetual futures (e.g., 'binance', 'bybit', 'okx') (optional) Examples: "binance", "bybit", "okx"
        symbols: Comma-separated list of perpetual futures symbols (optional) (optional) Examples: "BTC/USDT:USDT,ETH/USDT:USDT"

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_funding_rates(exchange="binance")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/funding_rates"
        params = {
            "exchange": exchange,
            "symbols": symbols
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_funding_rates: {e}")
        return {"error": str(e), "endpoint": "/funding_rates"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="100000000000000",  # 0.0001 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Fetch historical funding rates for a perpetual fut"

)
async def fetch_funding_rate_history(
    context: Context,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 100,
    since: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch historical funding rates for a perpetual futures contract.

    Generated from OpenAPI endpoint: GET /funding_rate_history

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        exchange: Exchange ID supporting perpetual futures (e.g., 'binance', 'bybit', 'okx') (optional) Examples: "binance", "bybit", "okx"
        symbol: Perpetual futures symbol (e.g., 'BTC/USDT:USDT') (optional) Examples: "BTC/USDT:USDT", "ETH/USDT:USDT"
        limit: Number of historical funding rates to return (default: 100) (optional, default: 100)
        since: Timestamp in milliseconds for the oldest funding rate (optional) (optional)

    Returns:
        Dictionary with API response

    Example Usage:
        await fetch_funding_rate_history(exchange="binance", symbol="BTC/USDT:USDT")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://api.ccxt.com/funding_rate_history"
        params = {
            "exchange": exchange,
            "symbol": symbol,
            "limit": limit,
            "since": since
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        # No auth required for this API

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in fetch_funding_rate_history: {e}")
        return {"error": str(e), "endpoint": "/funding_rate_history"}


# TODO: Add your API-specific functions here

# ============================================================================
# APPLICATION SETUP WITH STARLETTE MIDDLEWARE
# ============================================================================

def create_app_with_middleware():
    """
    Create Starlette app with d402 payment middleware.
    
    Strategy:
    1. Get FastMCP's Starlette app via streamable_http_app()
    2. Extract payment configs from @require_payment_for_tool decorators
    3. Add Starlette middleware with extracted configs
    4. Single source of truth - no duplication!
    """
    logger.info("🔧 Creating FastMCP app with middleware...")
    
    # Get FastMCP's Starlette app
    app = mcp.streamable_http_app()
    logger.info(f"✅ Got FastMCP Starlette app")
    
    # Extract payment configs from decorators (single source of truth!)
    tool_payment_configs = extract_payment_configs_from_mcp(mcp, SERVER_ADDRESS)
    logger.info(f"📊 Extracted {len(tool_payment_configs)} payment configs from @require_payment_for_tool decorators")
    
    # D402 Configuration
    facilitator_url = os.getenv("FACILITATOR_URL") or os.getenv("D402_FACILITATOR_URL")
    operator_key = os.getenv("MCP_OPERATOR_PRIVATE_KEY")
    network = os.getenv("NETWORK", "sepolia")
    testing_mode = os.getenv("D402_TESTING_MODE", "false").lower() == "true"
    
    # Log D402 configuration with prominent facilitator info
    logger.info("="*60)
    logger.info("D402 Payment Protocol Configuration:")
    logger.info(f"  Server Address: {SERVER_ADDRESS}")
    logger.info(f"  Network: {network}")
    logger.info(f"  Operator Key: {'✅ Set' if operator_key else '❌ Not set'}")
    logger.info(f"  Testing Mode: {'⚠️  ENABLED (bypasses facilitator)' if testing_mode else '✅ DISABLED (uses facilitator)'}")
    logger.info("="*60)
    
    if not facilitator_url and not testing_mode:
        logger.error("❌ FACILITATOR_URL required when testing_mode is disabled!")
        raise ValueError("Set FACILITATOR_URL or enable D402_TESTING_MODE=true")
    
    if facilitator_url:
        logger.info(f"🌐 FACILITATOR: {facilitator_url}")
        if "localhost" in facilitator_url or "127.0.0.1" in facilitator_url or "host.docker.internal" in facilitator_url:
            logger.info(f"   📍 Using LOCAL facilitator for development")
        else:
            logger.info(f"   🌍 Using REMOTE facilitator for production")
    else:
        logger.warning("⚠️  D402 Testing Mode - Facilitator bypassed")
    logger.info("="*60)
    
    # Add CORS middleware first (processes before other middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods
        allow_headers=["*"],  # Allow all headers
        expose_headers=["mcp-session-id"],  # Expose custom headers to browser
    )
    logger.info("✅ Added CORS middleware (allow all origins, expose mcp-session-id)")
    
    # Add D402 payment middleware with extracted configs
    app.add_middleware(
        D402PaymentMiddleware,
        tool_payment_configs=tool_payment_configs,
        server_address=SERVER_ADDRESS,
        requires_auth=False,  # Only checks payment
        testing_mode=testing_mode,
        facilitator_url=facilitator_url,
        facilitator_api_key=os.getenv("D402_FACILITATOR_API_KEY"),
        server_name="ccxt-public-api-mcp-server"  # MCP server ID for tracking
    )
    logger.info("✅ Added D402PaymentMiddleware")
    logger.info("   - Payment-only mode")
    
    # Add health check endpoint (bypasses middleware)
    @app.route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        """Health check endpoint for container orchestration."""
        return JSONResponse(
            content={
                "status": "healthy",
                "service": "ccxt-public-api-mcp-server",
                "timestamp": datetime.now().isoformat()
            }
        )
    logger.info("✅ Added /health endpoint")
    
    return app

if __name__ == "__main__":
    logger.info("="*80)
    logger.info(f"Starting CCXT Public API MCP Server")
    logger.info("="*80)
    logger.info("Architecture:")
    logger.info("  1. D402PaymentMiddleware intercepts requests")
    logger.info("     - Checks payment → HTTP 402 if missing")
    logger.info("  2. FastMCP processes valid requests with tool decorators")
    logger.info("="*80)
    
    # Create app with middleware
    app = create_app_with_middleware()
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
