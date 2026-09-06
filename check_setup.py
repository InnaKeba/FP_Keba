import asyncio
from mcp.server.fastmcp import FastMCP
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command
import chromadb
from dotenv import load_dotenv

load_dotenv()

async def main():
    print("Перевірка середовища...\n")

    # Перевірка MCP
    try:
        mcp = FastMCP('test')
        @mcp.tool()
        def ping() -> str:
            """Ping."""
            return 'pong'
        
        tools = await mcp.list_tools()
        print(f'MCP: {len(tools)} tool(s) registered (FastMCP працює)')
    except Exception as e:
        print(f'Помилка MCP: {e}')

    # Перевірка LangGraph
    try:
        assert StateGraph and SqliteSaver and interrupt and Command
        print('LangGraph + SqliteSaver + interrupt: OK')
    except Exception as e:
        print(f'Помилка LangGraph: {e}')

    # Перевірка ChromaDB
    try:
        client = chromadb.PersistentClient(path='./chroma_db')
        print('ChromaDB: PersistentClient створено (OK)')
    except Exception as e:
        print(f'Помилка ChromaDB: {e}')

if __name__ == "__main__":
    asyncio.run(main())