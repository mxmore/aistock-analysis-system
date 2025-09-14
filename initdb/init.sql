
CREATE TABLE IF NOT EXISTS watchlist (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(16) NOT NULL,
  name VARCHAR(64),
  sector VARCHAR(64),
  enabled BOOLEAN DEFAULT TRUE,
  UNIQUE(symbol)
);

CREATE TABLE IF NOT EXISTS prices_daily (
  id BIGSERIAL PRIMARY KEY,
  symbol VARCHAR(16) NOT NULL,
  trade_date DATE NOT NULL,
  open NUMERIC(18,4),
  high NUMERIC(18,4),
  low NUMERIC(18,4),
  close NUMERIC(18,4),
  pre_close NUMERIC(18,4),
  change NUMERIC(18,4),
  pct_chg NUMERIC(8,4),
  vol BIGINT,
  amount NUMERIC(20,2),
  UNIQUE(symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_prices_symbol_date ON prices_daily(symbol, trade_date);

CREATE TABLE IF NOT EXISTS forecasts (
  id BIGSERIAL PRIMARY KEY,
  symbol VARCHAR(16) NOT NULL,
  run_at TIMESTAMP NOT NULL,
  target_date DATE NOT NULL,
  model VARCHAR(32) NOT NULL,
  yhat NUMERIC(18,4),
  yhat_lower NUMERIC(18,4),
  yhat_upper NUMERIC(18,4)
);

CREATE TABLE IF NOT EXISTS signals (
  id BIGSERIAL PRIMARY KEY,
  symbol VARCHAR(16) NOT NULL,
  trade_date DATE NOT NULL,
  ma_short NUMERIC(18,4),
  ma_long NUMERIC(18,4),
  rsi NUMERIC(8,4),
  macd NUMERIC(18,4),
  signal_score NUMERIC(8,4),
  action VARCHAR(16)
);

-- 任务表
CREATE TABLE IF NOT EXISTS tasks (
  id BIGSERIAL PRIMARY KEY,
  task_type VARCHAR(32) NOT NULL,
  symbol VARCHAR(16) NOT NULL,
  status VARCHAR(16) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  error_message TEXT,
  priority INTEGER DEFAULT 5,
  task_metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_task_status_priority ON tasks(status, priority);
CREATE INDEX IF NOT EXISTS idx_task_symbol_type ON tasks(symbol, task_type);

-- 报告表
CREATE TABLE IF NOT EXISTS reports (
  id BIGSERIAL PRIMARY KEY,
  symbol VARCHAR(16) NOT NULL,
  version INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_latest BOOLEAN DEFAULT TRUE,
  latest_price_data TEXT,
  signal_data TEXT,
  forecast_data TEXT,
  analysis_summary TEXT,
  data_quality_score NUMERIC(4,2),
  prediction_confidence NUMERIC(5,3)
);

CREATE INDEX IF NOT EXISTS idx_report_symbol_latest ON reports(symbol, is_latest);
CREATE INDEX IF NOT EXISTS idx_report_symbol_version ON reports(symbol, version);

INSERT INTO watchlist(symbol, name, sector) VALUES
('600519.SH','贵州茅台','白酒'),
('300750.SZ','宁德时代','新能源'),
('601318.SH','中国平安','金融')
ON CONFLICT(symbol) DO NOTHING;
