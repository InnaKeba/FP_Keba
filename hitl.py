"""Демонстрація HITL approval flow для ризикового MCP-tool"""
import operator
import asyncio
import aiosqlite
from typing import Annotated, TypedDict
from langchain_core.messages import HumanMessage, AIMessage, ToolCall
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import interrupt, Command

class HITLState(TypedDict):
    messages: Annotated[list, operator.add]
    current_agent: str
    pending_approval: bool

RISKY_TOOLS = {'update_ticket_status', 'delete_customer', 'send_mass_email'}

def agent_node(state: HITLState) -> dict:
    tc = ToolCall(name='update_ticket_status', args={'ticket_id': 'TKT-001', 'new_status': 'closed'}, id='call_123')
    msg = AIMessage(content='', tool_calls=[tc])
    return {'messages': [msg], 'current_agent': 'billing', 'pending_approval': True}

def approval_gate(state: HITLState) -> dict:
    """HITL: блокує граф, чекає approve/reject/edit."""
    last_msg = state['messages'][-1]
    if not hasattr(last_msg, 'tool_calls') or not last_msg.tool_calls:
        return {'pending_approval': False}

    results = []
    for tc in last_msg.tool_calls:
        if tc['name'] not in RISKY_TOOLS:
            continue
        
        decision = interrupt({
            'message': 'Підтвердити ризикову дію',
            'tool': tc['name'],
            'args': tc['args'],
            'agent_name': state['current_agent'],
        })
        
        if decision.get('action') == 'reject':
            return {'messages': [AIMessage(content=f'[REJECTED] Дія {tc["name"]} відхилена оператором.')], 'pending_approval': False}
        
        if decision.get('action') == 'edit':
            tc['args'].update(decision.get('args', {}))
            results.append(f'[EDITED] Дія {tc["name"]} відредагована. Нові аргументи: {tc["args"]}')
        elif decision.get('action') == 'approve':
            results.append(f'[APPROVED] Дія {tc["name"]} повністю схвалена. Аргументи: {tc["args"]}')

    return {'messages': [AIMessage(content="\n".join(results))], 'pending_approval': False}

async def main():
    g = StateGraph(HITLState)
    g.add_node('agent', agent_node)
    g.add_node('approval_gate', approval_gate)
    g.add_edge(START, 'agent')
    g.add_edge('agent', 'approval_gate')
    g.add_edge('approval_gate', END)

    async with aiosqlite.connect("hitl_test.db") as db_conn:
        saver = AsyncSqliteSaver(db_conn)
        app = g.compile(checkpointer=saver)

        print("--- Scenario 1: Approve ---")
        config1 = {'configurable': {'thread_id': 'hitl-scenario-1'}}
        async for event in app.astream({'messages': [HumanMessage(content='Закрий тікет')]}, config=config1):
            if '__interrupt__' in event:
                print("[System] Граф призупинено. Очікування рішення оператора...")
                break
        
        async for event in app.astream(Command(resume={'action': 'approve'}), config=config1):
            pass
        state1 = await app.aget_state(config1)
        print(state1.values['messages'][-1].content)


        print("\n--- Scenario 2: Reject ---")
        config2 = {'configurable': {'thread_id': 'hitl-scenario-2'}}
        async for event in app.astream({'messages': [HumanMessage(content='Закрий тікет')]}, config=config2):
            if '__interrupt__' in event:
                break
        
        async for event in app.astream(Command(resume={'action': 'reject', 'reason': 'Не час'}), config=config2):
            pass
        state2 = await app.aget_state(config2)
        print(state2.values['messages'][-1].content)


        print("\n--- Scenario 3: Edit ---")
        config3 = {'configurable': {'thread_id': 'hitl-scenario-3'}}
        async for event in app.astream({'messages': [HumanMessage(content='Закрий тікет')]}, config=config3):
            if '__interrupt__' in event:
                break
        
        async for event in app.astream(Command(resume={'action': 'edit', 'args': {'new_status': 'in_progress'}}), config=config3):
            pass
        state3 = await app.aget_state(config3)
        print(state3.values['messages'][-1].content)

if __name__ == '__main__':
    asyncio.run(main())