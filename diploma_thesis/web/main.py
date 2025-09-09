import re

from fastapi import FastAPI, Request, Body, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship
import uvicorn
from pydantic import BaseModel

from diploma_thesis.settings import NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_URI
from diploma_thesis.web.utils_for_web import is_safe_query

app = FastAPI()
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@ app.get("/", response_class=HTMLResponse)
def get_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/graph")
def get_graph():
    with driver.session() as session:
        result = session.run("""
            MATCH (n)-[r]->(m)
            RETURN n, r, m
            LIMIT 100
        """)
        nodes = {}
        edges = []
        for record in result:
            for value in record.values():
                if isinstance(value, Node):
                    label = value.get("title") or value.get("name") or str(value.id)
                    nodes[value.id] = {
                        "data": {"id": str(value.id), "label": label}
                    }
                elif isinstance(value, Relationship):
                    edges.append({
                        "data": {
                            "source": str(value.start_node.id),
                            "target": str(value.end_node.id),
                            "label": value.type
                        }
                    })
        return {"nodes": list(nodes.values()), "edges": edges}


class QueryRequest(BaseModel):
    query: str


@app.post("/api/query")
def run_query(request: QueryRequest = Body(...)):
    if not is_safe_query(request.query):
        raise HTTPException(status_code=400, detail="Unsafe Cypher query detected.")

    with driver.session() as session:
        result = session.run(request.query)
        nodes = {}
        edges = []
        for record in result:
            # Try extracting nodes and relationships
            for value in record.values():
                if hasattr(value, "id") and hasattr(value, "labels"):
                    nodes[value.id] = {
                        "data": {"id": str(value.id), "label": value.get("name", str(value.id))}
                    }
                elif hasattr(value, "start_node") and hasattr(value, "end_node"):
                    edges.append({
                        "data": {
                            "source": str(value.start_node.id),
                            "target": str(value.end_node.id),
                            "label": value.type
                        }
                    })
        return {"nodes": list(nodes.values()), "edges": edges}


if __name__ == "__main__":
    uvicorn.run("diploma_thesis.web.main:app", host="0.0.0.0", port=8000, reload=True)
