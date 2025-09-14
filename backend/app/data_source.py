
import os
import pandas as pd
from datetime import datetime, timedelta
from dateutil.tz import gettz

DATA_SOURCE = os.getenv("DATA_SOURCE", "akshare").lower()
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")

def normalize_symbol(symbol: str) -> str:
    s = symbol.upper().strip()
    if s.endswith(".SH") or s.endswith(".SZ"):
        return s
    if s.startswith("6"):
        return f"{s}.SH"
    return f"{s}.SZ"

def fetch_daily_akshare(symbol: str, start_date: str = None) -> pd.DataFrame:
    import akshare as ak
    sym = normalize_symbol(symbol)
    base = sym.replace(".SH", "").replace(".SZ", "")
    df = ak.stock_zh_a_hist(symbol=base, period="daily", start_date=start_date, adjust="qfq")
    df = df.rename(columns={
        "日期": "trade_date", "开盘": "open", "收盘": "close", "最高": "high",
        "最低": "low", "成交量": "vol", "成交额": "amount", "涨跌幅": "pct_chg"
    })
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    df["pct_chg"] = pd.to_numeric(df["pct_chg"], errors="coerce")
    df["vol"] = pd.to_numeric(df["vol"], errors="coerce").astype("Int64")
    for col in ["open", "close", "high", "low", "amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["symbol"] = sym
    return df[["symbol", "trade_date", "open", "high", "low", "close", "pct_chg", "vol", "amount"]].dropna(subset=["close"])

def fetch_daily_tushare(symbol: str, start_date: str = None) -> pd.DataFrame:
    import tushare as ts
    if not TUSHARE_TOKEN:
        raise RuntimeError("TUSHARE_TOKEN must be set to use Tushare")
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    sym = normalize_symbol(symbol)
    ts_code = sym
    if start_date is None:
        dt = datetime.now(gettz("Asia/Taipei")) - timedelta(days=365*3)
        start_date = dt.strftime("%Y%m%d")
    df = pro.daily(ts_code=ts_code, start_date=start_date)
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    df = df.rename(columns={"amount": "amount_x"})
    df["amount"] = df["amount_x"] * 1000.0
    out = df.rename(columns={"vol": "vol_x"})
    out["vol"] = out["vol_x"].astype("Int64")
    out["symbol"] = sym
    return out[["symbol", "trade_date", "open", "high", "low", "close", "pct_chg", "vol", "amount"]].dropna(subset=["close"])

def fetch_daily(symbol: str, start_date: str | None = None) -> pd.DataFrame:
    if DATA_SOURCE == "tushare" and TUSHARE_TOKEN:
        return fetch_daily_tushare(symbol, start_date)
    return fetch_daily_akshare(symbol, start_date)

def search_stocks(query: str):
    """搜索股票，返回匹配的股票列表"""
    import akshare as ak
    try:
        # 使用akshare搜索股票
        df = ak.stock_info_a_code_name()
        
        # 过滤匹配的股票
        mask = (
            df['code'].str.contains(query, case=False, na=False) |
            df['name'].str.contains(query, case=False, na=False)
        )
        results = df[mask].head(20)  # 限制返回20个结果
        
        # 转换为字典列表
        stocks = []
        for _, row in results.iterrows():
            stocks.append({
                'symbol': normalize_symbol(row['code']),
                'name': row['name'],
                'code': row['code']
            })
        
        return stocks
    except Exception as e:
        print(f"Error searching stocks: {e}")
        return []

def get_stock_info(symbol: str):
    """获取股票基本信息"""
    import akshare as ak
    try:
        sym = normalize_symbol(symbol)
        base = sym.replace(".SH", "").replace(".SZ", "")
        
        # 获取股票信息
        df = ak.stock_info_a_code_name()
        stock_info = df[df['code'] == base]
        
        if stock_info.empty:
            return None
            
        row = stock_info.iloc[0]
        return {
            'symbol': sym,
            'name': row['name'],
            'code': row['code']
        }
    except Exception as e:
        print(f"Error getting stock info: {e}")
        return None

def get_realtime_stock(symbol: str):
    """获取股票实时数据"""
    import akshare as ak
    try:
        sym = normalize_symbol(symbol)
        base = sym.replace(".SH", "").replace(".SZ", "")
        
        # 获取实时数据
        df = ak.stock_zh_a_spot_em()
        stock_data = df[df['代码'] == base]
        
        if stock_data.empty:
            return None
            
        row = stock_data.iloc[0]
        return {
            'symbol': sym,
            'name': row['名称'],
            'price': float(row['最新价']),
            'change': float(row['涨跌额']),
            'pct_change': float(row['涨跌幅']),
            'volume': int(row['成交量']),
            'amount': float(row['成交额'])
        }
    except Exception as e:
        print(f"Error getting realtime stock data: {e}")
        return None
