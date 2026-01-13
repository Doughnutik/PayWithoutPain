from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.db_name = "neo4j"

    def close(self):
        if self.driver is not None:
            self.driver.close()

    def add_person(self, name):
        summary = self.driver.execute_query('CREATE (p:Person {name: $name})',
            name=name
            database_=self.,
        ).summary
        print("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))