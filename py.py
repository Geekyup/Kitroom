"""
Ставит process_kit(kit_id) заново в очередь arq.

Использование:
    pip install arq
    python reenqueue_kit.py "<REDIS_URL>" 3

REDIS_URL бери из Railway -> Redis service -> Connect -> публичный URL
(вида redis://default:PASSWORD@HOST.proxy.rlwy.net:PORT).
"""
import asyncio
import sys

from arq import create_pool
from arq.connections import RedisSettings


async def main(redis_url: str, kit_id: int) -> None:
    redis = await create_pool(RedisSettings.from_dsn(redis_url))
    job = await redis.enqueue_job("process_kit", kit_id)
    print(f"Поставлено в очередь: job_id={job.job_id}, kit_id={kit_id}")
    await redis.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reenqueue_kit.py <REDIS_URL> <kit_id>")
        sys.exit(1)

    redis_url = sys.argv[1]
    kit_id = int(sys.argv[2])
    asyncio.run(main(redis_url, kit_id))