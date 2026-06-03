import json

from app.ai.graphs.project_graph import project_graph
from app.ai.graphs.approval_resume_graph import approval_resume_graph


initial_state = {
    "project_id": "crm-saas-multifile-001",
    "raw_prompt": """
    Build a CRM SaaS platform for SMEs with:
    - customer management
    - analytics dashboard
    - admin panel
    - authentication
    """,
}


result = project_graph.invoke(initial_state)


print("\n===== REVIEW STATUS =====")
print(result.get("review_status"))

print("\n===== CURRENT STEP =====")
print(result.get("current_step"))

print("\n===== APPROVAL REQUIRED =====")
print(result.get("approval_required"))

print("\n===== GENERATED FILES BEFORE APPROVAL =====")
print(result.get("generated_files"))

print("\n===== FIX ATTEMPTS =====")
print(result.get("fix_attempts"))

print("\n===== REVIEW FEEDBACK =====")
print(result.get("review_feedback", "")[:2000])

print("\n===== DEPENDENCY REPORT =====")
print(json.dumps(result.get("dependency_report", {}), indent=2))

print("\n===== CONTRACT REPORT =====")
print(json.dumps(result.get("contract_report", {}), indent=2))


manifest = result.get("file_manifest", {})
files = manifest.get("files", [])

print("\n===== FILE COUNT =====")
print(len(files))


print("\n===== AUTH SCHEMA FILE =====")
for file in files:
    if file.get("file_path") == "backend/app/schemas/auth.py":
        print(file.get("content"))


print("\n===== ALL FILES IN MANIFEST =====")

for file in files:
    print(file.get("file_path"))


print("\n===== API INIT FILE =====")
for file in files:
    if file.get("file_path") == "backend/app/api/__init__.py":
        print(file.get("content"))


feedback = result.get("review_feedback", "")
normalized_feedback = (
    feedback
    .replace("*", "")
    .replace("`", "")
    .strip()
    .lower()
)

dependency_passed = result.get("dependency_report", {}).get("passed") is True
contract_passed = result.get("contract_report", {}).get("passed") is True
review_passed = "overall status: pass" in normalized_feedback

ready_for_approval = (
    result.get("approval_required") is True
    and result.get("current_step") == "waiting_for_human_approval"
    and dependency_passed
    and contract_passed
    and review_passed
)

if ready_for_approval:
    approved_state = {
        **result,
        "approved": True,
        "review_status": "PASS",
    }

    final_result = approval_resume_graph.invoke(approved_state)

    print("\n===== AFTER APPROVAL STEP =====")
    print(final_result.get("current_step"))

    print("\n===== RUNTIME REPORT =====")
    print(json.dumps(final_result.get("runtime_report", {}), indent=2))

    print("\n===== GENERATED FILES AFTER APPROVAL =====")
    print(final_result.get("generated_files"))

else:
    print("\n===== APPROVAL SKIPPED =====")
    print("Project is not ready for final approval.")
