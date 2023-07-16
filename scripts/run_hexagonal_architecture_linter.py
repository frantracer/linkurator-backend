import argparse
import glob
import sys
from typing import List


class ProjectDependency:
    project: str
    bounding_context: str
    layer: str
    name: str

    def __init__(self, module_dir: str) -> None:
        """Initialize project dependency."""
        module_split = module_dir.split(".")

        self.project = module_split[0]
        self.bounding_context = module_split[1] if len(module_split) > 1 else ""
        self.layer = module_split[2] if len(module_split) > 2 else ""
        self.name = ".".join(module_split[3:]) if len(module_split) > 3 else ""


def _dependencies(python_file: str) -> List[str]:
    """Return dependencies of a python file."""
    dependencies: List[str] = []
    with open(python_file, "r", encoding="utf-8") as file:
        for line in file:
            if line.startswith("from"):
                dependency = line.split("from ")[1].split(" import")[0]
                dependencies.append(dependency)
            if line.startswith("import"):
                dependency = line.split("import ")[1].split(" ")[0]
                dependencies.append(dependency)
    return dependencies


class HexagonalArchitectureLinter:
    """Linter to check hexagonal architecture rules."""

    def __init__(self, directory: str, common_folder: str) -> None:
        """Initialize linter to check hexagonal architecture rules."""
        self.directory = directory
        self.common_folder = common_folder
        self.project_name = self.directory.split("/")[-1]

    def run(self) -> int:
        """Run linter to check hexagonal architecture rules."""
        print(f"Running linter to check hexagonal architecture rules in {self.directory}")
        python_files: List[str] = glob.glob(f"{self.directory}/*/**/*.py", recursive=True)
        error_found = False

        for python_file in python_files:
            basename = python_file.split("/")[-1]
            if basename == "__init__.py":
                continue

            current_bounding_context = python_file.split("/")[2]
            current_layer = python_file.split("/")[3]

            raw_dependencies = _dependencies(python_file)
            for raw_dependency in raw_dependencies:
                dependency = ProjectDependency(raw_dependency)
                if dependency.project != self.project_name:
                    continue
                if dependency.bounding_context not in (current_bounding_context, self.common_folder):
                    print(f"ERROR: {python_file} depends on {raw_dependency} from another bounding context")
                    error_found = True
                if current_layer == "domain" and dependency.layer != "domain":
                    print(f"ERROR: {python_file} depends on {raw_dependency} from another layer")
                    error_found = True
                if current_layer == "application" and dependency.layer not in ["domain", "application"]:
                    print(f"ERROR: {python_file} depends on {raw_dependency} from another layer")
                    error_found = True
                if current_layer == "infrastructure" and dependency.layer not in ["domain", "application",
                                                                                  "infrastructure"]:
                    print(f"ERROR: {python_file} depends on {raw_dependency} from another layer")
                    error_found = True

        return 1 if error_found else 0


def main() -> int:
    """Run linter to check hexagonal architecture rules."""
    parser = argparse.ArgumentParser(
        description="Run linter to check hexagonal architecture rules."
    )
    parser.add_argument("--directory", type=str, help="Directory to check", required=True)
    parser.add_argument("--common-folder", type=str, help="Common folder", default="common")
    args = parser.parse_args()

    linter = HexagonalArchitectureLinter(directory=args.directory, common_folder=args.common_folder)
    return linter.run()


if __name__ == "__main__":
    sys.exit(main())
