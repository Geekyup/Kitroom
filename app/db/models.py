"""
Единая точка регистрации всех доменных моделей.

Модели живут внутри своих доменов (app/auth/models.py, app/kits/models.py),
но между ними есть межмодульные relationship (User.kits <-> DrumKit.owner),
которые SQLAlchemy резолвит по имени класса через configure_mappers().
Чтобы это сработало, оба модуля должны быть импортированы до первого
обращения к БД — этот файл и есть то единое место импорта.

Используется в: alembic/env.py, app/worker/settings.py, app/main.py.
"""

from app.auth.models import RefreshToken, User, VerificationCode  # noqa: F401
from app.kits.models import DrumKit, DrumKitNode  # noqa: F401
