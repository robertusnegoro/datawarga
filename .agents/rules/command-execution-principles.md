---
trigger: model_decision
description: When executing external commands, shell scripts, or system processes
---

## Command Execution Principles

### Security

**Never execute user input directly:**

- ❌ `exec(userInput)`  
- ❌ `shell("rm " + userFile)`  
- ✅ Use argument lists, not shell string concatenation  
- ✅ Validate and sanitize all arguments

**Run with minimum permissions:**

- Never run commands as root/admin without explicit human approval. If elevated permissions are absolutely required, STOP and request authorization.
- Use least-privilege service accounts

### Portability

**Use language standard library:**

- Avoid shell commands when standard library provides functionality  
- Example: Use file I/O APIs instead of `cat`, `cp`, `mv`

**Test on all target OS:**

- Windows, Linux, macOS have different commands and behaviors  
- Use path joining functions (don't concatenate with /)

### Error Handling

**Check exit codes:**

- Non-zero exit code = failure  
- Capture and log stderr  
- Set timeouts for long-running commands  
- Handle "command not found" gracefully

### Environment

**Python Virtual Environment:**

The project uses a `.venv` virtual environment at the repository root. **All Python commands MUST use the venv explicitly.** Do not rely on the system `python` or assume the venv is already activated.

**Activation (when running an interactive shell session):**

```bash
source .venv/bin/activate
```

**Preferred: explicit executable paths (no activation needed):**

Use explicit `.venv/bin/` paths in all commands to guarantee the correct environment regardless of shell state:

| Task | Command |
| ---- | ------- |
| Run Python scripts | `.venv/bin/python script.py` |
| Django management | `.venv/bin/python datawarga/manage.py <command>` |
| Run dev server | `.venv/bin/python datawarga/manage.py runserver` |
| Run migrations | `.venv/bin/python datawarga/manage.py migrate` |
| Install packages | `.venv/bin/pip install <package>` |
| Run tests | `.venv/bin/pytest` |
| Lint (ruff) | `.venv/bin/ruff check . --fix` |
| Format (ruff) | `.venv/bin/ruff format .` |
| Type check (mypy) | `.venv/bin/mypy src/ --strict` |
| Security scan | `.venv/bin/bandit -r src/ -c pyproject.toml` |
| Dependency audit | `.venv/bin/pip-audit` |

**Rules:**

- ❌ Never use bare `python`, `pip`, `pytest`, `ruff`, `mypy` — these may resolve to the wrong system-level interpreter or tool.
- ✅ Always prefix with `.venv/bin/` (e.g., `.venv/bin/python`, `.venv/bin/pip`, `.venv/bin/pytest`).
- ✅ If activating the venv in a shell script, use `source .venv/bin/activate` at the top of the script.
- ✅ When in doubt, verify the active interpreter: `.venv/bin/python -c "import sys; print(sys.executable)"`

### Command Execution Checklist

- [ ] Is user input sanitized/validated before use in commands?
- [ ] Are arguments passed as lists (not shell string concatenation)?
- [ ] Are commands running with minimum necessary permissions?
- [ ] Are exit codes checked and errors handled?
- [ ] Are timeouts set for long-running commands?
- [ ] Is stderr captured and logged?

### Related Principles
- Security Mandate @security-mandate.md
- Security Principles @security-principles.md