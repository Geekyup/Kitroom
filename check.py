"""
Настройка CORS на S3-совместимом бакете (Railway Bucket) через boto3,
без установки awscli — использует уже имеющиеся в проекте зависимости.

Запуск изнутри контейнера api (там уже есть boto3/botocore нужных версий):
    docker compose exec api python -m scripts.setup_cors

Или локально, если у тебя есть venv с установленным boto3:
    python scripts/setup_cors.py
"""

import boto3

from app.core.config import settings


def main() -> None:
    client = boto3.client(
        "s3",
        endpoint_url=settings.B2_ENDPOINT_URL,
        aws_access_key_id=settings.B2_KEY_ID,
        aws_secret_access_key=settings.B2_APPLICATION_KEY,
        region_name=settings.B2_REGION,
    )

    cors_configuration = {
        "CORSRules": [
            {
                "AllowedOrigins": [
                    "http://localhost:3000",
                    # Добавь сюда прод-домен фронтенда перед деплоем на Railway,
                    # например "https://kitroom.up.railway.app"
                ],
                "AllowedMethods": ["PUT", "GET", "HEAD"],
                "AllowedHeaders": ["*"],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": 3600,
            }
        ]
    }

    print(f"Настраиваю CORS для бакета '{settings.B2_BUCKET_NAME}'...")
    client.put_bucket_cors(
        Bucket=settings.B2_BUCKET_NAME,
        CORSConfiguration=cors_configuration,
    )
    print("CORS применён. Проверяю текущую конфигурацию:")

    result = client.get_bucket_cors(Bucket=settings.B2_BUCKET_NAME)
    for rule in result.get("CORSRules", []):
        print(f"  AllowedOrigins: {rule.get('AllowedOrigins')}")
        print(f"  AllowedMethods: {rule.get('AllowedMethods')}")
        print(f"  AllowedHeaders: {rule.get('AllowedHeaders')}")

    print("\nГотово. Presigned PUT из браузера теперь должен проходить CORS-проверку.")


if __name__ == "__main__":
    main()