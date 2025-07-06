from datetime import datetime, timezone
from celery import shared_task
from sqlalchemy import delete
from database import async_session_maker, ActivationTokenModel, PasswordResetTokenModel


@shared_task
def cleanup_expired_tokens():
    import asyncio
    asyncio.run(_cleanup_expired_tokens())


async def _cleanup_expired_tokens():
    async with async_session_maker() as session:
        now = datetime.now(timezone.utc)
        await session.execute(
            delete(ActivationTokenModel).where(ActivationTokenModel.expires_at < now)
        )
        await session.execute(
            delete(PasswordResetTokenModel).where(PasswordResetTokenModel.expires_at < now)
        )
        await session.commit()
