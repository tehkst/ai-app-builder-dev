from app.services.file_writer_service import safe_write_generated_files


project_id = "test-project-005"

generated_files = [
    {
        "file_path": "README.md",
        "content": "# Startup CRM Platform\n\nGenerated app.",
    },
    {
        "file_path": "backend/main.py",
        "content": """from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def health_check():
    return {"ok": True}
""",
    },
    {
        "file_path": "frontend/app/page.tsx",
        "content": """export default function HomePage() {
  return <h1>Generated App</h1>;
}
""",
    },
]

written = safe_write_generated_files(project_id, generated_files)

print("Written files:")
for path in written:
    print(path)
