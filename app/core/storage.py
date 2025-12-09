from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.models.schemas import GraphDefinition, WorkflowState, ExecutionStep
import json
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Integer, Text, Float, JSON, DateTime
from sqlalchemy.future import select

# --- SQLAlchemy Models for SQLite ---
Base = declarative_base()

class DBGraph(Base):
    __tablename__ = "graphs"
    id = Column(String, primary_key=True)
    definition = Column(JSON)
    created_at = Column(DateTime)

class DBRun(Base):
    __tablename__ = "runs"
    id = Column(String, primary_key=True)
    graph_id = Column(String)
    status = Column(String)
    current_node = Column(String, nullable=True)
    state = Column(JSON)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class DBLog(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String)
    node_id = Column(String)
    input_state = Column(JSON)
    output_state = Column(JSON)
    timestamp = Column(DateTime)
    duration_ms = Column(Float)


class BaseStorage(ABC):
    @abstractmethod
    async def save_graph(self, graph_id: str, definition: GraphDefinition): pass

    @abstractmethod
    async def get_graph(self, graph_id: str) -> Optional[GraphDefinition]: pass

    @abstractmethod
    async def save_run(self, run: WorkflowState): pass

    @abstractmethod
    async def get_run(self, run_id: str) -> Optional[WorkflowState]: pass

    @abstractmethod
    async def add_log(self, log: ExecutionStep): pass

    @abstractmethod
    async def get_logs(self, run_id: str) -> List[ExecutionStep]: pass


class InMemoryStorage(BaseStorage):
    def __init__(self):
        self.graphs: Dict[str, GraphDefinition] = {}
        self.runs: Dict[str, WorkflowState] = {}
        self.logs: Dict[str, List[ExecutionStep]] = {}

    async def save_graph(self, graph_id: str, definition: GraphDefinition):
        self.graphs[graph_id] = definition

    async def get_graph(self, graph_id: str) -> Optional[GraphDefinition]:
        return self.graphs.get(graph_id)

    async def save_run(self, run: WorkflowState):
        self.runs[run.run_id] = run

    async def get_run(self, run_id: str) -> Optional[WorkflowState]:
        return self.runs.get(run_id)

    async def add_log(self, log: ExecutionStep):
        if log.run_id not in self.logs:
            self.logs[log.run_id] = []
        self.logs[log.run_id].append(log)

    async def get_logs(self, run_id: str) -> List[ExecutionStep]:
        return self.logs.get(run_id, [])


class SQLiteStorage(BaseStorage):
    def __init__(self, db_url: str = "sqlite+aiosqlite:///./workflow.db"):
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
    
    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def save_graph(self, graph_id: str, definition: GraphDefinition):
        async with self.async_session() as session:
            db_graph = DBGraph(
                id=graph_id, 
                definition=definition.model_dump(mode="json"),
                created_at=datetime.now(timezone.utc)
            )
            session.add(db_graph)
            await session.commit()

    async def get_graph(self, graph_id: str) -> Optional[GraphDefinition]:
        async with self.async_session() as session:
            result = await session.execute(select(DBGraph).where(DBGraph.id == graph_id))
            db_graph = result.scalar_one_or_none()
            if db_graph:
                return GraphDefinition(**db_graph.definition)
            return None

    async def save_run(self, run: WorkflowState):
        async with self.async_session() as session:
            # Check if exists to update, else insert
            result = await session.execute(select(DBRun).where(DBRun.id == run.run_id))
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.status = run.status
                existing.current_node = run.current_node
                existing.state = run.state
                existing.updated_at = run.updated_at
            else:
                db_run = DBRun(
                    id=run.run_id,
                    graph_id=run.graph_id,
                    status=run.status,
                    current_node=run.current_node,
                    state=run.state,
                    created_at=run.created_at,
                    updated_at=run.updated_at
                )
                session.add(db_run)
            await session.commit()

    async def get_run(self, run_id: str) -> Optional[WorkflowState]:
        async with self.async_session() as session:
            result = await session.execute(select(DBRun).where(DBRun.id == run_id))
            db_run = result.scalar_one_or_none()
            if db_run:
                return WorkflowState(
                    run_id=db_run.id,
                    graph_id=db_run.graph_id,
                    status=db_run.status,
                    current_node=db_run.current_node,
                    state=db_run.state,
                    created_at=db_run.created_at,
                    updated_at=db_run.updated_at
                )
            return None

    async def add_log(self, log: ExecutionStep):
        async with self.async_session() as session:
            db_log = DBLog(
                run_id=log.run_id,
                node_id=log.node_id,
                input_state=log.input_state,
                output_state=log.output_state,
                timestamp=log.timestamp,
                duration_ms=log.duration_ms
            )
            session.add(db_log)
            await session.commit()

    async def get_logs(self, run_id: str) -> List[ExecutionStep]:
        async with self.async_session() as session:
            result = await session.execute(select(DBLog).where(DBLog.run_id == run_id).order_by(DBLog.timestamp))
            logs = result.scalars().all()
            return [
                ExecutionStep(
                    run_id=l.run_id,
                    node_id=l.node_id,
                    input_state=l.input_state,
                    output_state=l.output_state,
                    timestamp=l.timestamp,
                    duration_ms=l.duration_ms
                ) for l in logs
            ]
