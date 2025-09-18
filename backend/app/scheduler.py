
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime, timedelta
import pandas as pd

from .db import SessionLocal, engine
from .models import Watchlist, PriceDaily, Signal, Forecast, Task, TaskType, TaskStatus
from .data_source import fetch_daily
from .signals import compute_signals
from .forecast import predict_stock_price
from .report import plain_summary, llm_summarize
from .news_service import NewsScheduler
from .news_strategy import NewsStrategyScheduler

TZ = os.getenv("TZ", "Asia/Taipei")
AHEAD = int(os.getenv("FORECAST_AHEAD_DAYS", "5"))

async def run_daily_pipeline() -> bool:
    now = datetime.now()
    with SessionLocal() as session:
        watches = session.execute(select(Watchlist).where(Watchlist.enabled == True)).scalars().all()
        for w in watches:
            start = (now - timedelta(days=365 * 3)).strftime("%Y%m%d")
            df = fetch_daily(w.symbol, start_date=start)
            if df.empty:
                continue
            for _, row in df.iterrows():
                stmt = pg_insert(PriceDaily).values(
                    symbol=row["symbol"],
                    trade_date=row["trade_date"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    pct_chg=row.get("pct_chg"),
                    vol=(int(row["vol"]) if pd.notna(row["vol"]) else None),
                    amount=row.get("amount"),
                ).on_conflict_do_nothing(index_elements=["symbol", "trade_date"])
                session.execute(stmt)
            session.commit()

            qdf = pd.read_sql_query(
                "SELECT trade_date, open, high, low, close, pct_chg, vol, amount FROM prices_daily WHERE symbol = %s ORDER BY trade_date",
                con=engine,
                params=(w.symbol,),
            )
            if len(qdf) < 50:
                continue
            sig_df = compute_signals(qdf)
            last_sig = sig_df.iloc[-1]
            stmt_sig = pg_insert(Signal).values(
                symbol=w.symbol,
                trade_date=last_sig["trade_date"],
                ma_short=last_sig["ma_s"],
                ma_long=last_sig["ma_l"],
                rsi=last_sig["rsi"],
                macd=last_sig["macd"],
                signal_score=last_sig["signal_score"],
                action=last_sig["action"],
            ).on_conflict_do_nothing(index_elements=["symbol", "trade_date"])
            session.execute(stmt_sig)

            # 使用增强预测模型
            prediction_result = predict_stock_price(qdf, w.symbol, ahead_days=AHEAD)
            
            if prediction_result.get("predictions"):
                run_at = now
                model_name = prediction_result.get("method", "enhanced").upper()
                
                for pred in prediction_result["predictions"]:
                    day = pred["day"]
                    target_date = qdf["trade_date"].iloc[-1] + timedelta(days=day)
                    stmt_fc = insert(Forecast).values(
                        symbol=w.symbol,
                        run_at=run_at,
                        target_date=target_date,
                        model=model_name,
                        yhat=float(pred["predicted_price"]),
                        yhat_lower=float(pred["lower_bound"]),
                        yhat_upper=float(pred["upper_bound"]),
                    )
                    session.execute(stmt_fc)
            session.commit()

            fdf = pd.read_sql_query(
                "SELECT target_date, avg(yhat) yhat, avg(yhat_lower) yl, avg(yhat_upper) yu FROM forecasts WHERE symbol=%s AND run_at=%s GROUP BY target_date ORDER BY target_date",
                con=engine,
                params=(w.symbol, run_at),
            )
            preds_view: list[tuple] = []
            if not fdf.empty:
                for _, row in fdf.iterrows():
                    preds_view.append((row["target_date"], row["yhat"], row["yl"], row["yu"]))
            today_row = qdf.iloc[-1]
            summary = plain_summary(w.symbol, w.name, today_row, last_sig, preds_view)
            pretty = await llm_summarize(summary)
            print(pretty)
            
    # Run intelligent news collection
    await run_intelligent_news_collection()
    
    return True

async def run_intelligent_news_collection():
    """
    Run intelligent news collection based on watchlist and strategies
    """
    try:
        strategy_scheduler = NewsStrategyScheduler()
        result = await strategy_scheduler.run_intelligent_collection()
        
        print(f"✓ Intelligent news collection completed:")
        print(f"  - Strategies executed: {result.get('strategies_executed', 0)}")
        print(f"  - Strategies skipped: {result.get('strategies_skipped', 0)}")
        print(f"  - Total articles collected: {result.get('total_articles', 0)}")
        
        return result
        
    except Exception as e:
        print(f"✗ Intelligent news collection failed: {e}")
        raise

async def run_news_collection():
    """
    Run news collection for all enabled stocks (Legacy method)
    """
    try:
        news_scheduler = NewsScheduler()
        await news_scheduler.run_scheduled_news_collection()
        print("✓ Legacy news collection completed successfully")
    except Exception as e:
        print(f"✗ Legacy news collection failed: {e}")

async def run_manual_intelligent_collection():
    """
    Manually trigger intelligent news collection
    """
    try:
        return await run_intelligent_news_collection()
    except Exception as e:
        print(f"✗ Manual intelligent news collection failed: {e}")
        raise

async def run_manual_news_collection(symbol: str):
    """
    Manually run news collection for a specific stock
    """
    try:
        with SessionLocal() as session:
            # Check if stock exists in watchlist
            stock = session.execute(
                select(Watchlist).where(Watchlist.symbol == symbol)
            ).scalar_one_or_none()
            
            if not stock:
                raise ValueError(f"Stock {symbol} not found in watchlist")
        
        news_scheduler = NewsScheduler()
        await news_scheduler._collect_news_for_stock(symbol, stock.name)
        print(f"✓ News collection for {symbol} completed successfully")
        
    except Exception as e:
        print(f"✗ News collection for {symbol} failed: {e}")
        raise

def attach_scheduler(app):
    try:
        sched = AsyncIOScheduler(timezone=TZ)
        hour = int(os.getenv("CRON_HOUR", "16"))
        minute = int(os.getenv("CRON_MINUTE", "10"))
        
        # 添加主要数据处理作业
        main_job = sched.add_job(
            run_daily_pipeline, 
            CronTrigger(hour=hour, minute=minute),
            id='daily_pipeline',
            replace_existing=True,
            max_instances=1
        )
        
        # 添加智能新闻收集作业 - 每4小时运行一次
        intelligent_news_job = sched.add_job(
            run_intelligent_news_collection,
            CronTrigger(hour='*/4'),  # 每4小时
            id='intelligent_news_collection',
            replace_existing=True,
            max_instances=1
        )
        
        # 添加传统新闻收集作业 - 每12小时运行一次 (作为备份)
        legacy_news_job = sched.add_job(
            run_news_collection,
            CronTrigger(hour='*/12'),  # 每12小时
            id='legacy_news_collection',
            replace_existing=True,
            max_instances=1
        )
        
        sched.start()
        app.state.scheduler = sched
        print(f"✓ Scheduler started:")
        print(f"  - Daily pipeline: {hour:02d}:{minute:02d} {TZ}")
        print(f"  - Intelligent news collection: Every 4 hours")
        print(f"  - Legacy news collection: Every 12 hours")
        return sched
        
    except Exception as e:
        print(f"✗ Failed to start scheduler: {e}")
        raise
