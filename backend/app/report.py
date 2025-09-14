
import os
from datetime import date
import pandas as pd

USE_LLM = bool(os.getenv("AZURE_OPENAI_KEY", ""))

def plain_summary(
    symbol: str,
    name: str | None,
    today_row: pd.Series,
    signal_row: pd.Series,
    preds: list[tuple[date, float, float, float]]
) -> str:
    n = name or symbol
    action = signal_row.get("action", "HOLD") if signal_row is not None else "HOLD"
    score = float(signal_row.get("signal_score", 0) or 0) if signal_row is not None else 0
    ma_s = float(signal_row.get("ma_s", 0) or 0) if signal_row is not None else 0
    ma_l = float(signal_row.get("ma_l", 0) or 0) if signal_row is not None else 0
    rsi = float(signal_row.get("rsi", 50) or 50) if signal_row is not None else 50
    close = float(today_row["close"])
    pct = float(today_row.get("pct_chg", 0) or 0)

    bullets = [
        f"【{n}】收盘 {close:.2f}（{pct:+.2f}%），短均线 {ma_s:.2f}，长均线 {ma_l:.2f}，RSI {rsi:.1f}。",
        f"综合打分 {score:+.1f} → 建议：{action}（仅供参考）。",
    ]
    if preds:
        t0, p0, lo0, hi0 = preds[0]
        bullets.append(
            f"未来{len(preds)}天预测：第1天 {p0:.2f}（{lo0:.2f}~{hi0:.2f}）。"
        )
    return "\n".join(bullets)

async def llm_summarize(text: str) -> str:
    if not USE_LLM:
        return text
    try:
        import json
        import requests
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        api_key = os.getenv("AZURE_OPENAI_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "把下面的股市技术分析摘要转成口语化、给普通投资者看的简明解读，保留关键数字，控制在150字以内，避免夸大。",
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0.3,
        }
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        r = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=int(os.getenv("AZURE_OPENAI_TIMEOUT", "30")),
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return text


def generate_report_data(symbol: str, price_data=None, signal_data=None, forecast_data=None):
    """
    生成报告数据
    
    Args:
        symbol: 股票代码
        price_data: 价格数据
        signal_data: 信号数据
        forecast_data: 预测数据
    
    Returns:
        dict: 报告数据
    """
    import json
    from datetime import datetime
    
    try:
        report = {
            "symbol": symbol,
            "generated_at": datetime.now().isoformat(),
            "data_quality_score": 0.0,
            "prediction_confidence": 0.0,
            "analysis_summary": ""
        }
        
        # 处理价格数据
        if price_data is not None:
            if isinstance(price_data, pd.DataFrame) and not price_data.empty:
                latest_data = price_data.sort_values("trade_date").iloc[-1]
                report["latest_price_data"] = {
                    "close": float(latest_data["close"]),
                    "open": float(latest_data["open"]) if "open" in latest_data else None,
                    "high": float(latest_data["high"]) if "high" in latest_data else None,
                    "low": float(latest_data["low"]) if "low" in latest_data else None,
                    "volume": int(latest_data["vol"]) if "vol" in latest_data and pd.notna(latest_data["vol"]) else None,
                    "pct_change": float(latest_data["pct_chg"]) if "pct_chg" in latest_data and pd.notna(latest_data["pct_chg"]) else None,
                    "trade_date": latest_data["trade_date"].isoformat() if hasattr(latest_data["trade_date"], 'isoformat') else str(latest_data["trade_date"])
                }
                
                # 计算数据质量分数
                data_points = len(price_data)
                if data_points >= 250:
                    report["data_quality_score"] = 1.0
                elif data_points >= 100:
                    report["data_quality_score"] = 0.8
                elif data_points >= 50:
                    report["data_quality_score"] = 0.6
                else:
                    report["data_quality_score"] = 0.4
        
        # 处理信号数据
        if signal_data is not None:
            if isinstance(signal_data, pd.DataFrame) and not signal_data.empty:
                latest_signal = signal_data.sort_values("trade_date").iloc[-1]
                report["signal_data"] = {
                    "action": latest_signal.get("action", "HOLD"),
                    "signal_score": float(latest_signal["signal_score"]) if "signal_score" in latest_signal and pd.notna(latest_signal["signal_score"]) else 0.0,
                    "ma_short": float(latest_signal["ma_short"]) if "ma_short" in latest_signal and pd.notna(latest_signal["ma_short"]) else None,
                    "ma_long": float(latest_signal["ma_long"]) if "ma_long" in latest_signal and pd.notna(latest_signal["ma_long"]) else None,
                    "rsi": float(latest_signal["rsi"]) if "rsi" in latest_signal and pd.notna(latest_signal["rsi"]) else None,
                    "macd": float(latest_signal["macd"]) if "macd" in latest_signal and pd.notna(latest_signal["macd"]) else None,
                    "trade_date": latest_signal["trade_date"].isoformat() if hasattr(latest_signal["trade_date"], 'isoformat') else str(latest_signal["trade_date"])
                }
        
        # 处理预测数据
        if forecast_data is not None:
            if isinstance(forecast_data, dict) and "predictions" in forecast_data:
                report["forecast_data"] = forecast_data
                report["prediction_confidence"] = forecast_data.get("confidence", 0.5)
            elif hasattr(forecast_data, '__iter__'):
                # 处理预测数组
                predictions = []
                for i, pred in enumerate(forecast_data):
                    if isinstance(pred, (list, tuple)) and len(pred) >= 3:
                        predictions.append({
                            "day": i + 1,
                            "predicted_price": float(pred[1]) if len(pred) > 1 else float(pred[0]),
                            "lower_bound": float(pred[2]) if len(pred) > 2 else None,
                            "upper_bound": float(pred[3]) if len(pred) > 3 else None
                        })
                
                report["forecast_data"] = {
                    "predictions": predictions,
                    "method": "unknown",
                    "confidence": 0.5
                }
                report["prediction_confidence"] = 0.5
        
        # 生成分析摘要
        summary_parts = []
        
        if "latest_price_data" in report:
            price_info = report["latest_price_data"]
            close = price_info["close"]
            pct_change = price_info.get("pct_change", 0) or 0
            summary_parts.append(f"股票{symbol}最新收盘价{close:.2f}，涨跌幅{pct_change:+.2f}%")
        
        if "signal_data" in report:
            signal_info = report["signal_data"]
            action = signal_info.get("action", "HOLD")
            score = signal_info.get("signal_score", 0) or 0
            summary_parts.append(f"技术指标建议{action}，综合评分{score:+.1f}")
        
        if "forecast_data" in report and report["forecast_data"].get("predictions"):
            pred = report["forecast_data"]["predictions"][0]
            summary_parts.append(f"预测明日价格{pred['predicted_price']:.2f}")
        
        report["analysis_summary"] = "；".join(summary_parts) if summary_parts else f"股票{symbol}分析报告"
        
        return report
        
    except Exception as e:
        return {
            "symbol": symbol,
            "error": f"Report generation failed: {str(e)}",
            "generated_at": datetime.now().isoformat(),
            "data_quality_score": 0.0,
            "prediction_confidence": 0.0,
            "analysis_summary": f"报告生成失败: {str(e)}"
        }
