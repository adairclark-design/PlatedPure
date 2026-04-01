import json
from tools.menu_analyzer import analyze_allergens
res = analyze_allergens('Burger King', 'California', [{'name': 'MSG', 'restrictions': ['MSG']}])
for r in res.get('results', []):
    print(f"[{r['status']}] {r['dish_name']} | Q: {r.get('server_question', 'MISSING')}")
