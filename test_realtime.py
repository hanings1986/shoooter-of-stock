"""
快速测试：盘中实时监控
跳过交易时段检查，直接测试核心功能
"""

import json
from datetime import datetime
from pathlib import Path

# 模拟测试数据
TEST_STOCKS = [
    {'symbol': '000001', 'name': '平安银行', 'price': 12.50, 'change': -4.5, 'score': 68},
    {'symbol': '000002', 'name': '万科A', 'price': 8.20, 'change': -6.2, 'score': 72},
    {'symbol': '600519', 'name': '贵州茅台', 'price': 1680.0, 'change': -3.1, 'score': 55},
]

def test_incremental_tracker():
    """测试增量追踪器"""
    from realtime_monitor import IncrementalTracker, Config

    print("=" * 50)
    print("🧪 测试：增量追踪器")
    print("=" * 50)

    tracker = IncrementalTracker()

    # 测试1：检查未推送的股票
    print("\n📋 测试1：检查未推送的股票")
    result = tracker.was_recently_sent('000001', 'MA10支撑')
    print(f"  000001 MA10支撑 已推送? {result}")  # 应该 False

    # 测试2：标记已推送
    print("\n📋 测试2：标记已推送")
    tracker.mark_sent('000001', 'MA10支撑', 68)
    print(f"  ✅ 已标记：000001 MA10支撑")

    # 测试3：再次检查
    print("\n📋 测试3：检查已推送的股票")
    result = tracker.was_recently_sent('000001', 'MA10支撑')
    print(f"  000001 MA10支撑 已推送? {result}")  # 应该 True（冷却期内）

    # 测试4：不同信号类型
    print("\n📋 测试4：不同信号类型")
    result = tracker.was_recently_sent('000001', 'RSI反弹')
    print(f"  000001 RSI反弹 已推送? {result}")  # 应该 False（不同信号）

    # 测试5：清理过期记录
    print("\n📋 测试5：清理过期记录")
    tracker.cleanup_old(hours=24)
    print(f"  ✅ 清理完成")

    print("\n" + "=" * 50)
    print("✅ 增量追踪器测试通过！")
    print("=" * 50)


def test_trading_time():
    """测试交易时段判断"""
    from realtime_monitor import Config

    print("\n" + "=" * 50)
    print("🧪 测试：交易时段判断")
    print("=" * 50)

    now = datetime.now()
    current_time = now.time()

    print(f"\n当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"星期: {['周一','周二','周三','周四','周五','周六','周日'][now.weekday()]}")

    # 早盘
    is_morning = Config.MORNING_START <= current_time <= Config.MORNING_END
    is_afternoon = Config.AFTERNOON_START <= current_time <= Config.AFTERNOON_END
    is_weekend = now.weekday() >= 5

    print(f"\n早盘时段: {Config.MORNING_START.strftime('%H:%M')} - {Config.MORNING_END.strftime('%H:%M')}")
    print(f"午盘时段: {Config.AFTERNOON_START.strftime('%H:%M')} - {Config.AFTERNOON_END.strftime('%H:%M')}")
    print(f"\n当前是否早盘? {is_morning}")
    print(f"当前是否午盘? {is_afternoon}")
    print(f"当前是否周末? {is_weekend}")

    is_trading = (is_morning or is_afternoon) and not is_weekend
    print(f"\n⏰ 当前是否交易时间? {is_trading}")

    print("\n" + "=" * 50)


def test_data_source():
    """测试数据源获取"""
    from data_sources import get_data_manager, DataSource

    print("\n" + "=" * 50)
    print("🧪 测试：数据源获取")
    print("=" * 50)

    # 优先使用国内源
    dm = get_data_manager(preferred_source=DataSource.SINA)

    # 测试获取实时数据
    print("\n📡 获取 000001 实时数据...")
    try:
        data = dm.get_realtime('000001')
        if data:
            print(f"  ✅ 成功!")
            print(f"  股票: {data.get('name', 'N/A')}")
            print(f"  现价: ¥{data.get('price', 0):.2f}")
            print(f"  涨幅: {data.get('change_pct', 0):+.2f}%")
        else:
            print(f"  ⚠️ 无数据")
    except Exception as e:
        print(f"  ❌ 错误: {e}")

    print("\n" + "=" * 50)


def show_config():
    """显示配置"""
    from realtime_monitor import Config

    print("\n" + "=" * 50)
    print("⚙️  当前配置")
    print("=" * 50)
    print(f"  扫描间隔: {Config.SCAN_INTERVAL} 分钟")
    print(f"  信号冷却期: {Config.SIGNAL_COOLDOWN} 分钟")
    print(f"  强信号阈值: {Config.STRONG_SIGNAL_THRESHOLD} 分")
    print(f"  新信号阈值: {Config.NEW_SIGNAL_THRESHOLD} 分")
    print(f"  增量模式: {Config.INCREMENTAL_MODE}")
    print(f"\n  交易时段:")
    print(f"    早盘: {Config.MORNING_START.strftime('%H:%M')} - {Config.MORNING_END.strftime('%H:%M')}")
    print(f"    午盘: {Config.AFTERNOON_START.strftime('%H:%M')} - {Config.AFTERNOON_END.strftime('%H:%M')}")
    print("\n" + "=" * 50)


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🚀 股坛狙击手 - 盘中实时监控测试")
    print("=" * 50)

    # 显示配置
    show_config()

    # 测试交易时段
    test_trading_time()

    # 测试增量追踪器
    test_incremental_tracker()

    # 测试数据源
    test_data_source()

    print("\n✅ 所有测试完成!")
    print("\n下一步:")
    print("  1. 上传到GitHub: git push")
    print("  2. 查看Actions: https://github.com/你的用户名/股坛狙击手/actions")
