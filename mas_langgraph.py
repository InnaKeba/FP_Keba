"""Базовий рівень. MAS supervisor + agents."""
import os
import operator
import asyncio
from typing import Annotated, Literal, TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite

from langchain_mcp_adapters.client import MultiServerMCPClient

from trajectory_logger import TrajectoryLogger
from tools_legacy import search_knowledge, calculate_refund

load_dotenv()

# Ініціалізація логера
logger = TrajectoryLogger("trajectory.json")

# ── 1. State ──
class MASState(TypedDict):
    messages: Annotated[list, operator.add]
    current_agent: str
    plan: list[str]
    current_step: int
    results: list[str]
    step_count: int
    trajectory: Annotated[list, operator.add]
    completed: bool
    pending_approval: bool

class RouteDecision(BaseModel):
    action: Literal['billing', 'tech', 'researcher', 'general'] = Field(description='Цільовий агент або "general" для нерозпізнаних запитів')
    reasoning: str = Field(description='Коротке пояснення вибору')

# Ініціалізація LLM через OpenRouter, провайдер Gemini 2.5 Flash
llm = ChatOpenAI(
    model="google/gemini-2.5-flash", 
    api_key=os.getenv("OPENROUTER_API_KEY"), 
    base_url="https://openrouter.ai/api/v1",
    temperature=0.1
)
supervisor_llm = llm.with_structured_output(RouteDecision)

# ── 2. Supervisor ──
async def supervisor_node(state: MASState) -> dict:
    SUPERVISOR_SYSTEM = """Ти — супервізор customer-support MAS. Маршрутизуй запит:
    - billing: про платежі, кошти, рахунки, повернення.
    - tech: про збій пристрою, помилки, налаштування, ПЕРЕВІРКУ ТА ОНОВЛЕННЯ ТІКЕТІВ (будь-які TKT-...).
    - researcher: довідкові питання — "як", "які правила", "що таке X", база знань, FAQ.
    - general: вітання, нерозпізнані запити.
    Поверни RouteDecision."""
    
    user_msg = state['messages'][-1].content if state['messages'] else ''
    decision = await supervisor_llm.ainvoke([
        SystemMessage(content=SUPERVISOR_SYSTEM), 
        HumanMessage(content=user_msg)
    ])
    
    step = logger.log_step('supervisor', 'route', user_msg, f'-> {decision.action}: {decision.reasoning}')
    
    return {
        'current_agent': decision.action,
        'step_count': state.get('step_count', 0) + 1,
        'trajectory': [step],
    }

async def general_agent(state: MASState) -> dict:
    reply = "Я загальний асистент. Ваш запит не стосується підтримки, але я спробую допомогти."
    step = logger.log_step('general', 'reply', 'Processing fallback query', reply)
    return {"messages": [AIMessage(content=reply, name="general")], "completed": True, "trajectory": [step]}

# ── 3. Головна функція ──
async def main():
    # Підключення MCP
    client = MultiServerMCPClient({
        'support': {
            'command': 'python',
            'args': [os.path.abspath('mcp_server.py')],
            'transport': 'stdio',
        },
    })
    mcp_tools = await client.get_tools()
    
    async with aiosqlite.connect("agent_state.db") as db_conn:
        
        def create_agent(agent_name: str, system_prompt: str, tools: list):
            agent_llm = llm.bind_tools(tools) if tools else llm
            async def node(state: MASState) -> dict:
                messages = [SystemMessage(content=system_prompt)] + state["messages"]
                response = await agent_llm.ainvoke(messages)
                
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    new_msgs = [response]
                    traj_steps = []

                    for tc in response.tool_calls:
                        tool_fn = {t.name: t for t in tools}.get(tc["name"])
                        if tool_fn:
                            res = await tool_fn.ainvoke(tc["args"])
                            new_msgs.append(ToolMessage(content=str(res), name=tc["name"], tool_call_id=tc["id"]))
                            traj_steps.append(logger.log_step(agent_name, 'tool_call', tc['name'], str(res)[:100], [tc['name']]))
                    
                    # Другий виклик LLM для підбиття підсумків на основі результатів інструментів
                    final_response = await agent_llm.ainvoke(messages + new_msgs)
                    new_msgs.append(final_response)
                    
                    step = logger.log_step(agent_name, 'generate', 'Final response', final_response.content)
                    traj_steps.append(step)
                    
                    return {
                        "messages": new_msgs,
                        "trajectory": traj_steps,
                        "step_count": state.get('step_count', 0) + 1,
                        "completed": True
                    }
                
                step = logger.log_step(agent_name, 'generate', 'Direct response', response.content)
                return {
                    "messages": [response],
                    "completed": True,
                    "trajectory": [step]
                }
            return node

        billing_agent = create_agent(
            "billing", 
            "Ти Billing Agent. Розраховуй повернення. Використовуй tools.", 
            mcp_tools + [calculate_refund]
        )
        
        tech_agent = create_agent(
            "tech", 
            "Ти Tech Agent (ReAct). Допомагаєш з пристроями. Використовуй tools для пошуку та перевірки тікетів.", 
            mcp_tools
        )
        
        researcher_agent = create_agent(
            "researcher", 
            "Ти Researcher. Відповідаєш на довідкові питання використовуючи FAQ RAG Tool.", 
            [search_knowledge]
        )

        def route(state: MASState) -> Literal['billing', 'tech', 'researcher', 'general', '__end__']:
            if state.get('completed'): return '__end__'
            return state.get('current_agent', 'general')

        # ── Побудова графа ──
        g = StateGraph(MASState)
        g.add_node('supervisor', supervisor_node)
        g.add_node('billing', billing_agent)
        g.add_node('tech', tech_agent)
        g.add_node('researcher', researcher_agent)
        g.add_node('general', general_agent)

        g.add_edge(START, 'supervisor')
        g.add_conditional_edges('supervisor', route)
        for agent in ['billing', 'tech', 'researcher', 'general']:
            g.add_edge(agent, END)

        saver = AsyncSqliteSaver(db_conn)
        app = g.compile(checkpointer=saver)

        # ── Демонстрація ──
        queries = [
            ('demo-1', 'Які правила повернення коштів за невикористаний період?'),
            ('demo-2', 'Перевір тікет TKT-002'),
            ('demo-3', 'Розрахуй повернення для 500 грн, використано 10 днів')
        ]

        print("\nЗапуск MAS...")
        for tid, query in queries:
            config = {'configurable': {'thread_id': tid}}
            print(f'\n{"="*60}\n[THREAD: {tid}] USER: {query}')
            
            async for event in app.astream({
                'messages': [HumanMessage(content=query)],
                'completed': False, 'step_count': 0, 'trajectory': []
            }, config=config):
                for node, data in event.items():
                    if node == 'supervisor':
                        print(f"[SUPERVISOR] Маршрутизація -> {data['current_agent'].upper()}")
                    else:
                        msg_content = data['messages'][-1].content
                        if msg_content:
                            print(f"[{node.upper()}]: {msg_content}")
        
        logger.save()
        print("\nТраєкторію збережено у trajectory.json")

if __name__ == "__main__":
    asyncio.run(main())