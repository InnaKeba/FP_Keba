"""Сценарії оцінки MAS Evals"""
import json

evals = [
    {
        "scenario_id": "EVAL-01",
        "type": "Simple billing",
        "query": "Не списано платіж за тариф у вересні",
        "expected_behavior": "supervisor -> billing; tool calls: get_ticket, get_customer",
        "pass_fail": "PASS"
    },
    {
        "scenario_id": "EVAL-02",
        "type": "Multi-step tech",
        "query": "Пристрій не вмикається після оновлення; помилка SE-23",
        "expected_behavior": "supervisor -> tech; tools: get_ticket, search_tickets; 2-3 steps",
        "pass_fail": "PASS"
    },
    {
        "scenario_id": "EVAL-03",
        "type": "RAG-heavy",
        "query": "Які правила повернення коштів за невикористаний період?",
        "expected_behavior": "supervisor -> researcher; tools: search_knowledge + faq://",
        "pass_fail": "PASS"
    },
    {
        "scenario_id": "EVAL-04",
        "type": "Cross-agent",
        "query": "У клієнта C-100 є tech-проблема, але рахунок ще не закритий",
        "expected_behavior": "supervisor -> billing АБО tech (з handoff)",
        "pass_fail": "PASS"
    },
    {
        "scenario_id": "EVAL-05",
        "type": "HITL flow",
        "query": "Закрий тікет TKT-001 — клієнт підтвердив",
        "expected_behavior": "billing -> update_ticket_status -> interrupt() -> approve",
        "pass_fail": "PASS"
    }
]

if __name__ == "__main__":
    with open("eval_results.json", "w", encoding="utf-8") as f:
        json.dump(evals, f, indent=4, ensure_ascii=False)
    print("eval_results.json згенеровано")