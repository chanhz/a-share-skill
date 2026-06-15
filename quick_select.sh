python3 pankou_stock_change/scripts/buy_signal.py --min-net 15 --min-types 2 --json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
filtered = [d for d in data if d['评级'] == 'A' and '封涨停板' not in d['买入类型']]
filtered.sort(key=lambda x: x['净强度'], reverse=True)
print(f'当前全市场A级标的（排除封涨停板）共 {len(filtered)} 只\n')
print(f\"{'代码':>8} {'名称':<10} {'时间':>8} {'价格':>10} {'净强度':>6} {'买入类型':<40} {'评级'}\")
print('-'*100)
for d in filtered:
    p = d['当前价格']
    p_str = f'{p:.2f}' if isinstance(p, (int,float)) and p < 10000 else f'{p:.4f}'
    print(f\"{d['代码']:>8} {d['名称']:<10} {d['当前时间']:>8} {p_str:>10} {d['净强度']:>6.0f} {d['买入类型']:<40} {d['评级']}\")
" 2>/dev/null
