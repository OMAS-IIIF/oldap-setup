"""Resolve unpublished core candidates offline with Poetry's normal solver.

Run with Python from a Poetry 2.x environment. Candidate wheel metadata and its
SHA-256 replace only oldaplib in the union of existing project locks. No package
index, editable source, local file dependency or private repository is added to
the resulting locks. Installation before publication requires this exact wheel
in a local wheelhouse; a normal index install cannot fetch an unpublished RC.
"""
import argparse
import hashlib
from pathlib import Path

from cleo.io.null_io import NullIO
from poetry.factory import Factory
from poetry.inspection.info import PackageInfo
from poetry.puzzle.solver import Solver
from poetry.repositories.repository import Repository
from poetry.repositories.repository_pool import RepositoryPool


def lock_candidates(library_wheel: Path, projects: list[Path]) -> None:
    """Resolve all projects before writing locks; refuse inconsistent candidates.

    Args:
        library_wheel: Built oldaplib wheel intended for this coordinated release.
        projects: Core project roots with existing Poetry locks.

    Raises:
        ValueError: Wrong wheel, version or non-registry dependency in the inputs.
        SolverProblemError: Existing locked packages cannot satisfy the candidates.
    """
    # Round-trip distribution metadata only: the local inspection path must not
    # become a file dependency in the portable registry lock.
    candidate = PackageInfo.load(PackageInfo.from_wheel(library_wheel).asdict()).to_package()
    if candidate.name != 'oldaplib' or candidate.source_type is not None:
        raise ValueError('Expected ordinary oldaplib wheel metadata')
    candidate.files = [{'file': library_wheel.name,
                        'hash': 'sha256:' + hashlib.sha256(library_wheel.read_bytes()).hexdigest()}]
    poetry_projects = [Factory().create_poetry(project) for project in projects]
    if not any(p.package.name == 'oldaplib' and p.package.version == candidate.version
               for p in poetry_projects):
        raise ValueError('Include the matching library project in the lock inputs')
    repository = Repository('locked-candidates')
    for poetry in poetry_projects:
        if poetry.package.version != candidate.version:
            raise ValueError('Core candidate versions must agree')
        for package in poetry.locker.locked_repository().packages:
            if package.name == 'oldaplib':
                continue
            if package.source_type is not None:
                raise ValueError('Only ordinary registry dependencies are supported')
            if not repository.has_package(package):
                repository.add_package(package)
    repository.add_package(candidate)
    pool = RepositoryPool([repository])
    results = []
    for poetry in poetry_projects:
        locked = [p for p in poetry.locker.locked_repository().packages if p.name != 'oldaplib']
        solver = Solver(poetry.package, pool, [], locked, NullIO())
        packages = solver.solve(use_latest=['oldaplib']).get_solved_packages()
        results.append((poetry, packages))
    for poetry, packages in results:
        poetry.locker.set_lock_data(poetry.package, packages)
        print(f'Locked {poetry.package.name} {poetry.package.version} offline')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library-wheel', type=Path, required=True)
    parser.add_argument('--project', type=Path, action='append', required=True)
    args = parser.parse_args()
    lock_candidates(args.library_wheel.resolve(), [p.resolve() for p in args.project])
