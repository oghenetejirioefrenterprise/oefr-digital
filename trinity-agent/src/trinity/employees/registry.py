"""Employee registry — create, list, read, and remove employee identities."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from trinity.employees.defaults import generate_identity

# ── Validation ──────────────────────────────────────────────────

_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _validate_name(name: str) -> str:
    """Validate and normalize an employee name.

    Names must be lowercase, start with a letter, and contain only
    alphanumeric characters and underscores.

    Raises:
        ValueError: If the name is invalid.
    """
    name = name.strip().lower()
    if not name:
        raise ValueError("Employee name cannot be empty.")
    if not _NAME_PATTERN.match(name):
        raise ValueError(
            f"Invalid employee name '{name}'. "
            "Names must be lowercase, start with a letter, and contain "
            "only letters, digits, and underscores."
        )
    return name


def _employees_dir(trinity_dir: Path) -> Path:
    """Return the employees directory path."""
    return trinity_dir / "employees"


# ── Public API ──────────────────────────────────────────────────


def init_employees_dir(trinity_dir: Path) -> None:
    """Create .trinity/employees/ if it does not exist."""
    _employees_dir(trinity_dir).mkdir(parents=True, exist_ok=True)


def create_employee(
    trinity_dir: Path,
    name: str,
    title: str,
    company_name: str,
    company_desc: str,
) -> Path:
    """Create an employee directory and identity.md.

    Args:
        trinity_dir: Path to the .trinity directory.
        name: Employee name (lowercase, alphanumeric + underscore).
        title: Role title (e.g., "CEO", "CMO").
        company_name: Company name for identity context.
        company_desc: Company description for identity context.

    Returns:
        Path to the created identity.md file.

    Raises:
        ValueError: If the name is invalid or the employee already exists.
    """
    name = _validate_name(name)

    emp_dir = _employees_dir(trinity_dir) / name
    if emp_dir.exists():
        raise ValueError(f"Employee '{name}' already exists at {emp_dir}")

    emp_dir.mkdir(parents=True, exist_ok=True)

    identity_content = generate_identity(
        name=name,
        title=title,
        company_name=company_name,
        company_description=company_desc,
    )

    identity_path = emp_dir / "identity.md"
    identity_path.write_text(identity_content, encoding="utf-8")

    return identity_path


def list_employees(trinity_dir: Path) -> list[dict]:
    """List all employees.

    Returns a list of dicts with keys: name, title, identity_path.
    The title is extracted from the first line of each identity.md.
    """
    employees_root = _employees_dir(trinity_dir)
    if not employees_root.exists():
        return []

    result = []
    for emp_dir in sorted(employees_root.iterdir()):
        if not emp_dir.is_dir():
            continue

        identity_path = emp_dir / "identity.md"
        title = ""

        if identity_path.exists():
            first_line = identity_path.read_text(encoding="utf-8").split("\n", 1)[0]
            # Parse title from "# Name — Title of Company" or "# Name — Title at Company"
            if "—" in first_line:
                after_dash = first_line.split("—", 1)[1].strip()
                # Remove "of Company" or "at Company" suffix
                for sep in (" of ", " at "):
                    if sep in after_dash:
                        title = after_dash.split(sep, 1)[0].strip()
                        break
                else:
                    title = after_dash

        result.append({
            "name": emp_dir.name,
            "title": title,
            "identity_path": identity_path,
        })

    return result


def get_employee_identity(trinity_dir: Path, name: str) -> str | None:
    """Read and return the full identity.md content for an employee.

    Returns None if the employee or identity file does not exist.
    """
    try:
        name = _validate_name(name)
    except ValueError:
        return None

    identity_path = _employees_dir(trinity_dir) / name / "identity.md"
    if not identity_path.exists():
        return None

    return identity_path.read_text(encoding="utf-8")


def get_employee_skills(trinity_dir: Path, name: str) -> list[dict[str, str]]:
    """Read specialist skill files for an employee.

    Skills live at .trinity/employees/{name}/skills/*.md. Each file becomes
    a skill with title = filename stem (spaces replace underscores) and
    body = file contents. Returns an empty list if no skills directory exists.
    """
    try:
        name = _validate_name(name)
    except ValueError:
        return []

    skills_dir = _employees_dir(trinity_dir) / name / "skills"
    if not skills_dir.is_dir():
        return []

    skills: list[dict[str, str]] = []
    for path in sorted(skills_dir.glob("*.md")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        title = path.stem.replace("_", " ").replace("-", " ").strip()
        skills.append({"title": title, "content": content})
    return skills


def remove_employee(trinity_dir: Path, name: str) -> bool:
    """Remove an employee directory and all its contents.

    Returns True if the employee was removed, False if it did not exist.
    """
    try:
        name = _validate_name(name)
    except ValueError:
        return False

    emp_dir = _employees_dir(trinity_dir) / name
    if not emp_dir.exists():
        return False

    shutil.rmtree(emp_dir)
    return True


def employee_exists(trinity_dir: Path, name: str) -> bool:
    """Check if an employee exists."""
    try:
        name = _validate_name(name)
    except ValueError:
        return False

    return (_employees_dir(trinity_dir) / name).is_dir()
