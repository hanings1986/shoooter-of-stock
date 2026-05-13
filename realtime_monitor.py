"""
股坛狙击手 - 盘中实时监控系统
===============================
核心功能：盘中每5分钟扫描，发现新信号立即推送

主动出击 vs 被动等待:
- 被动模式：每天9:30收盘后扫描一次
- 主动模式：盘中每5分钟扫描，实时推送新信号
"""

import os
import json
import time
import hashlib
from datetime import datetime, time as dtime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
from pathlib import Path

# ============== 配置 ==============
class Config:
    """主动出击配置"""
    # 扫描频率（分钟）
    SCAN_INTERVAL = 5  # 每5分钟扫描一次

    # 交易时间段
    MORNING_START = dtime(9, 30)   # 早盘开始
    MORNING_END = dtime(11, 30)     # 早盘结束
    AFTERNOON_START = dtime(13, 0)  # 午盘开始
    AFTERNOON_END = dtime(14, 55)   # 午盘结束（收盘前5分钟）

    # 增量推送模式
    INCREMENTAL_MODE = True  # 只推送新信号，避免重复骚扰

    # 信号冷却期（分钟）- 同一股票推送后，多久内不再重复推送
    SIGNAL_COOLDOWN = 30

    # 推送阈值
    STRONG_SIGNAL_THRESHOLD = 60  # 强信号立即推送
    NEW_SIGNAL_THRESHOLD = 45      # 普通新信号累计推送

    # Server酱配置
    SCKEY = os.getenv('SCKEY', '')
    
    # GitHub Pages URL - 用于生成分析页面链接
    GITHUB_PAGES_URL = os.getenv('GITHUB_PAGES_URL', 'https://你的用户名.github.io/股坛狙击手')


@dataclass
class StockSignal:
    """股票信号"""
    symbol: str
    name: str
    price: float
    change_pct: float
    score: int
    signals: List[str]
    timestamp: str
    reason: str = ""


class SignalTracker:
    """增量推送追踪器"""
    
    def __init__(self, cache_file: str = "data/sent_signals.json"):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.sent_signals = self._load()
        
    def _load(self) -> Dict:
        """加载已推送记录"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"signals": {}, "last_cleanup": ""}
    
    def _save(self):
        """保存推送记录"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.sent_signals, f, ensure_ascii=False, indent=2)
    
    def is_sent_recently(self, symbol: str, signal_type: str) -> bool:
        """检查是否最近推送过"""
        key = f"{symbol}_{signal_type}"
        if key in self.sent_signals.get("signals", {}):
            last_sent = datetime.fromisoformat(self.sent_signals["signals"][key])
            minutes_since = (datetime.now() - last_sent).total_seconds() / 60
            return minutes_since < Config.SIGNAL_COOLDOWN
        return False
    
    def mark_sent(self, symbol: str, signal_type: str):
        """标记已推送"""
        key = f"{symbol}_{signal_type}"
        if "signals" not in self.sent_signals:
            self.sent_signals["signals"] = {}
        self.sent_signals["signals"][key] = datetime.now().isoformat()
        self._save()
    
    def cleanup_old(self):
        """清理过期记录"""
        cutoff = datetime.now().timestamp() - (24 * 60 * 60)  # 24小时前的记录
        cleaned = 0
        
        if "signals" in self.sent_signals:
            old_keys = []
            for key, timestamp in self.sent_signals["signals"].items():
                try:
                    ts = datetime.fromisoformat(timestamp).timestamp()
                    if ts < cutoff:
                        old_keys.append(key)
                except:
                    old_keys.append(key)
            
            for key in old_keys:
                del self.sent_signals["signals"][key]
                cleaned += 1
            
            if cleaned > 0:
                self._save()
                print(f"  🧹 清理了 {cleaned} 条过期记录")


class RealtimeScanner:
    """盘中实时扫描器"""
    
    def __init__(self):
        self.tracker = SignalTracker()
        self.push_count = 0
        
    def is_trading_time(self) -> bool:
        """检查是否在交易时段"""
        now = datetime.now()
        current_time = now.time()
        
        # 周末休市
        if now.weekday() >= 5:
            return False
        
        # 早盘
        if Config.MORNING_START <= current_time <= Config.MORNING_END:
            return True
        
        # 午盘
        if Config.AFTERNOON_START <= current_time <= Config.AFTERNOON_END:
            return True
        
        return False
    
    def should_push(self, signal: StockSignal) -> bool:
        """判断是否应该推送"""
        # 检查信号冷却
        for sig_type in signal.signals:
            if self.tracker.is_sent_recently(signal.symbol, sig_type):
                return False
        
        # 检查评分阈值
        if signal.score >= Config.STRONG_SIGNAL_THRESHOLD:
            return True
        
        return False
    
    def scan_and_notify(self, candidates: List[Dict]) -> List[StockSignal]:
        """扫描并通知"""
        new_signals = []
        
        for candidate in candidates:
            signal = self._analyze_stock(candidate)
            if signal and self.should_push(signal):
                new_signals.append(signal)
                # 标记已推送
                for sig_type in signal.signals:
                    self.tracker.mark_sent(signal.symbol, sig_type)
        
        if new_signals:
            self._push_notifications(new_signals)
            
        return new_signals
    
    def _analyze_stock(self, candidate: Dict) -> Optional[StockSignal]:
        """分析单只股票"""
        # TODO: 调用 scanner_sina.py 的分析逻辑
        # 示例返回值
        return None
    
    def _push_notifications(self, signals: List[StockSignal]):
        """推送信号到微信"""
        if not Config.SCKEY:
            print("⚠️ 未配置SCKEY，跳过推送")
            return

        for signal in signals:
            self._send_wechat(signal)

    def _send_wechat(self, signal: StockSignal):
        """发送微信推送"""
        import requests

        # 构建消息
        emoji = "🚀" if signal.score >= 70 else "📈"
        title = f"{emoji} 【盘中信号】{signal.name}"
        
        # 生成分析页面链接
        pure_code = signal.symbol.replace('sz', '').replace('sh', '')
        signals_param = ','.join(signal.signals) if signal.signals else ''
        analysis_url = f"{Config.GITHUB_PAGES_URL}/analysis.html?c={pure_code}&p={signal.score}&t={signal.timestamp}"
        if signals_param:
            analysis_url += f"&s={signals_param}"
        
        # 构建完整消息内容
        content = f"""<strong>📊 代码</strong>：{signal.symbol}
<strong>💰 现价</strong>：¥{signal.price:.2f}
<strong>📈 涨幅</strong>：{signal.change_pct:+.2f}%
<strong>⭐ 评分</strong>：{signal.score}/100
<strong>🎯 信号</strong>：{" | ".join(signal.signals)}
<strong>⏰ 时间</strong>：{signal.timestamp}

<hr/>

<a href="{analysis_url}">👉 点击查看详细分析</a>"""

        url = f'https://sctapi.ftqq.com/{Config.SCKEY}.send'
        data = {
            'title': title,
            'desp': content
        }

        try:
            r = requests.post(url, data=data, timeout=10)
            if r.status_code == 200:
                print(f"  ✅ 推送成功：{signal.name}")
                print(f"     📎 分析链接：{analysis_url}")
            else:
                print(f"  ❌ 推送失败：{signal.name}")
        except Exception as e:
            print(f"  ❌ 推送异常：{e}")


def run_realtime_monitor():
    """运行实时监控主循环"""
    print("=" * 50)
    print("🚀 股坛狙击手 - 盘中实时监控模式")
    print(f"📊 扫描间隔：{Config.SCAN_INTERVAL}分钟")
    print(f"⏰ 交易时段：9:30-11:30 / 13:00-14:55")
    print("=" * 50)

    scanner = RealtimeScanner()

    # 清理过期记录
    scanner.tracker.cleanup_old()

    while True:
        try:
            if scanner.is_trading_time():
                # TODO: 从候选池获取股票列表
                candidates = []  # scanner_sina.py.get_candidates()
                signals = scanner.scan_and_notify(candidates)

                if signals:
                    print(f"\n📈 本次发现 {len(signals)} 个新信号")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 本次扫描无新信号")
            else:
                now = datetime.now()
                current_time = now.time()

                # 计算下次扫描时间
                if now.weekday() >= 5:
                    next_scan = "周一开盘"
                elif current_time < Config.MORNING_START:
                    next_scan = f"{Config.MORNING_START.strftime('%H:%M')} 开盘"
                elif Config.MORNING_END < current_time < Config.AFTERNOON_START:
                    next_scan = f"{Config.AFTERNOON_START.strftime('%H:%M')} 午盘"
                else:
                    next_scan = "今日收盘"

                print(f"[{now.strftime('%H:%M:%S')}] 非交易时间，下次扫描：{next_scan}")

        except KeyboardInterrupt:
            print("\n👋 监控已停止")
            break
        except Exception as e:
            print(f"❌ 扫描异常：{e}")

        time.sleep(Config.SCAN_INTERVAL * 60)


if __name__ == '__main__':
    run_realtime_monitor()
