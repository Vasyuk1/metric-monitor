import os
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, Text, Index, select, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://metrics:metrics@postgres/metrics")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class Agent(Base):
    __tablename__ = 'agents'
    agent_id = Column(String, primary_key=True)
    hostname = Column(String, nullable=True)
    ip = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    first_seen = Column(Integer, nullable=False)
    last_seen = Column(Integer, nullable=False)
    tags = Column(Text)  # JSON
    version = Column(String, nullable=True)

class Metric(Base):
    __tablename__ = 'metrics'
    id = Column(Integer, primary_key=True)
    agent_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=False)
    timestamp = Column(Integer, nullable=False, index=True)
    tags = Column(Text)  # JSON

    __table_args__ = (
        Index('idx_agent_time', 'agent_id', 'timestamp'),
        Index('idx_name_time', 'name', 'timestamp'),
    )

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def save_metric(agent_id: str, timestamp: int, name: str, value: float, tags: dict = None):
    async with AsyncSessionLocal() as session:
        # Проверяем, существует ли агент
        stmt = select(Agent).where(Agent.agent_id == agent_id)
        result = await session.execute(stmt)
        agent = result.scalar_one_or_none()
        if agent is None:
            agent = Agent(
                agent_id=agent_id,
                first_seen=timestamp,
                last_seen=timestamp,
                tags=json.dumps(tags) if tags else None
            )
            session.add(agent)
        else:
            agent.last_seen = timestamp
            # Обновляем поля, если они переданы в tags
            if tags:
                if 'hostname' in tags:
                    agent.hostname = tags['hostname']
                if 'ip' in tags:
                    agent.ip = tags['ip']
                if 'version' in tags:
                    agent.version = tags['version']
                # Обновляем tags (последние теги)
                agent.tags = json.dumps(tags)

        metric = Metric(
            agent_id=agent_id,
            name=name,
            value=value,
            timestamp=timestamp,
            tags=json.dumps(tags) if tags else None
        )
        session.add(metric)
        await session.commit()