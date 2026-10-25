import csv, json

rows = list(csv.DictReader(open('output.csv', encoding='utf-8')))
for r in rows:
    if r['deletion_status'] == 'INCOMPLETE':
        steps = json.loads(r['steps_json'])
        print('INCOMPLETE:', r['case_id'])
        for s in steps:
            print('  step %d: %s | %s | %s | %s | %s | %s' % (
                s['step_no'], s['phase'], s['system_id'], s['resource_id'],
                s['operation'], s['state'], s['evidence_id']))
        break

print('---')
for r in rows:
    if r['deletion_status'] == 'COMPLETE':
        steps = json.loads(r['steps_json'])
        print('COMPLETE:', r['case_id'])
        for s in steps:
            print('  step %d: %s | %s | %s | %s | %s | %s' % (
                s['step_no'], s['phase'], s['system_id'], s['resource_id'],
                s['operation'], s['state'], s['evidence_id']))
        break
