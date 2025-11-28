import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.database import SessionLocal
from app.services.trading import trading_service

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def generate_daily_snapshots():
    db = SessionLocal()
    try:
        snapshot_count = await trading_service.create_daily_portfolio_snapshots(db)
        logger.info(f"Daily portfolio snapshots generated: {snapshot_count} snapshots created")
    except Exception as e:
        logger.error(f"Error generating daily portfolio snapshots: {e}")
    finally:
        db.close()


def start_scheduler():
    if os.getenv("TESTING") == "true":
        logger.info("Scheduler disabled in test environment")
        return

    if not scheduler.running:
        scheduler.add_job(
            generate_daily_snapshots,
            'cron',
            hour=0,
            minute=0,
            id='daily_portfolio_snapshots',
            name='Generate Daily Portfolio Snapshots',
            replace_existing=True
        )
        scheduler.start()
        logger.info("Scheduler started with daily portfolio snapshot job")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
