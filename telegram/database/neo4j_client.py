from neo4j import AsyncGraphDatabase
from typing import Optional, Any
from contextlib import asynccontextmanager
import logging

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self._closed = False

    async def close(self):
        if not self._closed:
            await self.driver.close()
            self._closed = True

    @asynccontextmanager
    async def get_session(self):
        """Контекстный менеджер для сессии"""
        session = self.driver.session()
        try:
            yield session
        finally:
            await session.close()

    async def execute_query(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> list[dict]:
        """Выполняет Cypher-запрос (чтение)"""
        async with self.get_session() as session:
            async def work(tx):
                result = await tx.run(query, parameters or {})
                return await result.data()
            
            return await session.execute_read(work)

    async def execute_write(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> list[dict]:
        """Выполняет запись с транзакцией"""
        async with self.get_session() as session:
            async def work(tx):
                result = await tx.run(query, parameters or {})
                return await result.data()
            
            return await session.execute_write(work)


# Глобальный экземпляр
neo4j_client = Neo4jClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)