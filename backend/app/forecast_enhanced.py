#!/usr/bin/env python3
"""
改进的股票价格预测模型
包含神经网络训练和时间序列预测
"""
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.pipeline import Pipeline
from sklearn.neural_network import MLPRegressor
from sklearn.ensemble import RandomForestRegressor
import warnings
warnings.filterwarnings('ignore')

def create_sequence_features(df: pd.DataFrame, lookback_days: int = 20):
    """
    创建时间序列特征，包含滞后特征和技术指标
    """
    df = df.sort_values("trade_date").copy()
    
    # 基础价格特征
    df["ret1"] = df["close"].pct_change()
    df["ret5"] = df["close"].pct_change(5)
    df["ret10"] = df["close"].pct_change(10)
    
    # 移动平均特征
    df["ma5"] = df["close"].rolling(5).mean()
    df["ma10"] = df["close"].rolling(10).mean()
    df["ma20"] = df["close"].rolling(20).mean()
    df["ema12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema26"] = df["close"].ewm(span=26, adjust=False).mean()
    
    # 价格相对位置
    df["price_vs_ma5"] = df["close"] / df["ma5"] - 1
    df["price_vs_ma20"] = df["close"] / df["ma20"] - 1
    
    # 成交量特征
    df["vol_ma"] = df["vol"].rolling(20).mean()
    df["vol_ratio"] = df["vol"] / (df["vol_ma"] + 1e-9)
    df["vol_z"] = ((df["vol"] - df["vol_ma"]) / (df["vol"].rolling(20).std() + 1e-9))
    
    # 波动率特征
    df["volatility"] = df["ret1"].rolling(20).std()
    df["high_low_ratio"] = (df["high"] - df["low"]) / df["close"]
    
    # RSI类似指标
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + gain / (loss + 1e-9)))
    
    # 布林带特征
    bb_middle = df["close"].rolling(20).mean()
    bb_std = df["close"].rolling(20).std()
    df["bb_upper"] = bb_middle + 2 * bb_std
    df["bb_lower"] = bb_middle - 2 * bb_std
    df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-9)
    
    # 选择特征列
    feature_cols = [
        "close",  # 添加close作为特征
        "ret1", "ret5", "ret10", "ma5", "ma10", "ma20", "ema12", "ema26",
        "price_vs_ma5", "price_vs_ma20", "vol_ratio", "vol_z", 
        "volatility", "high_low_ratio", "rsi", "bb_position"
    ]
    
    # 添加滞后特征
    for i in range(1, min(lookback_days + 1, 6)):  # 添加1-5天的滞后价格特征
        df[f"close_lag_{i}"] = df["close"].shift(i)
        df[f"ret_lag_{i}"] = df["ret1"].shift(i)
        feature_cols.extend([f"close_lag_{i}", f"ret_lag_{i}"])
    
    return df, feature_cols

def neural_network_forecast(df: pd.DataFrame, ahead_days: int = 5):
    """
    使用神经网络进行股票价格预测
    """
    try:
        df_features, feature_cols = create_sequence_features(df)
        df_clean = df_features.dropna().copy()
        
        if len(df_clean) < 60:
            return None
        
        # 准备特征和目标变量
        X = df_clean[feature_cols].values
        y = df_clean["close"].values
        
        # 数据标准化
        scaler_X = StandardScaler()
        scaler_y = MinMaxScaler()
        
        X_scaled = scaler_X.fit_transform(X)
        y_scaled = scaler_y.fit_transform(y.reshape(-1, 1)).flatten()
        
        # 创建时间序列训练集（多步预测）
        sequence_length = 10
        X_seq, y_seq = [], []
        
        for i in range(sequence_length, len(X_scaled) - ahead_days):
            X_seq.append(X_scaled[i-sequence_length:i].flatten())
            # 预测未来1天的价格
            y_seq.append(y_scaled[i])
        
        X_seq = np.array(X_seq)
        y_seq = np.array(y_seq)
        
        if len(X_seq) < 30:
            return None
        
        # 训练神经网络
        model = MLPRegressor(
            hidden_layer_sizes=(100, 50, 25),
            max_iter=500,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
            alpha=0.001
        )
        
        model.fit(X_seq, y_seq)
        
        # 进行多步预测（改进版）
        predictions = []
        current_features = df_clean[feature_cols].iloc[-sequence_length:].copy()
        
        for step in range(ahead_days):
            # 准备输入特征
            X_pred = scaler_X.transform(current_features.values)
            pred_input = X_pred.flatten().reshape(1, -1)
            
            # 预测下一步
            pred_scaled = model.predict(pred_input)[0]
            pred_actual = scaler_y.inverse_transform([[pred_scaled]])[0, 0]
            
            # 添加一些随机性来模拟市场波动
            if step > 0:
                last_price = predictions[-1] if predictions else df_clean["close"].iloc[-1]
                volatility = df["close"].pct_change().dropna().std()
                noise_factor = min(volatility * 0.5, 0.02)  # 限制噪声不超过2%
                noise = np.random.normal(0, noise_factor * last_price)
                pred_actual += noise
            
            predictions.append(pred_actual)
            
            # 更新特征序列为下一步预测做准备
            if step < ahead_days - 1:
                # 创建新的特征行
                new_row = current_features.iloc[-1].copy()
                
                # 更新关键特征（基于预测价格）
                last_close = current_features["close"].iloc[-1]
                new_row["close"] = pred_actual
                new_row["ret1"] = (pred_actual - last_close) / last_close if last_close > 0 else 0
                
                # 更新移动平均相关特征（简化）
                if len(predictions) >= 5:
                    new_row["ma5"] = np.mean(predictions[-4:] + [pred_actual])
                if len(predictions) >= 10:
                    new_row["ma10"] = np.mean(predictions[-9:] + [pred_actual])
                
                # 滑动窗口：移除最旧的一行，添加新行
                current_features = pd.concat([current_features.iloc[1:], pd.DataFrame([new_row])], ignore_index=True)
        
        # 计算置信区间（基于历史预测误差）
        historical_errors = []
        for i in range(max(30, len(X_seq)//4), len(X_seq)):
            pred_val = model.predict(X_seq[i:i+1])[0]
            actual_val = y_seq[i]
            historical_errors.append(abs(scaler_y.inverse_transform([[pred_val]])[0, 0] - 
                                      scaler_y.inverse_transform([[actual_val]])[0, 0]))
        
        error_std = np.std(historical_errors) if historical_errors else np.std(y) * 0.02
        
        predictions = np.array(predictions)
        lower_bounds = predictions - 1.28 * error_std  # 80% 置信区间
        upper_bounds = predictions + 1.28 * error_std
        
        # 格式化返回结果
        result = {
            "method": "neural_network",
            "confidence": 0.85,
            "predictions": []
        }
        
        for i in range(len(predictions)):
            result["predictions"].append({
                "day": i + 1,
                "predicted_price": round(predictions[i], 2),
                "lower_bound": round(lower_bounds[i], 2),
                "upper_bound": round(upper_bounds[i], 2)
            })
        
        return result
        
    except Exception as e:
        print(f"Neural network forecast failed: {e}")
        return None

def enhanced_feature_regression_forecast(df: pd.DataFrame, ahead_days: int = 5):
    """
    增强的特征回归预测，考虑时间序列特性
    """
    try:
        df_features, feature_cols = create_sequence_features(df)
        df_clean = df_features.dropna().copy()
        
        if len(df_clean) < 80:
            return None
        
        X = df_clean[feature_cols].values
        y = df_clean["close"].values
        
        # 使用随机森林代替简单的Ridge回归
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        # 训练模型
        model.fit(X[:-ahead_days], y[:-ahead_days])
        
        # 计算历史预测误差
        pred_hist = model.predict(X[:-ahead_days])
        sigma = np.std(y[:-ahead_days] - pred_hist)
        
        # 进行多步预测
        predictions = []
        current_features = X[-1].copy()
        
        for step in range(ahead_days):
            pred_price = model.predict(current_features.reshape(1, -1))[0]
            predictions.append(pred_price)
            
            # 更新特征向量以进行下一步预测
            if step < ahead_days - 1:
                # 模拟特征更新（简化版本）
                # 更新价格相关特征
                prev_close = current_features[feature_cols.index("close_lag_1")] if "close_lag_1" in feature_cols else pred_price
                
                # 滚动更新滞后特征
                for i in range(5, 1, -1):
                    if f"close_lag_{i}" in feature_cols:
                        idx_curr = feature_cols.index(f"close_lag_{i}")
                        idx_prev = feature_cols.index(f"close_lag_{i-1}")
                        current_features[idx_curr] = current_features[idx_prev]
                
                if "close_lag_1" in feature_cols:
                    current_features[feature_cols.index("close_lag_1")] = pred_price
                
                # 更新收益率特征
                if "ret1" in feature_cols and prev_close > 0:
                    current_features[feature_cols.index("ret1")] = (pred_price - prev_close) / prev_close
        
        predictions = np.array(predictions)
        
        # 添加一些随机波动来模拟市场的不确定性
        trend_factor = np.linspace(1.0, 1.0 + np.random.normal(0, 0.01), ahead_days)
        predictions = predictions * trend_factor
        
        lower_bounds = predictions - 1.28 * sigma
        upper_bounds = predictions + 1.28 * sigma
        
        # 格式化返回结果
        result = {
            "method": "enhanced_regression",
            "confidence": 0.80,
            "predictions": []
        }
        
        for i in range(len(predictions)):
            result["predictions"].append({
                "day": i + 1,
                "predicted_price": round(predictions[i], 2),
                "lower_bound": round(lower_bounds[i], 2),
                "upper_bound": round(upper_bounds[i], 2)
            })
        
        return result
        
    except Exception as e:
        print(f"Enhanced regression forecast failed: {e}")
        return None

def predict_stock_price_enhanced(df: pd.DataFrame, symbol: str, ahead_days: int = 5):
    """
    增强的股票价格预测函数
    """
    try:
        if df.empty or len(df) < 30:
            return {
                "symbol": symbol,
                "error": "Insufficient data for prediction",
                "predictions": [],
                "method": "none"
            }
        
        # 首先尝试神经网络预测
        try:
            result = neural_network_forecast(df, ahead_days)
            if result is not None:
                return {
                    "symbol": symbol,
                    "predictions": result["predictions"],
                    "method": result["method"],
                    "confidence": result["confidence"]
                }
        except Exception as e:
            print(f"Neural network failed for {symbol}: {e}")
        
        # 如果神经网络失败，尝试增强的特征回归
        try:
            result = enhanced_feature_regression_forecast(df, ahead_days)
            if result is not None:
                return {
                    "symbol": symbol,
                    "predictions": result["predictions"],
                    "method": result["method"],
                    "confidence": result["confidence"]
                }
        except Exception as e:
            print(f"Enhanced regression failed for {symbol}: {e}")
        
        # 如果增强方法失败，使用SARIMAX
        try:
            series = df.sort_values("trade_date")["close"].astype(float)
            if len(series) >= 60:
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
                
                predictions = []
                for i in range(ahead_days):
                    predictions.append({
                        "day": i + 1,
                        "predicted_price": float(yhat[i]),
                        "lower_bound": float(conf[i, 0]),
                        "upper_bound": float(conf[i, 1])
                    })
                
                return {
                    "symbol": symbol,
                    "predictions": predictions,
                    "method": "sarimax",
                    "confidence": 0.7
                }
        except Exception as e:
            print(f"SARIMAX failed for {symbol}: {e}")
        
        # 最后的线性趋势预测（带波动）
        close_prices = df.sort_values("trade_date")["close"].astype(float)
        if len(close_prices) >= 5:
            recent_trend = (close_prices.iloc[-1] - close_prices.iloc[-5]) / 5
            last_price = close_prices.iloc[-1]
            volatility = close_prices.pct_change().std() * last_price
            
            predictions = []
            for i in range(ahead_days):
                # 添加一些随机波动
                random_factor = np.random.normal(1.0, 0.005)  # 0.5% 随机波动
                predicted_price = (last_price + (i + 1) * recent_trend) * random_factor
                
                # 基于历史波动率的置信区间
                lower_bound = predicted_price - 1.28 * volatility
                upper_bound = predicted_price + 1.28 * volatility
                
                predictions.append({
                    "day": i + 1,
                    "predicted_price": float(predicted_price),
                    "lower_bound": float(lower_bound),
                    "upper_bound": float(upper_bound)
                })
            
            return {
                "symbol": symbol,
                "predictions": predictions,
                "method": "enhanced_linear_trend",
                "confidence": 0.6
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

if __name__ == "__main__":
    # 测试代码
    print("Enhanced forecast model loaded successfully!")
