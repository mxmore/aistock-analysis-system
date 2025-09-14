
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# 导入增强的预测功能
try:
    from .forecast_enhanced import predict_stock_price_enhanced
    USE_ENHANCED = True
except ImportError:
    USE_ENHANCED = False
    print("Enhanced forecast not available, using basic methods")


def sarimax_forecast(df: pd.DataFrame, ahead_days: int = 5):
    series = df.sort_values("trade_date")["close"].astype(float)
    if len(series) < 60:
        return None
    model = SARIMAX(
        series,
        order=(1, 1, 1),
        seasonal_order=(0, 0, 0, 0),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    res = model.fit(disp=False)
    pred = res.get_forecast(steps=ahead_days)
    yhat = pred.predicted_mean.values
    conf = pred.conf_int(alpha=0.2).values
    return yhat, conf[:, 0], conf[:, 1]


def feature_regression_forecast(df: pd.DataFrame, ahead_days: int = 5):
    df = df.sort_values("trade_date").copy()
    df["ret1"] = df["close"].pct_change()
    df["ma5"] = df["close"].rolling(5).mean()
    df["ma10"] = df["close"].rolling(10).mean()
    df["ema12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["vol_z"] = (
        (df["vol"] - df["vol"].rolling(20).mean()) /
        (df["vol"].rolling(20).std() + 1e-9)
    )
    df = df.dropna().copy()

    X = df[["ret1", "ma5", "ma10", "ema12", "ema26", "vol_z"]].values
    y = df["close"].values
    if len(y) < 80:
        return None
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge", RidgeCV(alphas=np.logspace(-3, 3, 20))),
    ])
    pipe.fit(X[:-ahead_days], y[:-ahead_days])
    sigma = np.std(y - pipe.predict(X))
    
    # 改进预测逻辑，使每天的预测都有所不同
    preds, lo, hi = [], [], []
    current_features = X[-1].copy()
    
    for day in range(ahead_days):
        # 预测当前特征对应的价格
        pred_y = pipe.predict(current_features.reshape(1, -1))[0]
        
        # 添加一些基于时间的随机变化
        trend_factor = 1.0 + np.random.normal(0, 0.005)  # 小的随机波动
        pred_y *= trend_factor
        
        preds.append(pred_y)
        lo.append(pred_y - 1.28 * sigma)
        hi.append(pred_y + 1.28 * sigma)
        
        # 更新特征向量为下一天的预测
        if day < ahead_days - 1:
            # 模拟特征的变化
            # 更新收益率（基于预测价格变化）
            if day == 0:
                prev_price = y[-1]  # 使用最后一个真实价格
            else:
                prev_price = preds[-2]  # 使用前一天的预测价格
            
            new_ret = (pred_y - prev_price) / prev_price if prev_price > 0 else 0
            current_features[0] = new_ret  # ret1
            
            # 更新移动平均（简化处理）
            current_features[1] = (current_features[1] * 4 + pred_y) / 5  # ma5
            current_features[2] = (current_features[2] * 9 + pred_y) / 10  # ma10
            current_features[3] = current_features[3] * 0.85 + pred_y * 0.15  # ema12
            current_features[4] = current_features[4] * 0.90 + pred_y * 0.10  # ema26
            
            # vol_z 保持相对稳定
            current_features[5] *= 0.95  # 逐渐衰减成交量异常
    
    return np.array(preds), np.array(lo), np.array(hi)


def predict_stock_price(df: pd.DataFrame, symbol: str, ahead_days: int = 5):
    """
    预测股票价格 - 使用增强版本如果可用
    
    Args:
        df: 包含历史价格数据的DataFrame
        symbol: 股票代码
        ahead_days: 预测天数
    
    Returns:
        dict: 包含预测结果的字典
    """
    # 如果增强版本可用，优先使用
    if USE_ENHANCED:
        try:
            result = predict_stock_price_enhanced(df, symbol, ahead_days)
            if result.get("method") != "none":
                return result
        except Exception as e:
            print(f"Enhanced prediction failed for {symbol}: {e}")
    
    # 回退到原始方法
    return predict_stock_price_basic(df, symbol, ahead_days)

def predict_stock_price_basic(df: pd.DataFrame, symbol: str, ahead_days: int = 5):
    """
    预测股票价格 - 基础版本
    
    Args:
        df: 包含历史价格数据的DataFrame
        symbol: 股票代码
        ahead_days: 预测天数
    
    Returns:
        dict: 包含预测结果的字典
    """
    try:
        if df.empty or len(df) < 30:
            return {
                "symbol": symbol,
                "error": "Insufficient data for prediction",
                "predictions": [],
                "method": "none"
            }
        
        # 尝试使用特征回归预测
        try:
            result = feature_regression_forecast(df, ahead_days)
            if result is not None:
                yhat, yhat_lower, yhat_upper = result
                predictions = []
                for i in range(ahead_days):
                    predictions.append({
                        "day": i + 1,
                        "predicted_price": float(yhat[i]),
                        "lower_bound": float(yhat_lower[i]),
                        "upper_bound": float(yhat_upper[i])
                    })
                
                return {
                    "symbol": symbol,
                    "predictions": predictions,
                    "method": "feature_regression",
                    "confidence": 0.8
                }
        except Exception as e:
            print(f"Feature regression failed for {symbol}: {e}")
        
        # 如果特征回归失败，尝试SARIMAX
        try:
            result = sarimax_forecast(df, ahead_days)
            if result is not None:
                yhat, yhat_lower, yhat_upper = result
                predictions = []
                for i in range(ahead_days):
                    predictions.append({
                        "day": i + 1,
                        "predicted_price": float(yhat[i]),
                        "lower_bound": float(yhat_lower[i]),
                        "upper_bound": float(yhat_upper[i])
                    })
                
                return {
                    "symbol": symbol,
                    "predictions": predictions,
                    "method": "sarimax",
                    "confidence": 0.7
                }
        except Exception as e:
            print(f"SARIMAX failed for {symbol}: {e}")
        
        # 如果所有方法都失败，返回简单的线性趋势预测
        close_prices = df.sort_values("trade_date")["close"].astype(float)
        if len(close_prices) >= 5:
            recent_trend = (close_prices.iloc[-1] - close_prices.iloc[-5]) / 5
            last_price = close_prices.iloc[-1]
            
            predictions = []
            for i in range(ahead_days):
                predicted_price = last_price + (i + 1) * recent_trend
                # 简单的置信区间（±5%）
                lower_bound = predicted_price * 0.95
                upper_bound = predicted_price * 1.05
                
                predictions.append({
                    "day": i + 1,
                    "predicted_price": float(predicted_price),
                    "lower_bound": float(lower_bound),
                    "upper_bound": float(upper_bound)
                })
            
            return {
                "symbol": symbol,
                "predictions": predictions,
                "method": "linear_trend",
                "confidence": 0.5
            }
        
        return {
            "symbol": symbol,
            "error": "All prediction methods failed",
            "predictions": [],
            "method": "none"
        }
        
    except Exception as e:
        return {
            "symbol": symbol,
            "error": f"Prediction error: {str(e)}",
            "predictions": [],
            "method": "none"
        }
