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


@dataclass
class StockSignal:
    """股票信号"""
    symbol: str
    name: str
    score: int
    signals: List[str]
    price: float
    change_pct: float
    timestamp: str
    is_new: bool = True  # 是否是新发现的信号


class IncrementalTracker:
    """增量追踪器 - 记录已推送的信号"""

    def __init__(self, cache_file: str = 'data/sent_signals.json'):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.sent_signals: Dict[str, dict] = self._load()

    def _load(self) -> Dict[str, dict]:
        """加载已推送记录"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save(self):
        """保存已推送记录"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.sent_signals, f, ensure_ascii=False, indent=2)

    def _make_key(self, symbol: str, signal_type: str) -> str:
        """生成信号唯一键"""
        return f"{symbol}_{signal_type}"

    def was_recently_sent(self, symbol: str, signal_type: str) -> bool:
        """检查是否最近已推送"""
        key = self._make_key(symbol, signal_type)
        if key not in self.sent_signals:
            return False

        last_sent = datetime.fromisoformat(self.sent_signals[key]['timestamp'])
        elapsed = (datetime.now() - last_sent).total_seconds() / 60

        return elapsed < Config.SIGNAL_COOLDOWN

    def mark_sent(self, symbol: str, signal_type: str, score: int):
        """标记已推送"""
        key = self._make_key(symbol, signal_type)
        self.sent_signals[key] = {
            'timestamp': datetime.now().isoformat(),
            'score': score
        }
        self._save()

    def cleanup_old(self, hours: int = 24):
        """清理过期记录"""
        cutoff = datetime.now().timestamp() - hours * 3600
        self.sent_signals = {
            k: v for k, v in self.sent_signals.items()
            if datetime.fromisoformat(v['timestamp']).timestamp() > cutoff
        }
        self._save()


class RealtimeScanner:
    """实时扫描器 - 主动出击"""

    def __init__(self):
        self.tracker = IncrementalTracker()
        self.last_scan_file = Path('data/last_scan.json')

    def is_trading_time(self) -> bool:
        """检查是否在交易时间"""
        now = datetime.now()
        current_time = now.time()

        # 周末休市
        if now.weekday() >= 5:
            return False

        # 检查交易时段
        is_morning = Config.MORNING_START <= current_time <= Config.MORNING_END
        is_afternoon = Config.AFTERNOON_START <= current_time <= Config.AFTERNOON_END

        return is_morning or is_afternoon

    def scan_and_notify(self, candidates: List[str]) -> List[StockSignal]:
        """
        扫描并推送新信号

        Returns:
            List[StockSignal]: 新发现的信号列表
        """
        if not self.is_trading_time():
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 非交易时间，跳过扫描")
            return []

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 盘中扫描开始...")

        new_signals = []
        for symbol in candidates:
            signals = self._check_stock(symbol)

            for signal in signals:
                if not signal.is_new:
                    continue

                # 检查冷却期
                if self.tracker.was_recently_sent(signal.symbol, signal.signals[0]):
                    print(f"  {signal.symbol} {signal.name} - 冷却中，跳过")
                    continue

                new_signals.append(signal)

        # 推送新信号
        if new_signals:
            self._push_notifications(new_signals)
            for signal in new_signals:
                self.tracker.mark_sent(signal.symbol, signal.signals[0], signal.score)

        return new_signals

    def _check_stock(self, symbol: str) -> List[StockSignal]:
        """
        检查单只股票 - 这里需要接入你的扫描逻辑

        TODO: 接入 scanner_sina.py 的扫描逻辑
        """
        # 示例返回值
        return []

    def _push_notifications(self, signals: List[StockSignal]):
        """推送信号到微信"""
        if not Config.SCKEY:
            print("未配置SCKEY，跳过推送")
            return

        for signal in signals:
            self._send_wechat(signal)

    def _send_wechat(self, signal: StockSignal):
        """发送微信推送"""
        import requests

        # 构建消息
        title = f"【盘中信号】{signal.name}"

        content = f"""
<strong>代码</strong>：{signal.symbol}
<strong>现价</strong>：¥{signal.price:.2f}
<strong>涨幅</strong>：{signal.change_pct:+.2f}%
<strong>评分</strong>：{signal.score}/100
<strong>信号</strong>：{" | ".join(signal.signals)}
<strong>时间</strong>：{signal.timestamp}
        """

        url = f'https://sctapi.ftqq.com/{Config.SCKEY}.send'
        data = {
            'title': title,
            'desp': content
        }

        try:
            r = requests.post(url, data=data, timeout=10)
            if r.status_code == 200:
                print(f"  推送成功：{signal.name}")
            else:
                print(f"  推送失败：{signal.name}")
        except Exception as e:
            print(f"  推送异常：{e}")


def run_realtime_monitor():
    """运行实时监控主循环"""
    print("=" * 50)
    print("股坛狙击手 - 盘中实时监控模式")
    print(f"扫描间隔：{Config.SCAN_INTERVAL}分钟")
    print(f"交易时段：9:30-11:30 / 13:00-14:55")
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
                    print(f"\n本次发现 {len(signals)} 个新信号")
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
            print("\n监控已停止")
            break
        except Exception as e:
            print(f"扫描异常：{e}")

        time.sleep(Config.SCAN_INTERVAL * 60)


if __name__ == '__main__':
    run_realtime_monitor()
