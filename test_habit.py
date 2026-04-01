from tools.menu_analyzer import analyze_allergens
import json
test_profiles = [{'name': 'MSG', 'restrictions': ['MSG-Free']}]
res = analyze_allergens('Habit Burger', 'California', test_profiles)
for r in res.get('results', []):
    print(f"[{r['status']}] {r['dish_name']} | {r.get('ingredients')}")
