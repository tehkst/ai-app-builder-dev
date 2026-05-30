import re

from app.ai.state import ProjectState


def extract_imports(content: str):
    imports = []

    for line in content.splitlines():
        line = line.strip()

        match = re.match(
            r"from\s+(app\.[\w\.]+)\s+import\s+(.+)",
            line,
        )

        if match:
            module_name = match.group(1)
            symbols = [
                symbol.strip().split(" as ")[0]
                for symbol in match.group(2).split(",")
            ]

            imports.append(
                {
                    "module": module_name,
                    "symbols": symbols,
                }
            )

    return imports


def module_to_file_path(module_name: str) -> str:
    if not module_name.startswith("app."):
        return ""

    if module_name == "app.api.routes":
        return "backend/app/api/routes/__init__.py"

    if module_name == "app.api":
        return "backend/app/api/__init__.py"

    return "backend/" + "/".join(module_name.split(".")) + ".py"


def contract_guard_node(state: ProjectState) -> ProjectState:
    files = state.get("file_manifest", {}).get("files", [])
    contract = state.get("interface_contract", {})

    approved_exports = {}

    for item in contract.get("exported_symbols", []):
        file_path = item.get("file_path")
        symbol_name = item.get("symbol_name")

        if file_path not in approved_exports:
            approved_exports[file_path] = set()

        approved_exports[file_path].add(symbol_name)

    issues = []

    for file in files:
        consumer_path = file.get("file_path")
        content = file.get("content", "")

        imports = extract_imports(content)

        for import_item in imports:
            producer_path = module_to_file_path(import_item["module"])

            if not producer_path:
                continue

            approved_symbols = approved_exports.get(producer_path)

            if approved_symbols is None:
                continue

            for symbol in import_item["symbols"]:
                if symbol not in approved_symbols:
                    issues.append(
                        {
                            "severity": "high",
                            "type": "unapproved_symbol",
                            "producer": producer_path,
                            "consumer": consumer_path,
                            "symbol": symbol,
                            "issue": f"Symbol '{symbol}' is not approved in interface contract",
                        }
                    )

    return {
        **state,
        "contract_report": {
            "passed": len(issues) == 0,
            "issues": issues,
        },
        "current_step": "contract_guard_completed",
    }
