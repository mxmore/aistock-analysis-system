"""
任务管理器 - 负责创建、执行和监控任务
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .db import SessionLocal
from .models import Task, Report, Watchlist, PriceDaily, Signal, Forecast, TaskStatus, TaskType

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self):
        self.running_tasks = set()
        self.max_concurrent_tasks = 3
        self._stopped = False
        
    def stop(self):
        """停止任务管理器"""
        self._stopped = True
        
    def is_stopped(self) -> bool:
        """检查任务管理器是否已停止"""
        return self._stopped
        
    def create_task(self, task_type: str, symbol: str, priority: int = 5, metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """创建新任务
        
        Args:
            task_type: 任务类型 (TaskType)
            symbol: 股票代码
            priority: 优先级 (1-10, 1最高)
            metadata: 任务元数据
            
        Returns:
            task_id: 创建的任务ID，如果失败返回None
        """
        try:
            with SessionLocal() as session:
                # 检查是否已有相同任务在队列中
                existing_task = session.execute(
                    select(Task).where(
                        and_(
                            Task.symbol == symbol,
                            Task.task_type == task_type,
                            Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
                        )
                    )
                ).scalar_one_or_none()
                
                if existing_task:
                    logger.info(f"Task already exists for {symbol} with type {task_type}")
                    return existing_task.id
                
                # 创建新任务
                task = Task(
                    task_type=task_type,
                    symbol=symbol,
                    status=TaskStatus.PENDING,
                    priority=priority,
                    task_metadata=json.dumps(metadata) if metadata else None
                )
                
                session.add(task)
                session.commit()
                session.refresh(task)
                
                logger.info(f"Created task {task.id} for {symbol} with type {task_type}")
                return task.id
                
        except Exception as e:
            logger.error(f"Failed to create task for {symbol}: {e}")
            return None
        
    async def create_report_task(self, symbol: str, priority: int = 5) -> Optional[int]:
        """为指定股票创建报告生成任务"""
        with SessionLocal() as session:
            # 检查是否已有相同任务在队列中
            existing_task = session.execute(
                select(Task).where(
                    and_(
                        Task.symbol == symbol,
                        Task.task_type == TaskType.GENERATE_REPORT,
                        Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
                    )
                )
            ).scalar_one_or_none()
            
            if existing_task:
                logger.info(f"Task already exists for {symbol}, task_id: {existing_task.id}")
                return existing_task.id
            
            # 创建新任务
            new_task = Task(
                task_type=TaskType.GENERATE_REPORT,
                symbol=symbol,
                priority=priority,
                task_metadata=json.dumps({"auto_created": True})
            )
            session.add(new_task)
            session.commit()
            session.refresh(new_task)
            
            logger.info(f"Created report task for {symbol}, task_id: {new_task.id}")
            return new_task.id
    
    async def check_and_create_missing_report_tasks(self) -> List[int]:
        """检查所有自选股票，为没有报告且没有任务的股票创建报告任务"""
        created_tasks = []
        
        with SessionLocal() as session:
            # 获取所有启用的自选股票
            watchlist_stocks = session.execute(
                select(Watchlist.symbol).where(Watchlist.enabled == True)
            ).scalars().all()
            
            for symbol in watchlist_stocks:
                # 检查是否有最新报告
                has_report = session.execute(
                    select(Report).where(
                        and_(Report.symbol == symbol, Report.is_latest == True)
                    )
                ).scalar_one_or_none()
                
                if not has_report:
                    # 检查是否有待处理的任务
                    has_pending_task = session.execute(
                        select(Task).where(
                            and_(
                                Task.symbol == symbol,
                                Task.task_type == TaskType.GENERATE_REPORT,
                                Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if not has_pending_task:
                        task_id = await self.create_report_task(symbol, priority=3)
                        if task_id:
                            created_tasks.append(task_id)
        
        logger.info(f"Created {len(created_tasks)} missing report tasks")
        return created_tasks
    
    async def execute_report_task(self, task_id: int) -> bool:
        """执行报告生成任务"""
        with SessionLocal() as session:
            # 获取任务
            task = session.execute(
                select(Task).where(Task.id == task_id)
            ).scalar_one_or_none()
            
            if not task or task.status != TaskStatus.PENDING:
                logger.warning(f"Task {task_id} not found or not pending")
                return False
            
            # 更新任务状态为运行中
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            session.commit()
            
            try:
                # 生成报告
                success = await self._generate_report(task.symbol, session)
                
                if success:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.utcnow()
                    logger.info(f"Report task {task_id} completed for {task.symbol}")
                else:
                    task.status = TaskStatus.FAILED
                    task.error_message = "Failed to generate report"
                    task.completed_at = datetime.utcnow()
                    logger.error(f"Report task {task_id} failed for {task.symbol}")
                
                session.commit()
                return success
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()
                session.commit()
                logger.error(f"Report task {task_id} failed with exception: {e}")
                return False
    
    async def _generate_report(self, symbol: str, session) -> bool:
        """生成股票报告"""
        try:
            # 获取最新价格数据
            latest_price = session.execute(
                select(PriceDaily).where(PriceDaily.symbol == symbol)
                .order_by(PriceDaily.trade_date.desc())
                .limit(1)
            ).scalar_one_or_none()
            
            # 获取最新信号数据
            latest_signal = session.execute(
                select(Signal).where(Signal.symbol == symbol)
                .order_by(Signal.trade_date.desc())
                .limit(1)
            ).scalar_one_or_none()
            
            # 获取预测数据
            forecasts = session.execute(
                select(Forecast).where(Forecast.symbol == symbol)
                .order_by(Forecast.target_date)
            ).scalars().all()
            
            # 构建报告数据
            price_data = None
            if latest_price:
                price_data = {
                    "trade_date": latest_price.trade_date.isoformat(),
                    "close": float(latest_price.close) if latest_price.close is not None else None,
                    "open": float(latest_price.open) if latest_price.open is not None else None,
                    "high": float(latest_price.high) if latest_price.high is not None else None,
                    "low": float(latest_price.low) if latest_price.low is not None else None,
                    "pct_chg": float(latest_price.pct_chg) if latest_price.pct_chg is not None else None,
                    "vol": latest_price.vol
                }
            
            signal_data = None
            if latest_signal:
                signal_data = {
                    "trade_date": latest_signal.trade_date.isoformat(),
                    "ma_short": float(latest_signal.ma_short) if latest_signal.ma_short is not None else None,
                    "ma_long": float(latest_signal.ma_long) if latest_signal.ma_long is not None else None,
                    "rsi": float(latest_signal.rsi) if latest_signal.rsi is not None else None,
                    "macd": float(latest_signal.macd) if latest_signal.macd is not None else None,
                    "signal_score": float(latest_signal.signal_score) if latest_signal.signal_score is not None else None,
                    "action": latest_signal.action
                }
            
            forecast_data = []
            for f in forecasts:
                forecast_data.append({
                    "target_date": f.target_date.isoformat(),
                    "yhat": float(f.yhat) if f.yhat is not None else None,
                    "yhat_lower": float(f.yhat_lower) if f.yhat_lower is not None else None,
                    "yhat_upper": float(f.yhat_upper) if f.yhat_upper is not None else None,
                    "model": f.model
                })
            
            # 计算数据质量评分
            data_quality_score = self._calculate_data_quality(latest_price, latest_signal, forecasts)
            
            # 计算预测置信度
            prediction_confidence = self._calculate_prediction_confidence(forecasts)
            
            # 生成分析摘要
            analysis_summary = self._generate_analysis_summary(symbol, latest_price, latest_signal, forecasts)
            
            # 获取当前最大版本号
            max_version = session.execute(
                select(Report.version).where(Report.symbol == symbol)
                .order_by(Report.version.desc())
                .limit(1)
            ).scalar_one_or_none()
            
            next_version = (max_version or 0) + 1
            
            # 将之前的报告标记为非最新 - 使用事务确保一致性
            session.execute(
                update(Report)
                .where(and_(Report.symbol == symbol, Report.is_latest == True))
                .values(is_latest=False)
            )
            
            # 立即提交更新，确保数据一致性
            session.commit()
            
            # 创建新报告
            new_report = Report(
                symbol=symbol,
                version=next_version,
                latest_price_data=json.dumps(price_data) if price_data else None,
                signal_data=json.dumps(signal_data) if signal_data else None,
                forecast_data=json.dumps(forecast_data) if forecast_data else None,
                analysis_summary=analysis_summary,
                data_quality_score=data_quality_score,
                prediction_confidence=prediction_confidence,
                is_latest=True
            )
            
            session.add(new_report)
            session.commit()
            
            logger.info(f"Generated report v{next_version} for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating report for {symbol}: {e}")
            return False
    
    def _calculate_data_quality(self, price_data, signal_data, forecasts) -> float:
        """计算数据质量评分 (0-10)"""
        score = 0.0
        
        # 价格数据质量 (40%)
        if price_data and price_data.close:
            score += 4.0
            if price_data.vol and price_data.vol > 0:
                score += 1.0
        
        # 信号数据质量 (40%)
        if signal_data:
            signal_count = sum(1 for v in [signal_data.ma_short, signal_data.ma_long, 
                                         signal_data.rsi, signal_data.macd] if v is not None)
            score += (signal_count / 4) * 4.0
        
        # 预测数据质量 (20%)
        if forecasts:
            valid_forecasts = sum(1 for f in forecasts if f.yhat is not None)
            if valid_forecasts > 0:
                score += min(2.0, valid_forecasts / 5 * 2.0)
        
        return round(score, 2)
    
    def _calculate_prediction_confidence(self, forecasts) -> float:
        """计算预测置信度 (0-1)"""
        if not forecasts:
            return 0.0
        
        # 基于预测区间的宽度来评估置信度
        valid_intervals = []
        for f in forecasts:
            if f.yhat and f.yhat_lower and f.yhat_upper:
                yhat = float(f.yhat)
                yhat_lower = float(f.yhat_lower)
                yhat_upper = float(f.yhat_upper)
                interval_width = abs(yhat_upper - yhat_lower)
                relative_width = interval_width / max(abs(yhat), 1)  # 避免除零
                valid_intervals.append(relative_width)
        
        if not valid_intervals:
            return 0.0
        
        # 区间越窄，置信度越高
        avg_relative_width = sum(valid_intervals) / len(valid_intervals)
        confidence = max(0.0, min(1.0, 1.0 - avg_relative_width))
        
        return round(confidence, 3)
    
    def _generate_analysis_summary(self, symbol: str, price_data, signal_data, forecasts) -> str:
        """生成分析摘要"""
        summary_parts = []
        
        if price_data and price_data.close:
            pct_chg = float(price_data.pct_chg) if price_data.pct_chg is not None else 0
            trend = "上涨" if pct_chg > 0 else "下跌" if pct_chg < 0 else "平盘"
            summary_parts.append(f"最新收盘价 {float(price_data.close):.2f}，{trend} {abs(pct_chg):.2f}%")
        
        if signal_data:
            if signal_data.action:
                summary_parts.append(f"技术信号：{signal_data.action}")
            if signal_data.signal_score is not None:
                summary_parts.append(f"信号评分：{float(signal_data.signal_score):.1f}")
        
        if forecasts:
            future_forecasts = [f for f in forecasts if f.target_date > datetime.now().date()]
            if future_forecasts:
                next_forecast = future_forecasts[0]
                if next_forecast.yhat:
                    summary_parts.append(f"短期预测：{float(next_forecast.yhat):.2f}")
        
        return " | ".join(summary_parts) if summary_parts else f"{symbol} 数据分析报告已生成"
    
    async def get_pending_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取待处理任务"""
        with SessionLocal() as session:
            tasks = session.execute(
                select(Task).where(Task.status == TaskStatus.PENDING)
                .order_by(Task.priority.asc(), Task.created_at.asc())
                .limit(limit)
            ).scalars().all()
            
            return [
                {
                    "id": task.id,
                    "symbol": task.symbol,
                    "task_type": task.task_type,
                    "priority": task.priority,
                    "created_at": task.created_at.isoformat()
                }
                for task in tasks
            ]
    
    async def process_tasks(self):
        """处理待处理的任务"""
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            return
        
        with SessionLocal() as session:
            # 获取待处理任务
            tasks = session.execute(
                select(Task).where(Task.status == TaskStatus.PENDING)
                .order_by(Task.priority.asc(), Task.created_at.asc())
                .limit(self.max_concurrent_tasks - len(self.running_tasks))
            ).scalars().all()
            
            for task in tasks:
                if task.id not in self.running_tasks:
                    self.running_tasks.add(task.id)
                    # 异步执行任务
                    asyncio.create_task(self._execute_task_wrapper(task.id))
    
    async def _execute_task_wrapper(self, task_id: int):
        """任务执行包装器"""
        try:
            if task_id in self.running_tasks:
                # 获取任务类型并执行相应的处理器
                with SessionLocal() as session:
                    task = session.execute(
                        select(Task).where(Task.id == task_id)
                    ).scalar_one_or_none()
                    
                    if task:
                        if task.task_type == TaskType.GENERATE_REPORT.value:
                            await self.execute_report_task(task_id)
                        elif task.task_type == TaskType.FETCH_NEWS.value:
                            await self.execute_news_task(task_id)
                        else:
                            logger.warning(f"Unknown task type: {task.task_type}")
        finally:
            self.running_tasks.discard(task_id)
    
    async def execute_news_task(self, task_id: int) -> bool:
        """执行新闻收集任务"""
        with SessionLocal() as session:
            # 获取任务
            task = session.execute(
                select(Task).where(Task.id == task_id)
            ).scalar_one_or_none()
            
            if not task or task.status != TaskStatus.PENDING:
                logger.warning(f"News task {task_id} not found or not pending")
                return False
            
            # 更新任务状态为运行中
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            session.commit()
            
            try:
                # 执行新闻收集
                success = await self._collect_news_for_task(task, session)
                
                if success:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.utcnow()
                    logger.info(f"News task {task_id} completed for {task.symbol}")
                else:
                    task.status = TaskStatus.FAILED
                    task.error_message = "Failed to collect news"
                    task.completed_at = datetime.utcnow()
                    logger.error(f"News task {task_id} failed for {task.symbol}")
                
                session.commit()
                return success
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()
                session.commit()
                logger.error(f"News task {task_id} failed with exception: {e}")
                return False
    
    async def _collect_news_for_task(self, task: Task, session) -> bool:
        """为任务收集新闻"""
        try:
            from .news_strategy import NewsStrategyScheduler
            
            if task.symbol == "ALL":
                # 执行智能新闻收集
                strategy_scheduler = NewsStrategyScheduler()
                result = await strategy_scheduler.run_intelligent_collection()
                return result.get("status") == "completed"
            else:
                # 为特定股票收集新闻
                from .scheduler import run_manual_news_collection
                await run_manual_news_collection(task.symbol)
                return True
                
        except Exception as e:
            logger.error(f"Error collecting news: {e}")
            return False

# 全局任务管理器实例
task_manager = TaskManager()
