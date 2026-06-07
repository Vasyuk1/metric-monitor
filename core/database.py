import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Index
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://metrics:metrics@postgres/metrics")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Agent(Base):
    __tablename__ = 'agents'
    agent_id = Column(String, primary_key=True)
    hostname = Column(String, nullable=True)
    ip = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    first_seen = Column(Integer, nullable=False)
    last_seen = Column(Integer, nullable=False)
    tags = Column(Text)
    version = Column(String, nullable=True)

class Metric(Base):
    __tablename__ = 'metrics'
    id = Column(Integer, primary_key=True)
    agent_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=False)
    timestamp = Column(Integer, nullable=False, index=True)
    tags = Column(Text)

    __table_args__ = (
        Index('idx_agent_time', 'agent_id', 'timestamp'),
        Index('idx_name_time', 'name', 'timestamp'),
    )

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    login = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default='user')
    created_at = Column(Integer, nullable=False)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_metric(agent_id: str, timestamp: int, name: str, value: float, tags: dict = None):
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if agent is None:
            agent = Agent(
                agent_id=agent_id,
                first_seen=timestamp,
                last_seen=timestamp,
                tags=json.dumps(tags) if tags else None
            )
            db.add(agent)
        else:
            agent.last_seen = timestamp
            if tags:
                if 'hostname' in tags:
                    agent.hostname = tags['hostname']
                if 'ip' in tags:
                    agent.ip = tags['ip']
                if 'version' in tags:
                    agent.version = tags['version']
                agent.tags = json.dumps(tags)
        metric = Metric(
            agent_id=agent_id,
            name=name,
            value=value,
            timestamp=timestamp,
            tags=json.dumps(tags) if tags else None
        )
        db.add(metric)
        db.commit()
    finally:
        db.close()