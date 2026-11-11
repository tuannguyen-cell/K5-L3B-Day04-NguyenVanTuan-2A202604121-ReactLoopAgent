import json
from status_tools import StatusTools

print("=== Test get_status ===")
result = StatusTools().get_status("github", "Actions")
print(json.dumps(result, ensure_ascii=True, indent=2))

print("\n=== Test get_incident_details ===")
result = StatusTools().get_incident_details("cloudflare", "wp49bp8bqo6c")
print(json.dumps(result, ensure_ascii=True, indent=2))