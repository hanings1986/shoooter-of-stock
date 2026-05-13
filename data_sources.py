"""
股票侦察兵 - 多数据源配置
有VPN时可用的数据源列表

使用方式:
  from data_sources import get_data_manager
  dm = get_data_manager(use_vpn=True)
  dm.get_realtime('000001')
"""

import os
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class DataSource(Enum):
    """可用数据源"""
    # 国内源
    TENCENT = "tencent"      # 腾讯财经（主力，稳定）
    SINA = "sina"            # 新浪财经（K线数据）
    EAST_MONEY = "east_money"  # 东方财富（全面，但限流）
    AKSHARE = "akshare"      # AKShare封装（自动降级）
    
    # 国际源（VPN可用）
    YAHOO = "yahoo"          # Yahoo Finance（免费，美股为主）
    FINNHUB = "finnhub"      # Finnhub（免费，需API Key）
    ALPHA_VANTAGE = "alpha"   # Alpha Vantage（免费，需API Key）
    
    # 备用/降级
    CACHE = "cache"          # 本地缓存
    MOCK = "mock"            # 测试数据


@dataclass
class DataSourceConfig:
    """数据源配置"""
    name: str
    priority: int           # 优先级（数字越小越高）
    vpn_required: bool      # 是否需要VPN
    rate_limit: str         # 限流说明
    supports_realtime: bool # 支持实时行情
    supports_history: bool  # 支持历史K线
    supports_fundamentals: bool  # 支持基本面数据
    api_key_needed: bool    # 是否需要API Key
    api_key_env: str        # API Key环境变量名
    cost: str               # 费用


# 数据源配置表
DATA_SOURCES: Dict[DataSource, DataSourceConfig] = {
    # ===== 国内源（主力）=====
    DataSource.TENCENT: DataSourceConfig(
        name="腾讯财经",
        priority=1,
        vpn_required=False,
        rate_limit="宽松",
        supports_realtime=True,
        supports_history=False,
        supports_fundamentals=False,
        api_key_needed=False,
        api_key_env="",
        cost="免费"
    ),
    
    DataSource.SINA: DataSourceConfig(
        name="新浪财经",
        priority=2,
        vpn_required=False,
        rate_limit="中等（>100次/小时可能限流）",
        supports_realtime=True,
        supports_history=True,
        supports_fundamentals=False,
        api_key_needed=False,
        api_key_env="",
        cost="免费"
    ),
    
    DataSource.EAST_MONEY: DataSourceConfig(
        name="东方财富",
        priority=3,
        vpn_required=False,
        rate_limit="严格（大量请求会IP封禁）",
        supports_realtime=True,
        supports_history=True,
        supports_fundamentals=True,
        api_key_needed=False,
        api_key_env="",
        cost="免费"
    ),
    
    DataSource.AKSHARE: DataSourceConfig(
        name="AKShare",
        priority=4,
        vpn_required=False,
        rate_limit="依赖底层源",
        supports_realtime=True,
        supports_history=True,
        supports_fundamentals=True,
        api_key_needed=False,
        api_key_env="",
        cost="免费"
    ),
    
    # ===== 国际源（VPN可用）=====
    DataSource.YAHOO: DataSourceConfig(
        name="Yahoo Finance",
        priority=5,
        vpn_required=True,
        rate_limit="宽松（但A股数据有限）",
        supports_realtime=True,
        supports_history=True,
        supports_fundamentals=False,
        api_key_needed=False,
        api_key_env="",
        cost="免费"
    ),
    
    DataSource.FINNHUB: DataSourceConfig(
        name="Finnhub",
        priority=6,
        vpn_required=True,
        rate_limit="60次/分钟（免费层）",
        supports_realtime=True,
        supports_history=True,
        supports_fundamentals=True,
        api_key_needed=True,
        api_key_env="FINNHUB_API_KEY",
        cost="免费（每日有限额）"
    ),
    
    DataSource.ALPHA_VANTAGE: DataSourceConfig(
        name="Alpha Vantage",
        priority=7,
        vpn_required=True,
        rate_limit="25次/天（免费层）",
        supports_realtime=False,
        supports_history=True,
        supports_fundamentals=True,
        api_key_needed=True,
        api_key_env="ALPHA_VANTAGE_API_KEY",
        cost="免费（每日25次）"
    ),
}


class DataManager:
    """数据管理器 - 自动选择最优数据源"""
    
    def __init__(self, use_vpn: bool = False, preferred_sources: List[DataSource] = None):
        self.use_vpn = use_vpn
        self.cache = {}
        
        # 按优先级排序可用数据源
        self.available_sources = self._get_available_sources(preferred_sources)
        
        print(f"数据源初始化完成")
        print(f"   VPN模式: {'开启' if use_vpn else '关闭'}")
        print(f"   可用数据源: {[ds.value for ds in self.available_sources]}")
    
    def _get_available_sources(self, preferred: List[DataSource] = None) -> List[DataSource]:
        """获取可用数据源列表"""
        sources = []
        
        for ds, config in DATA_SOURCES.items():
            # 检查是否需要VPN
            if config.vpn_required and not self.use_vpn:
                continue
            # 检查是否需要API Key
            if config.api_key_needed:
                api_key = os.environ.get(config.api_key_env, "")
                if not api_key:
                    continue
            sources.append(ds)
        
        # 如果有偏好，按偏好排序
        if preferred:
            sources = sorted(sources, key=lambda x: preferred.index(x) if x in preferred else 999)
        else:
            # 否则按默认优先级
            sources.sort(key=lambda x: DATA_SOURCES[x].priority)
        
        return sources
    
    def get_realtime(self, symbol: str) -> Optional[Dict]:
        """获取实时行情"""
        for source in self.available_sources:
            try:
                data = self._fetch_realtime(symbol, source)
                if data:
                    data['_source'] = source.value
                    return data
            except Exception as e:
                print(f"  [{source.value}] 获取失败: {e}")
                continue
        return None
    
    def get_history(self, symbol: str, days: int = 90) -> Optional[List[Dict]]:
        """获取历史K线"""
        for source in self.available_sources:
            try:
                data = self._fetch_history(symbol, source, days)
                if data:
                    return data
            except Exception as e:
                print(f"  [{source.value}] 获取失败: {e}")
                continue
        return None
    
    def _fetch_realtime(self, symbol: str, source: DataSource) -> Optional[Dict]:
        """从指定源获取实时数据"""
        if source == DataSource.TENCENT:
            return self._tencent_realtime(symbol)
        elif source == DataSource.SINA:
            return self._sina_realtime(symbol)
        elif source == DataSource.FINNHUB:
            return self._finnhub_realtime(symbol)
        elif source == DataSource.YAHOO:
            return self._yahoo_realtime(symbol)
        return None
    
    def _fetch_history(self, symbol: str, source: DataSource, days: int) -> Optional[List[Dict]]:
        """从指定源获取历史数据"""
        if source == DataSource.SINA:
            return self._sina_history(symbol, days)
        elif source == DataSource.YAHOO:
            return self._yahoo_history(symbol, days)
        elif source == DataSource.FINNHUB:
            return self._finnhub_history(symbol, days)
        return None
    
    # ===== 具体实现 =====
    
    def _tencent_realtime(self, symbol: str) -> Optional[Dict]:
        """腾讯财经实时行情"""
        try:
            import urllib.request
            
            # 转换代码格式
            prefix = 'sh' if symbol.startswith(('6', '5')) else 'sz'
            url = f"http://qt.gtimg.cn/q={prefix}{symbol}"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=5)
            content = resp.read().decode('gbk')
            
            if '=""' in content:
                return None
            
            parts = content.split('"')[1].split('~')
            if len(parts) < 40:
                return None
            
            return {
                'name': parts[1],
                'code': symbol,
                'price': float(parts[3]),
                'yd_close': float(parts[4]),
                'open': float(parts[5]),
                'volume': float(parts[6]),
                'b1': float(parts[9]),
                's1': float(parts[19]),
                'pct': (float(parts[3]) - float(parts[4])) / float(parts[4]) * 100 if float(parts[4]) > 0 else 0,
            }
        except:
            return None
    
    def _sina_realtime(self, symbol: str) -> Optional[Dict]:
        """新浪财经实时行情"""
        try:
            import urllib.request
            
            prefix = 'sh' if symbol.startswith('6') else 'sz'
            url = f"http://hq.sinajs.cn/list={prefix}{symbol}"
            
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'http://finance.sina.com.cn'
            })
            resp = urllib.request.urlopen(req, timeout=5)
            content = resp.read().decode('gbk')
            
            if '""' in content:
                return None
            
            parts = content.split('"')[1].split(',')
            if len(parts) < 10:
                return None
            
            return {
                'name': parts[0],
                'code': symbol,
                'price': float(parts[3]),
                'yd_close': float(parts[2]),
                'pct': (float(parts[3]) - float(parts[2])) / float(parts[2]) * 100 if float(parts[2]) > 0 else 0,
            }
        except:
            return None
    
    def _sina_history(self, symbol: str, days: int = 90) -> Optional[List[Dict]]:
        """新浪财经历史K线"""
        try:
            import urllib.request
            import json
            
            prefix = 'sh' if symbol.startswith('6') else 'sz'
            url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={prefix}{symbol}&scale=240&ma=no&datalen={days}"
            
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'http://finance.sina.com.cn/stock/',
            })
            resp = urllib.request.urlopen(req, timeout=10)
            content = resp.read().decode('gbk')
            
            if not content or content == 'null':
                return None
            
            records = json.loads(content)
            if not records:
                return None
            
            result = []
            for r in records:
                result.append({
                    'date': r.get('day', ''),
                    'open': float(r.get('open', 0)),
                    'high': float(r.get('high', 0)),
                    'low': float(r.get('low', 0)),
                    'close': float(r.get('close', 0)),
                    'volume': float(r.get('volume', 0)),
                })
            
            return result
        except:
            return None
    
    def _yahoo_realtime(self, symbol: str) -> Optional[Dict]:
        """Yahoo Finance 实时行情（A股需特殊格式）"""
        try:
            import urllib.request
            import json
            
            # Yahoo Finance A股代码格式
            if symbol.startswith('6'):
                yahoo_symbol = f"{symbol}.SS"  # 上海
            else:
                yahoo_symbol = f"{symbol}.SZ"  # 深圳
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=1d&range=1d"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10)
            content = resp.read().decode('utf-8')
            data = json.loads(content)
            
            result = data['chart']['result'][0]
            meta = result['meta']
            
            return {
                'name': meta.get('symbol', ''),
                'code': symbol,
                'price': meta.get('regularMarketPrice', 0),
                'yd_close': meta.get('previousClose', 0),
                'pct': meta.get('regularMarketChangePercent', 0),
            }
        except:
            return None
    
    def _yahoo_history(self, symbol: str, days: int = 90) -> Optional[List[Dict]]:
        """Yahoo Finance 历史数据"""
        try:
            import urllib.request
            import json
            from datetime import datetime, timedelta
            
            if symbol.startswith('6'):
                yahoo_symbol = f"{symbol}.SS"
            else:
                yahoo_symbol = f"{symbol}.SZ"
            
            end = int(datetime.now().timestamp())
            start = int((datetime.now() - timedelta(days=days+30)).timestamp())
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=1d&period1={start}&period2={end}"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10)
            content = resp.read().decode('utf-8')
            data = json.loads(content)
            
            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            quotes = result['indicators']['quote'][0]
            
            records = []
            for i, ts in enumerate(timestamps):
                records.append({
                    'date': datetime.fromtimestamp(ts).strftime('%Y-%m-%d'),
                    'open': quotes['open'][i],
                    'high': quotes['high'][i],
                    'low': quotes['low'][i],
                    'close': quotes['close'][i],
                    'volume': quotes['volume'][i],
                })
            
            return records
        except:
            return None
    
    def _finnhub_realtime(self, symbol: str) -> Optional[Dict]:
        """Finnhub 实时行情"""
        try:
            import urllib.request
            import json
            
            api_key = os.environ.get('FINNHUB_API_KEY', '')
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
            
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=5)
            content = resp.read().decode('utf-8')
            data = json.loads(content)
            
            return {
                'code': symbol,
                'price': data.get('c', 0),
                'yd_close': data.get('pc', 0),
                'pct': (data.get('c', 0) - data.get('pc', 0)) / data.get('pc', 1) * 100,
            }
        except:
            return None
    
    def _finnhub_history(self, symbol: str, days: int = 90) -> Optional[List[Dict]]:
        """Finnhub 历史K线"""
        try:
            import urllib.request
            import json
            from datetime import datetime, timedelta
            
            api_key = os.environ.get('FINNHUB_API_KEY', '')
            end = int(datetime.now().timestamp())
            start = int((datetime.now() - timedelta(days=days+30)).timestamp())
            
            url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution=D&from={start}&to={end}&token={api_key}"
            
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=10)
            content = resp.read().decode('utf-8')
            data = json.loads(content)
            
            if data.get('s') != 'ok':
                return None
            
            timestamps = data.get('t', [])
            opens = data.get('o', [])
            highs = data.get('h', [])
            lows = data.get('l', [])
            closes = data.get('c', [])
            volumes = data.get('v', [])
            
            records = []
            for i in range(len(timestamps)):
                records.append({
                    'date': datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d'),
                    'open': opens[i],
                    'high': highs[i],
                    'low': lows[i],
                    'close': closes[i],
                    'volume': volumes[i],
                })
            
            return records
        except:
            return None


def get_data_manager(use_vpn: bool = False) -> DataManager:
    """获取数据管理器实例"""
    return DataManager(use_vpn=use_vpn)


# ===== 快速测试 =====
if __name__ == "__main__":
    print("=" * 50)
    print("数据源测试")
    print("=" * 50)
    
    # 检测VPN
    use_vpn = os.environ.get('VPN_ENABLED', 'false').lower() == 'true'
    
    dm = get_data_manager(use_vpn=use_vpn)
    
    # 测试获取数据
    test_codes = ['000001', '000002', '600519']  # 平安银行、万科A、贵州茅台
    
    print("\n实时行情测试:")
    for code in test_codes:
        data = dm.get_realtime(code)
        if data:
            print(f"  {code}: {data.get('name', '')} {data.get('price', 0)} ({data.get('pct', 0):+.2f}%) [{data.get('_source', '')}]")
        else:
            print(f"  {code}: 获取失败")
    
    print("\n历史K线测试 (000001):")
    hist = dm.get_history('000001', 5)
    if hist:
        print(f"  获取成功: {len(hist)}条")
        for h in hist[-3:]:
            print(f"    {h.get('date')}: close={h.get('close')}")
    else:
        print("  获取失败")
