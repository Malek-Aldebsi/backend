ans = {'answer': None, 'duration': 18}

res = {'duration': 0, 'answer': ans.get('answer', {}).get(str('id'), None) if ans['answer'] else None}

print(res)