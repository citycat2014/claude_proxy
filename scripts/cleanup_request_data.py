"""
清理存量请求数据，减少存储空间。

提供多种清理策略：
1. 清理 request_body（最大节省，约 910MB）
2. 清理 messages_json（约 788MB）
3. 保留统计数据，删除原始内容

WARNING: 此操作会删除原始数据，仅保留统计摘要！
建议先备份数据库！

Run: python scripts/cleanup_request_data.py [--strategy=full|partial|stats-only]
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from datetime import datetime, timedelta
from sqlalchemy import func, text
from storage.database import Database


def get_size_info(db):
    """Get current database size info."""
    with db.db_session() as session:
        from storage.models import Request

        result = session.query(
            func.count(Request.id).label('count'),
            func.sum(func.length(Request.request_body)).label('request_body'),
            func.sum(func.length(Request.messages_json)).label('messages_json'),
            func.sum(func.length(Request.response_text)).label('response_text'),
            func.sum(func.length(Request.response_thinking)).label('response_thinking'),
        ).first()

        return {
            'count': result.count or 0,
            'request_body_mb': (result.request_body or 0) / 1024 / 1024,
            'messages_json_mb': (result.messages_json or 0) / 1024 / 1024,
            'response_text_mb': (result.response_text or 0) / 1024 / 1024,
            'response_thinking_mb': (result.response_thinking or 0) / 1024 / 1024,
            'total_mb': sum([
                (result.request_body or 0),
                (result.messages_json or 0),
                (result.response_text or 0),
                (result.response_thinking or 0),
            ]) / 1024 / 1024
        }


def cleanup_strategy_full(db):
    """完整清理：删除所有大字段内容，仅保留统计摘要。"""
    print("\n执行完整清理...")
    print("这将清空 request_body, messages_json, response_text, response_thinking")

    with db.db_session() as session:
        from storage.models import Request

        # Update in batches
        batch_size = 100
        offset = 0
        total = session.query(Request).count()
        processed = 0

        while offset < total:
            requests = session.query(Request).order_by(Request.id).offset(offset).limit(batch_size).all()

            for req in requests:
                req.request_body = ""
                req.messages_json = ""
                req.response_text = ""
                req.response_thinking = ""

            session.commit()
            processed += len(requests)
            print(f"  已处理 {processed}/{total} 条记录")
            offset += batch_size

    print("✓ 完整清理完成")


def cleanup_strategy_partial(db):
    """部分清理：只删除 request_body（最大收益）。"""
    print("\n执行部分清理...")
    print("这将清空 request_body，保留 messages_json 用于查看消息")

    with db.db_session() as session:
        from storage.models import Request

        batch_size = 100
        offset = 0
        total = session.query(Request).count()
        processed = 0

        while offset < total:
            requests = session.query(Request).order_by(Request.id).offset(offset).limit(batch_size).all()

            for req in requests:
                req.request_body = ""

            session.commit()
            processed += len(requests)
            print(f"  已处理 {processed}/{total} 条记录")
            offset += batch_size

    print("✓ 部分清理完成")


def cleanup_strategy_old_data(db, days=7):
    """清理旧数据：只保留最近 N 天的完整数据，旧数据只保留统计。"""
    print(f"\n执行旧数据清理（保留最近 {days} 天完整数据）...")

    cutoff = datetime.now() - timedelta(days=days)

    with db.db_session() as session:
        from storage.models import Request

        # Count old records
        old_count = session.query(Request).filter(Request.timestamp < cutoff).count()
        print(f"  发现 {old_count} 条旧记录将清理内容")

        # Update old records
        batch_size = 100
        offset = 0
        processed = 0

        while offset < old_count:
            requests = session.query(Request).filter(Request.timestamp < cutoff).order_by(Request.id).offset(offset).limit(batch_size).all()

            for req in requests:
                req.request_body = ""
                req.messages_json = ""
                req.response_text = ""
                req.response_thinking = ""

            session.commit()
            processed += len(requests)
            print(f"  已处理 {processed}/{old_count} 条旧记录")
            offset += batch_size

    print("✓ 旧数据清理完成")


def main():
    parser = argparse.ArgumentParser(description='清理请求数据以释放存储空间')
    parser.add_argument('--strategy', choices=['full', 'partial', 'old-only'], default='partial',
                        help='清理策略: full=清理所有内容, partial=只清理request_body, old-only=只清理旧数据')
    parser.add_argument('--days', type=int, default=7,
                        help='old-only策略下保留最近几天的完整数据')
    parser.add_argument('--dry-run', action='store_true',
                        help='只显示预估空间，不实际执行')

    args = parser.parse_args()

    db = Database()

    print("=" * 60)
    print("存量数据清理工具")
    print("=" * 60)

    # Show current size
    print("\n当前数据大小:")
    sizes = get_size_info(db)
    print(f"  请求总数: {sizes['count']}")
    print(f"  request_body: {sizes['request_body_mb']:.1f} MB")
    print(f"  messages_json: {sizes['messages_json_mb']:.1f} MB")
    print(f"  response_text: {sizes['response_text_mb']:.1f} MB")
    print(f"  response_thinking: {sizes['response_thinking_mb']:.1f} MB")
    print(f"  总计: {sizes['total_mb']:.1f} MB")

    if args.dry_run:
        print("\n[干运行模式] 不执行实际清理")
        return

    # Confirm
    print("\n" + "=" * 60)
    print("WARNING: 此操作将永久删除原始数据！")
    print("=" * 60)
    confirm = input(f"确认使用 {args.strategy} 策略清理数据? [yes/no]: ")

    if confirm.lower() != 'yes':
        print("已取消")
        return

    # Execute strategy
    if args.strategy == 'full':
        cleanup_strategy_full(db)
    elif args.strategy == 'partial':
        cleanup_strategy_partial(db)
    elif args.strategy == 'old-only':
        cleanup_strategy_old_data(db, args.days)

    # Show result
    print("\n清理后数据大小:")
    sizes = get_size_info(db)
    print(f"  请求总数: {sizes['count']}")
    print(f"  request_body: {sizes['request_body_mb']:.1f} MB")
    print(f"  messages_json: {sizes['messages_json_mb']:.1f} MB")
    print(f"  response_text: {sizes['response_text_mb']:.1f} MB")
    print(f"  response_thinking: {sizes['response_thinking_mb']:.1f} MB")
    print(f"  总计: {sizes['total_mb']:.1f} MB")

    print("\n" + "=" * 60)
    print("清理完成！建议运行 VACUUM 回收空间:")
    print("  sqlite3 data/capture.db 'VACUUM;'")
    print("=" * 60)


if __name__ == "__main__":
    main()
