import json
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name='support_domain_server',
    instructions='Сервер з ресурсами customer support: тікети, клієнти, FAQ, дії.',
)

# Mock data
TICKETS = {
    'TKT-001': {'customer_id': 'C-100', 'subject': 'Не списано платіж', 'status': 'open', 'priority': 'high', 'category': 'billing'},
    'TKT-002': {'customer_id': 'C-101', 'subject': 'Не вмикається пристрій', 'status': 'in_progress', 'priority': 'medium', 'category': 'tech'},
    'TKT-003': {'customer_id': 'C-102', 'subject': 'Запит на повернення', 'status': 'open', 'priority': 'high', 'category': 'billing'}
}
CUSTOMERS = {
    'C-100': {'name': 'Олег Петренко', 'tier': 'gold', 'email': 'oleh@example.com'},
    'C-101': {'name': 'Марія Коваленко', 'tier': 'silver', 'email': 'maria@example.com'}
}

@mcp.tool()
def get_ticket(ticket_id: str) -> str:
    """Отримати тікет за ID.
    Args:
        ticket_id: Ідентифікатор тікета (формат TKT-XXX).
    """
    try:
        t = TICKETS.get(ticket_id)
        if not t:
            return json.dumps({'error': f'Ticket {ticket_id} not found'}, ensure_ascii=False)
        return json.dumps({'id': ticket_id, **t}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})

@mcp.tool()
def update_ticket_status(ticket_id: str, new_status: str, reason: str = '') -> str:
    """Оновити статус тікета.
    Args:
        ticket_id: ID тікета.
        new_status: open | in_progress | resolved | closed.
        reason: Причина зміни.
    """
    try:
        valid = {'open', 'in_progress', 'resolved', 'closed'}
        if ticket_id not in TICKETS:
            return json.dumps({'error': f'Ticket {ticket_id} not found'}, ensure_ascii=False)
        if new_status not in valid:
            return json.dumps({'error': f'Invalid status. Valid: {sorted(valid)}'}, ensure_ascii=False)
        
        old = TICKETS[ticket_id]['status']
        TICKETS[ticket_id]['status'] = new_status
        return json.dumps({
            'updated': ticket_id, 'old_status': old, 'new_status': new_status,
            'reason': reason, 'timestamp': datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})

@mcp.tool()
def search_tickets(category: str) -> str:
    """Знайти тікети за категорією (наприклад: 'billing', 'tech')."""
    try:
        results = [{**t, "id": tid} for tid, t in TICKETS.items() if t['category'] == category]
        return json.dumps({"category": category, "tickets": results}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})

@mcp.tool()
def get_customer(customer_id: str) -> str:
    """Отримати дані клієнта за ID (формат C-XXX)."""
    try:
        c = CUSTOMERS.get(customer_id)
        if not c:
            return json.dumps({'error': f'Customer {customer_id} not found'}, ensure_ascii=False)
        return json.dumps({'id': customer_id, **c}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})

@mcp.tool()
def get_summary() -> str:
    """Отримати загальну статистику системи підтримки."""
    try:
        total = len(TICKETS)
        open_t = sum(1 for t in TICKETS.values() if t['status'] == 'open')
        return json.dumps({"total_tickets": total, "open_tickets": open_t}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})

@mcp.resource('faq://general')
def faq_resource() -> str:
    """Загальний FAQ для customer support — readonly довідник."""
    faq = [
        {'q': 'Як скинути пароль?', 'a': 'Сторінка входу → "Забули пароль?" → введіть email.'},
        {'q': 'Як повернути кошти?', 'a': 'Зверніться у billing-агента; повернення 3-5 днів.'},
        {'q': 'Час відповіді саппорту?', 'a': 'Gold: до 1 год; Silver: до 4 год; Standard: до 24 год.'},
    ]
    return json.dumps(faq, ensure_ascii=False)

@mcp.prompt()
def support_reply(customer_name: str, issue_summary: str, tone: str = 'professional') -> str:
    """Згенерувати ввічливу відповідь клієнту.
    Args:
        customer_name: Ім'я клієнта.
        issue_summary: Короткий опис проблеми.
        tone: professional | empathetic | concise.
    """
    tones = {
        'professional': 'Сформулюй формальну, чітку відповідь',
        'empathetic': 'Сформулюй теплу відповідь з визнанням труднощів клієнта',
        'concise': 'Сформулюй коротку відповідь без зайвих фраз',
    }
    return (f'{tones.get(tone, tones["professional"])} клієнту {customer_name}. '
            f'Тема: {issue_summary}. Запропонуй наступний крок та строки.')

if __name__ == '__main__':
    mcp.run(transport='stdio')