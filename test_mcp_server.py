import asyncio, json
from mcp_server import mcp

async def call_tool(name: str, args: dict) -> str:
    """Хелпер: виклик MCP-tool у тестах."""
    result = await mcp.call_tool(name, args)
    blocks = result[0] if isinstance(result, tuple) else result
    return blocks[0].text

async def main():
    print('Starting MCP tests...')
    
    # 1. list_tools
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert {'get_ticket', 'update_ticket_status', 'search_tickets', 'get_customer', 'get_summary'}.issubset(names)
    print('TEST 1 PASS - list_tools')

    # 2. get_ticket (found)
    data = json.loads(await call_tool('get_ticket', {'ticket_id': 'TKT-001'}))
    assert data['id'] == 'TKT-001' and 'subject' in data
    print('TEST 2 PASS - get_ticket(TKT-001)')

    # 3. get_ticket (not found)
    data = json.loads(await call_tool('get_ticket', {'ticket_id': 'TKT-999'}))
    assert 'error' in data
    print('TEST 3 PASS - get_ticket(TKT-999) -> error')

    # 4. update_ticket_status (valid)
    data = json.loads(await call_tool('update_ticket_status', {
        'ticket_id': 'TKT-001', 'new_status': 'in_progress', 'reason': 'unit test'}))
    assert data.get('updated') == 'TKT-001'
    print('TEST 4 PASS - update_ticket_status(valid)')

    # 5. update_ticket_status (invalid status)
    data = json.loads(await call_tool('update_ticket_status', {
        'ticket_id': 'TKT-001', 'new_status': 'BOGUS'}))
    assert 'error' in data
    print('TEST 5 PASS - update_ticket_status(invalid) -> error')

    # 6. search_tickets
    data = json.loads(await call_tool('search_tickets', {'category': 'billing'}))
    assert isinstance(data['tickets'], list)
    print('TEST 6 PASS - search_tickets')

    # 7. list_resources
    resources = await mcp.list_resources()
    assert any('faq' in str(r.uri) for r in resources)
    print('TEST 7 PASS - list_resources contains faq')

    # 8. list_prompts
    prompts = await mcp.list_prompts()
    assert 'support_reply' in [p.name for p in prompts]
    print('TEST 8 PASS - list_prompts contains support_reply')

    print('All MCP unit tests passed!')

if __name__ == '__main__':
    asyncio.run(main())