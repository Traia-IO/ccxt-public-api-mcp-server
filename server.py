#!/usr/bin/env python3
"""
CCXT Public API MCP Server - FastMCP with D402 Transport Wrapper

Uses the CCXT Python library directly to access 100+ cryptocurrency exchanges.
This is a PUBLIC data server - no exchange API keys required.

Architecture:
- FastMCP for tool decorators and Context objects
- D402MCPTransport wraps the /mcp route for HTTP 402 interception
- CCXT library provides unified access to 100+ exchanges

Environment Variables:
- SERVER_ADDRESS: Payment address (IATP wallet contract)
- MCP_OPERATOR_PRIVATE_KEY: Operator signing key
- D402_TESTING_MODE: Skip facilitator (default: true)
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio

import ccxt
import ccxt.async_support as ccxt_async
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

# Payment configuration
PAYMENT_TOKEN_ADDRESS = os.getenv("DEFAULT_SETTLEMENT_TOKEN", "0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822")
PAYMENT_TOKEN_DECIMALS = 18  # TRAIA has 18 decimals
PAYMENT_NETWORK = os.getenv("DEFAULT_SETTLEMENT_NETWORK", "sepolia")

# Price: 0.0001 TRAIA = 100000000000000 wei (10^14)
PRICE_AMOUNT = "100000000000000"

logger.info("="*80)
logger.info(f"CCXT Public API MCP Server (FastMCP + D402)")
logger.info(f"CCXT version: {ccxt.__version__}")
logger.info(f"Supported exchanges: {len(ccxt.exchanges)}")
logger.info(f"Payment: {SERVER_ADDRESS}")
logger.info("="*80)

# Create FastMCP server
mcp = FastMCP("CCXT Public API MCP Server", host="0.0.0.0")

logger.info(f"✅ FastMCP server created")


def get_exchange(exchange_id: str) -> ccxt.Exchange:
    """Get a CCXT exchange instance by ID."""
    exchange_id = exchange_id.lower()
    if exchange_id not in ccxt.exchanges:
        raise ValueError(f"Exchange '{exchange_id}' not found. Available: {', '.join(ccxt.exchanges[:10])}...")
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({
        'enableRateLimit': True,
        'timeout': 30000,
    })


async def get_exchange_async(exchange_id: str) -> ccxt_async.Exchange:
    """Get an async CCXT exchange instance by ID."""
    exchange_id = exchange_id.lower()
    if exchange_id not in ccxt_async.exchanges:
        raise ValueError(f"Exchange '{exchange_id}' not found. Available: {', '.join(ccxt_async.exchanges[:10])}...")
    exchange_class = getattr(ccxt_async, exchange_id)
    return exchange_class({
        'enableRateLimit': True,
        'timeout': 30000,
    })


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="List all supported cryptocurrency exchanges"
)
async def list_exchanges(context: Context) -> Dict[str, Any]:
    """
    List all supported cryptocurrency exchanges.
    Returns exchange IDs that can be used with other CCXT endpoints.
    """
    try:
        return {
            "exchanges": ccxt.exchanges,
            "count": len(ccxt.exchanges),
            "version": ccxt.__version__
        }
    except Exception as e:
        logger.error(f"Error in list_exchanges: {e}")
        return {"error": str(e)}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch all trading markets/pairs for an exchange"
)
async def fetch_markets(
    context: Context,
    exchange: str
) -> Dict[str, Any]:
    """
    Fetch all trading markets/pairs for a specific exchange.
    Returns detailed market information including symbols, base/quote currencies, precision, and limits.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        markets = await ex.load_markets()
        return {
            "exchange": exchange,
            "markets_count": len(markets),
            "markets": [
                {
                    "symbol": m["symbol"],
                    "base": m.get("base"),
                    "quote": m.get("quote"),
                    "active": m.get("active"),
                    "type": m.get("type"),
                }
                for m in markets.values()
            ][:100]  # Limit to first 100 for response size
        }
    except Exception as e:
        logger.error(f"Error in fetch_markets: {e}")
        return {"error": str(e), "exchange": exchange}
    finally:
        if ex:
            await ex.close()


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch current ticker data for a trading pair"
)
async def fetch_ticker(
    context: Context,
    exchange: str,
    symbol: str
) -> Dict[str, Any]:
    """
    Fetch current ticker data for a trading pair.
    Returns last price, bid, ask, volume, and price change statistics.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        await ex.load_markets()
        ticker = await ex.fetch_ticker(symbol)
        return {
            "exchange": exchange,
            "symbol": symbol,
            "ticker": {
                "symbol": ticker.get("symbol"),
                "timestamp": ticker.get("timestamp"),
                "datetime": ticker.get("datetime"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "last": ticker.get("last"),
                "open": ticker.get("open"),
                "close": ticker.get("close"),
                "change": ticker.get("change"),
                "percentage": ticker.get("percentage"),
                "baseVolume": ticker.get("baseVolume"),
                "quoteVolume": ticker.get("quoteVolume"),
            }
        }
    except Exception as e:
        logger.error(f"Error in fetch_ticker: {e}")
        return {"error": str(e), "exchange": exchange, "symbol": symbol}
    finally:
        if ex:
            await ex.close()


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch ticker data for multiple trading pairs"
)
async def fetch_tickers(
    context: Context,
    exchange: str,
    symbols: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch ticker data for multiple trading pairs at once.
    If symbols not specified, returns top tickers by volume.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        await ex.load_markets()
        
        symbol_list = None
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(",")]
        
        tickers = await ex.fetch_tickers(symbol_list)
        
        # Return limited set of ticker info
        result = {}
        for sym, t in list(tickers.items())[:50]:  # Limit to 50
            result[sym] = {
                "last": t.get("last"),
                "bid": t.get("bid"),
                "ask": t.get("ask"),
                "change": t.get("percentage"),
                "volume": t.get("baseVolume"),
            }
        
        return {
            "exchange": exchange,
            "tickers_count": len(result),
            "tickers": result
        }
    except Exception as e:
        logger.error(f"Error in fetch_tickers: {e}")
        return {"error": str(e), "exchange": exchange}
    finally:
        if ex:
            await ex.close()


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch the order book for a trading pair"
)
async def fetch_order_book(
    context: Context,
    exchange: str,
    symbol: str,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Fetch the order book (market depth) for a trading pair.
    Shows bids and asks with prices and amounts.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        await ex.load_markets()
        orderbook = await ex.fetch_order_book(symbol, limit)
        return {
            "exchange": exchange,
            "symbol": symbol,
            "timestamp": orderbook.get("timestamp"),
            "datetime": orderbook.get("datetime"),
            "bids": orderbook.get("bids", [])[:limit],
            "asks": orderbook.get("asks", [])[:limit],
            "bids_count": len(orderbook.get("bids", [])),
            "asks_count": len(orderbook.get("asks", [])),
        }
    except Exception as e:
        logger.error(f"Error in fetch_order_book: {e}")
        return {"error": str(e), "exchange": exchange, "symbol": symbol}
    finally:
        if ex:
            await ex.close()


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch OHLCV candlestick data for charting"
)
async def fetch_ohlcv(
    context: Context,
    exchange: str,
    symbol: str,
    timeframe: str = "1h",
    limit: int = 100
) -> Dict[str, Any]:
    """
    Fetch OHLCV (candlestick) data for charting and technical analysis.
    Returns open, high, low, close, volume for each candle.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        await ex.load_markets()
        
        if not ex.has.get("fetchOHLCV"):
            return {"error": f"Exchange {exchange} does not support OHLCV data"}
        
        ohlcv = await ex.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        # Format OHLCV data
        candles = []
        for c in ohlcv:
            candles.append({
                "timestamp": c[0],
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5],
            })
        
        return {
            "exchange": exchange,
            "symbol": symbol,
            "timeframe": timeframe,
            "candles_count": len(candles),
            "candles": candles
        }
    except Exception as e:
        logger.error(f"Error in fetch_ohlcv: {e}")
        return {"error": str(e), "exchange": exchange, "symbol": symbol}
    finally:
        if ex:
            await ex.close()


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch recent public trades for a trading pair"
)
async def fetch_trades(
    context: Context,
    exchange: str,
    symbol: str,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Fetch recent public trades for a trading pair.
    Returns trade history with price, amount, side, and timestamp.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        await ex.load_markets()
        trades = await ex.fetch_trades(symbol, limit=limit)
        
        # Format trades
        result = []
        for t in trades:
            result.append({
                "id": t.get("id"),
                "timestamp": t.get("timestamp"),
                "datetime": t.get("datetime"),
                "symbol": t.get("symbol"),
                "side": t.get("side"),
                "price": t.get("price"),
                "amount": t.get("amount"),
                "cost": t.get("cost"),
            })
        
        return {
            "exchange": exchange,
            "symbol": symbol,
            "trades_count": len(result),
            "trades": result
        }
    except Exception as e:
        logger.error(f"Error in fetch_trades: {e}")
        return {"error": str(e), "exchange": exchange, "symbol": symbol}
    finally:
        if ex:
            await ex.close()


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch all currencies supported by an exchange"
)
async def fetch_currencies(
    context: Context,
    exchange: str
) -> Dict[str, Any]:
    """
    Fetch all currencies supported by an exchange.
    Includes deposit/withdrawal info, precision, and network details.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        await ex.load_markets()
        currencies = ex.currencies
        
        result = []
        for code, c in list(currencies.items())[:100]:
            result.append({
                "code": code,
                "name": c.get("name"),
                "active": c.get("active"),
                "precision": c.get("precision"),
            })
        
        return {
            "exchange": exchange,
            "currencies_count": len(currencies),
            "currencies": result
        }
    except Exception as e:
        logger.error(f"Error in fetch_currencies: {e}")
        return {"error": str(e), "exchange": exchange}
    finally:
        if ex:
            await ex.close()


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch the operational status of an exchange"
)
async def fetch_status(
    context: Context,
    exchange: str
) -> Dict[str, Any]:
    """
    Fetch the current operational status of an exchange.
    Includes maintenance info and system status.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        
        if ex.has.get("fetchStatus"):
            status = await ex.fetch_status()
            return {
                "exchange": exchange,
                "status": status.get("status"),
                "updated": status.get("updated"),
                "eta": status.get("eta"),
                "url": status.get("url"),
            }
        else:
            return {
                "exchange": exchange,
                "status": "unknown",
                "message": f"Exchange {exchange} does not provide status endpoint"
            }
    except Exception as e:
        logger.error(f"Error in fetch_status: {e}")
        return {"error": str(e), "exchange": exchange}
    finally:
        if ex:
            await ex.close()


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch the server time of an exchange"
)
async def fetch_time(
    context: Context,
    exchange: str
) -> Dict[str, Any]:
    """
    Fetch the current server time of an exchange.
    Useful for timestamp synchronization.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        
        if ex.has.get("fetchTime"):
            timestamp = await ex.fetch_time()
            return {
                "exchange": exchange,
                "timestamp": timestamp,
                "datetime": datetime.fromtimestamp(timestamp / 1000).isoformat() if timestamp else None
            }
        else:
            return {
                "exchange": exchange,
                "error": f"Exchange {exchange} does not provide time endpoint"
            }
    except Exception as e:
        logger.error(f"Error in fetch_time: {e}")
        return {"error": str(e), "exchange": exchange}
    finally:
        if ex:
            await ex.close()


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch best bid and ask prices for multiple symbols"
)
async def fetch_bids_asks(
    context: Context,
    exchange: str,
    symbols: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch the best bid and ask prices for multiple symbols.
    More efficient than fetching full order books.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        await ex.load_markets()
        
        symbol_list = None
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(",")]
        
        if ex.has.get("fetchBidsAsks"):
            bids_asks = await ex.fetch_bids_asks(symbol_list)
            result = {}
            for sym, ba in list(bids_asks.items())[:50]:
                result[sym] = {
                    "bid": ba.get("bid"),
                    "ask": ba.get("ask"),
                    "bidVolume": ba.get("bidVolume"),
                    "askVolume": ba.get("askVolume"),
                }
            return {
                "exchange": exchange,
                "count": len(result),
                "bids_asks": result
            }
        else:
            # Fall back to tickers
            tickers = await ex.fetch_tickers(symbol_list)
            result = {}
            for sym, t in list(tickers.items())[:50]:
                result[sym] = {
                    "bid": t.get("bid"),
                    "ask": t.get("ask"),
                }
            return {
                "exchange": exchange,
                "count": len(result),
                "bids_asks": result,
                "note": "Fetched from tickers (fetchBidsAsks not available)"
            }
    except Exception as e:
        logger.error(f"Error in fetch_bids_asks: {e}")
        return {"error": str(e), "exchange": exchange}
    finally:
        if ex:
            await ex.close()


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch the current funding rate for perpetual futures"
)
async def fetch_funding_rate(
    context: Context,
    exchange: str,
    symbol: str
) -> Dict[str, Any]:
    """
    Fetch the current funding rate for a perpetual futures contract.
    Only available on exchanges with derivatives trading.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        await ex.load_markets()
        
        if ex.has.get("fetchFundingRate"):
            funding = await ex.fetch_funding_rate(symbol)
            return {
                "exchange": exchange,
                "symbol": symbol,
                "fundingRate": funding.get("fundingRate"),
                "fundingTimestamp": funding.get("fundingTimestamp"),
                "fundingDatetime": funding.get("fundingDatetime"),
                "nextFundingRate": funding.get("nextFundingRate"),
                "nextFundingTimestamp": funding.get("nextFundingTimestamp"),
            }
        else:
            return {
                "exchange": exchange,
                "symbol": symbol,
                "error": f"Exchange {exchange} does not support funding rates"
            }
    except Exception as e:
        logger.error(f"Error in fetch_funding_rate: {e}")
        return {"error": str(e), "exchange": exchange, "symbol": symbol}
    finally:
        if ex:
            await ex.close()


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch funding rates for multiple perpetual futures"
)
async def fetch_funding_rates(
    context: Context,
    exchange: str,
    symbols: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch funding rates for multiple perpetual futures contracts at once.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        await ex.load_markets()
        
        symbol_list = None
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(",")]
        
        if ex.has.get("fetchFundingRates"):
            rates = await ex.fetch_funding_rates(symbol_list)
            result = {}
            for sym, r in list(rates.items())[:50]:
                result[sym] = {
                    "fundingRate": r.get("fundingRate"),
                    "fundingTimestamp": r.get("fundingTimestamp"),
                }
            return {
                "exchange": exchange,
                "count": len(result),
                "funding_rates": result
            }
        else:
            return {
                "exchange": exchange,
                "error": f"Exchange {exchange} does not support bulk funding rates"
            }
    except Exception as e:
        logger.error(f"Error in fetch_funding_rates: {e}")
        return {"error": str(e), "exchange": exchange}
    finally:
        if ex:
            await ex.close()


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount=PRICE_AMOUNT,
        asset=TokenAsset(
            address=PAYMENT_TOKEN_ADDRESS,
            decimals=PAYMENT_TOKEN_DECIMALS,
            network=PAYMENT_NETWORK,
            eip712=EIP712Domain(name="IATPWallet", version="1")
        )
    ),
    description="Fetch historical funding rates for perpetual futures"
)
async def fetch_funding_rate_history(
    context: Context,
    exchange: str,
    symbol: str,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Fetch historical funding rates for a perpetual futures contract.
    """
    ex = None
    try:
        ex = await get_exchange_async(exchange)
        await ex.load_markets()
        
        if ex.has.get("fetchFundingRateHistory"):
            history = await ex.fetch_funding_rate_history(symbol, limit=limit)
            result = []
            for h in history:
                result.append({
                    "symbol": h.get("symbol"),
                    "fundingRate": h.get("fundingRate"),
                    "timestamp": h.get("timestamp"),
                    "datetime": h.get("datetime"),
                })
            return {
                "exchange": exchange,
                "symbol": symbol,
                "count": len(result),
                "history": result
            }
        else:
            return {
                "exchange": exchange,
                "symbol": symbol,
                "error": f"Exchange {exchange} does not support funding rate history"
            }
    except Exception as e:
        logger.error(f"Error in fetch_funding_rate_history: {e}")
        return {"error": str(e), "exchange": exchange, "symbol": symbol}
    finally:
        if ex:
            await ex.close()


# ============================================================================
# APPLICATION SETUP WITH STARLETTE MIDDLEWARE
# ============================================================================

def create_app_with_middleware():
    """
    Create Starlette app with d402 payment middleware.
    """
    logger.info("🔧 Creating FastMCP app with middleware...")
    
    # Get FastMCP's Starlette app
    app = mcp.streamable_http_app()
    logger.info(f"✅ Got FastMCP Starlette app")
    
    # Extract payment configs from decorators
    tool_payment_configs = extract_payment_configs_from_mcp(mcp, SERVER_ADDRESS)
    logger.info(f"📊 Extracted {len(tool_payment_configs)} payment configs")
    
    # D402 Configuration
    facilitator_url = os.getenv("FACILITATOR_URL") or os.getenv("D402_FACILITATOR_URL")
    operator_key = os.getenv("MCP_OPERATOR_PRIVATE_KEY")
    network = os.getenv("NETWORK", "sepolia")
    testing_mode = os.getenv("D402_TESTING_MODE", "false").lower() == "true"
    
    logger.info("="*60)
    logger.info("D402 Payment Protocol Configuration:")
    logger.info(f"  Server Address: {SERVER_ADDRESS}")
    logger.info(f"  Network: {network}")
    logger.info(f"  Operator Key: {'✅ Set' if operator_key else '❌ Not set'}")
    logger.info(f"  Testing Mode: {'⚠️  ENABLED' if testing_mode else '✅ DISABLED'}")
    if facilitator_url:
        logger.info(f"  Facilitator: {facilitator_url}")
    logger.info("="*60)
    
    if not facilitator_url and not testing_mode:
        logger.error("❌ FACILITATOR_URL required when testing_mode is disabled!")
        raise ValueError("Set FACILITATOR_URL or enable D402_TESTING_MODE=true")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )
    
    # Add D402 payment middleware
    app.add_middleware(
        D402PaymentMiddleware,
        tool_payment_configs=tool_payment_configs,
        server_address=SERVER_ADDRESS,
        requires_auth=False,
        testing_mode=testing_mode,
        facilitator_url=facilitator_url,
        facilitator_api_key=os.getenv("D402_FACILITATOR_API_KEY"),
        server_name="ccxt-public-api-mcp-server"
    )
    logger.info("✅ Added D402PaymentMiddleware")
    
    # Add health check endpoint
    @app.route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        """Health check endpoint for container orchestration."""
        return JSONResponse(
            content={
                "status": "healthy",
                "service": "ccxt-public-api-mcp-server",
                "ccxt_version": ccxt.__version__,
                "exchanges_count": len(ccxt.exchanges),
                "timestamp": datetime.now().isoformat()
            }
        )
    logger.info("✅ Added /health endpoint")
    
    return app


if __name__ == "__main__":
    logger.info("="*80)
    logger.info(f"Starting CCXT Public API MCP Server")
    logger.info(f"CCXT {ccxt.__version__} - {len(ccxt.exchanges)} exchanges supported")
    logger.info("="*80)
    
    app = create_app_with_middleware()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
