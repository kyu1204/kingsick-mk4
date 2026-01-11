"""
Scheduler entry point for KingSick trading loop.

This module provides the APScheduler-based trading scheduler that
periodically executes the trading loop during market hours.

Usage:
    python -m app.scheduler.main
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import async_session_maker
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.services.kis_api import KISApiClient
from app.services.risk_manager import RiskManager
from app.services.signal_generator import SignalGenerator
from app.services.trading_engine import TradingEngine, TradingMode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")

# Market hours (KRX: 09:00 - 15:30 KST)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 0
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30

TRADING_LOOP_INTERVAL_MINUTES = 5

settings = get_settings()


def is_market_hours() -> bool:
    """Check if current time is within KRX market hours.

    Returns:
        True if within market hours (09:00 - 15:30 KST), False otherwise.
    """
    now = datetime.now(KST)

    if now.weekday() >= 5:
        return False

    market_open = now.replace(
        hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0
    )
    market_close = now.replace(
        hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0
    )

    return market_open <= now <= market_close


async def run_trading_job() -> None:
    """Execute the trading loop for all active users.

    This job runs periodically during market hours and processes
    each user's watchlist and positions.
    """
    if not is_market_hours():
        logger.info("Outside market hours, skipping trading loop")
        return

    logger.info("Starting trading loop execution")

    async with async_session_maker() as db:
        try:
            from sqlalchemy import select

            result = await db.execute(
                select(User).where(User.is_active == True)  # noqa: E712
            )
            users = result.scalars().all()

            for user in users:
                await process_user_trading(db, user)

        except Exception as e:
            logger.error(f"Trading loop failed: {e}", exc_info=True)

    logger.info("Trading loop execution completed")


async def process_user_trading(db: object, user: User) -> None:
    """Process trading for a single user.

    Args:
        db: Database session
        user: User to process trading for
    """
    from sqlalchemy import select

    try:
        result = await db.execute(
            select(WatchlistItem).where(WatchlistItem.user_id == user.id)
        )
        watchlist_items = result.scalars().all()

        if not watchlist_items:
            logger.debug(f"User {user.id} has no watchlist items, skipping")
            return

        watchlist = [item.stock_code for item in watchlist_items]
        stock_names = {item.stock_code: item.stock_name for item in watchlist_items}

        kis_client = KISApiClient(
            app_key=settings.kis_app_key,
            app_secret=settings.kis_app_secret,
            account_no=settings.kis_account_no,
            is_mock=settings.kis_is_mock,
        )
        signal_generator = SignalGenerator()
        risk_manager = RiskManager()

        trading_mode = TradingMode.ALERT

        engine = TradingEngine(
            kis_client=kis_client,
            signal_generator=signal_generator,
            risk_manager=risk_manager,
            mode=trading_mode,
        )

        positions = await kis_client.get_positions()

        result = await engine.run_trading_loop(
            watchlist=watchlist,
            positions=positions,
            user_id=str(user.id),
            telegram_chat_id=user.telegram_chat_id,
            slack_webhook_url=user.slack_webhook_url,
            stock_names=stock_names,
        )

        logger.info(
            f"User {user.id} trading loop: "
            f"processed={result.processed_stocks}, "
            f"signals={result.signals_generated}, "
            f"orders={result.orders_executed}, "
            f"alerts={result.alerts_sent}"
        )

        if result.errors:
            for error in result.errors:
                logger.warning(f"User {user.id} trading error: {error}")

    except Exception as e:
        logger.error(f"Failed to process trading for user {user.id}: {e}", exc_info=True)


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance.

    Returns:
        Configured AsyncIOScheduler instance.
    """
    scheduler = AsyncIOScheduler(timezone=KST)

    scheduler.add_job(
        run_trading_job,
        CronTrigger(
            day_of_week="mon-fri",
            hour=f"{MARKET_OPEN_HOUR}-{MARKET_CLOSE_HOUR}",
            minute=f"*/{TRADING_LOOP_INTERVAL_MINUTES}",
            timezone=KST,
        ),
        id="trading_loop",
        name="Trading Loop",
        replace_existing=True,
        max_instances=1,
    )

    logger.info(
        f"Scheduler configured: trading loop every {TRADING_LOOP_INTERVAL_MINUTES} minutes "
        f"during market hours ({MARKET_OPEN_HOUR:02d}:{MARKET_OPEN_MINUTE:02d} - "
        f"{MARKET_CLOSE_HOUR:02d}:{MARKET_CLOSE_MINUTE:02d} KST)"
    )

    return scheduler


async def main() -> None:
    """Main entry point for the scheduler."""
    logger.info("Starting KingSick Trading Scheduler")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else 'configured'}")

    scheduler = create_scheduler()

    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def signal_handler(sig: signal.Signals) -> None:
        logger.info(f"Received signal {sig.name}, initiating shutdown...")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    try:
        scheduler.start()
        logger.info("Scheduler started successfully")

        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)
        raise
    finally:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
