"""
Проверка доступности S3-совместимого хранилища (Railway Bucket / B2 / любой S3 API)
перед стартом приложения.

Запуск:
    python -m scripts.check_storage

Или как entrypoint-шаг в Docker перед uvicorn:
    python -m scripts.check_storage && uvicorn app.main:app ...

Что проверяет, по шагам, с понятными сообщениями об ошибке на каждом:
    1. Заполнены ли обязательные env-переменные вообще (не пустые/не дефолтные)
    2. Резолвится ли DNS эндпоинта
    3. Устанавливается ли TCP/TLS соединение
    4. Проходит ли реальный S3-запрос (list_objects / head_bucket) с текущими кредами
    5. Проходит ли полный цикл put_object -> get_object -> delete_object
       на маленьком тестовом объекте — это ловит проблемы с правами на запись,
       которые head_bucket не обнаружит.

Скрипт завершается с exit code 1 при любой ошибке, чтобы Docker healthcheck
или entrypoint-скрипт мог остановить запуск приложения вместо того, чтобы
получить необъяснимый Broken pipe посреди реального аплоада пользователя.
"""

import asyncio
import socket
import sys
import time
import uuid
from urllib.parse import urlparse

import aioboto3
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
)

from app.core.config import settings


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"{GREEN}[OK]{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"{RED}[FAIL]{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def check_env() -> bool:
    """Шаг 1: обязательные переменные заполнены и не выглядят как заглушки."""
    required = {
        "B2_ENDPOINT_URL": settings.B2_ENDPOINT_URL,
        "B2_KEY_ID": settings.B2_KEY_ID,
        "B2_APPLICATION_KEY": settings.B2_APPLICATION_KEY,
        "B2_BUCKET_NAME": settings.B2_BUCKET_NAME,
        "B2_REGION": settings.B2_REGION,
    }

    all_ok = True
    for name, value in required.items():
        if not value:
            fail(f"{name} пустая — переменная не проброшена в контейнер")
            all_ok = False
        elif len(value) < 4:
            fail(f"{name} подозрительно короткая ('{value}') — похоже на опечатку")
            all_ok = False
        else:
            masked = value if name in ("B2_ENDPOINT_URL", "B2_BUCKET_NAME", "B2_REGION") else f"{value[:6]}...{value[-4:]}"
            ok(f"{name} = {masked}")

    if not settings.B2_ENDPOINT_URL.startswith("https://") and required.get("B2_ENDPOINT_URL"):
        fail("B2_ENDPOINT_URL должен начинаться с https://")
        all_ok = False

    return all_ok


def check_dns() -> bool:
    """Шаг 2: резолвится ли хост эндпоинта."""
    if not settings.B2_ENDPOINT_URL:
        return False

    host = urlparse(settings.B2_ENDPOINT_URL).hostname
    if not host:
        fail(f"Не удалось распарсить хост из B2_ENDPOINT_URL='{settings.B2_ENDPOINT_URL}'")
        return False

    try:
        t0 = time.monotonic()
        addr = socket.gethostbyname(host)
        dt = time.monotonic() - t0
        ok(f"DNS резолвится: {host} -> {addr} ({dt*1000:.0f}ms)")
        return True
    except socket.gaierror as e:
        fail(f"DNS не резолвится для '{host}': {e}")
        fail("Проверь интернет из контейнера: docker compose exec api curl -v " + settings.B2_ENDPOINT_URL)
        return False


def check_tcp() -> bool:
    """Шаг 3: устанавливается ли голое TCP-соединение на нужный порт."""
    if not settings.B2_ENDPOINT_URL:
        return False

    parsed = urlparse(settings.B2_ENDPOINT_URL)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        t0 = time.monotonic()
        with socket.create_connection((host, port), timeout=10) as sock:
            dt = time.monotonic() - t0
            ok(f"TCP-соединение установлено: {host}:{port} ({dt*1000:.0f}ms)")
            return True
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        fail(f"Не удалось установить TCP-соединение с {host}:{port}: {e}")
        fail("Возможно блокирует фаервол/VPN, либо проблема с сетью Docker Desktop наружу")
        return False


async def check_s3_auth() -> bool:
    """Шаг 4: проходит ли реальный S3-запрос с текущими кредами (head_bucket)."""
    session = aioboto3.Session()
    client_kwargs = dict(
        endpoint_url=settings.B2_ENDPOINT_URL,
        aws_access_key_id=settings.B2_KEY_ID,
        aws_secret_access_key=settings.B2_APPLICATION_KEY,
        region_name=settings.B2_REGION,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=10,
            read_timeout=15,
            retries={"max_attempts": 1},
        ),
    )

    try:
        async with session.client("s3", **client_kwargs) as client:
            t0 = time.monotonic()
            await client.head_bucket(Bucket=settings.B2_BUCKET_NAME)
            dt = time.monotonic() - t0
            ok(f"head_bucket успешен, бакет '{settings.B2_BUCKET_NAME}' доступен ({dt*1000:.0f}ms)")
            return True
    except EndpointConnectionError as e:
        fail(f"Не удалось подключиться к эндпоинту при S3-запросе: {e}")
        return False
    except NoCredentialsError:
        fail("Креды не переданы клиенту (aws_access_key_id/secret пустые)")
        return False
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "Unknown")
        message = e.response.get("Error", {}).get("Message", str(e))
        if code in ("403", "AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"):
            fail(f"Ошибка авторизации ({code}): {message}")
            fail("Проверь B2_KEY_ID / B2_APPLICATION_KEY — похоже, ключи неверные или обрезаны")
        elif code in ("404", "NoSuchBucket"):
            fail(f"Бакет не найден ({code}): {message}")
            fail(f"Проверь B2_BUCKET_NAME — сейчас '{settings.B2_BUCKET_NAME}'")
        else:
            fail(f"S3 вернул ошибку ({code}): {message}")
        return False
    except Exception as e:
        fail(f"Неожиданная ошибка при head_bucket: {type(e).__name__}: {e}")
        return False


async def check_s3_write_cycle() -> bool:
    """
    Шаг 5: полный цикл put -> get -> delete на тестовом объекте.
    Ловит проблемы с правами на запись, которые head_bucket не видит
    (некоторые S3-провайдеры разрешают head_bucket, но режут put_object
    по IAM-политике конкретного ключа).
    """
    session = aioboto3.Session()
    client_kwargs = dict(
        endpoint_url=settings.B2_ENDPOINT_URL,
        aws_access_key_id=settings.B2_KEY_ID,
        aws_secret_access_key=settings.B2_APPLICATION_KEY,
        region_name=settings.B2_REGION,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=10,
            read_timeout=15,
            retries={"max_attempts": 1},
        ),
    )

    test_key = f"_healthcheck/{uuid.uuid4()}.txt"
    test_body = b"kitroom storage healthcheck"

    try:
        async with session.client("s3", **client_kwargs) as client:
            t0 = time.monotonic()
            await client.put_object(Bucket=settings.B2_BUCKET_NAME, Key=test_key, Body=test_body)
            ok(f"put_object успешен ({(time.monotonic()-t0)*1000:.0f}ms)")

            t0 = time.monotonic()
            resp = await client.get_object(Bucket=settings.B2_BUCKET_NAME, Key=test_key)
            data = await resp["Body"].read()
            if data != test_body:
                fail("Прочитанные данные не совпадают с записанными — возможна проблема консистентности")
                return False
            ok(f"get_object успешен, данные совпадают ({(time.monotonic()-t0)*1000:.0f}ms)")

            t0 = time.monotonic()
            await client.delete_object(Bucket=settings.B2_BUCKET_NAME, Key=test_key)
            ok(f"delete_object успешен ({(time.monotonic()-t0)*1000:.0f}ms)")

            return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "Unknown")
        message = e.response.get("Error", {}).get("Message", str(e))
        fail(f"Ошибка в цикле put/get/delete ({code}): {message}")
        if code in ("403", "AccessDenied"):
            fail("Ключ прошёл head_bucket, но не имеет прав на запись/чтение/удаление объектов")
        return False
    except Exception as e:
        fail(f"Неожиданная ошибка в цикле put/get/delete: {type(e).__name__}: {e}")
        return False


async def main() -> int:
    print("=== Проверка хранилища Kitroom ===\n")

    print("--- Шаг 1: переменные окружения ---")
    if not check_env():
        print(f"\n{RED}Проверка остановлена: не заполнены обязательные переменные.{RESET}")
        return 1
    print()

    print("--- Шаг 2: DNS ---")
    if not check_dns():
        print(f"\n{RED}Проверка остановлена: DNS не резолвится.{RESET}")
        return 1
    print()

    print("--- Шаг 3: TCP-соединение ---")
    if not check_tcp():
        print(f"\n{RED}Проверка остановлена: TCP-соединение не устанавливается.{RESET}")
        return 1
    print()

    print("--- Шаг 4: авторизация в S3 (head_bucket) ---")
    if not await check_s3_auth():
        print(f"\n{RED}Проверка остановлена: head_bucket не прошёл.{RESET}")
        return 1
    print()

    print("--- Шаг 5: цикл put/get/delete ---")
    if not await check_s3_write_cycle():
        print(f"\n{RED}Проверка остановлена: запись/чтение не работают.{RESET}")
        return 1
    print()

    print(f"{GREEN}=== Хранилище полностью работоспособно ==={RESET}")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)