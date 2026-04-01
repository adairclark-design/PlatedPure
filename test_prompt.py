from tools.menu_analyzer import analyze_allergens
import json
test_profiles = [{'name': 'MSG', 'restrictions': ['MSG-Free']}]
res = analyze_allergens('Panda Express', 'Oregon', test_profiles)
safe = [r for r in res.get('results', []) if r.get('status') == 'SAFE']
print(f"SAFE ITEMS: {len(safe)}")
for r in safe: print(f"  [SAFE] {r['dish_name']} | {r.get('ingredients')}")
