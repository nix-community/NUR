import logging
import asyncio
from typing import List
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor, as_completed

from .eval import EvalError, eval_repo
from .manifest import Repo, LockedVersion, load_manifest, update_lock_file
from .path import LOCK_PATH, MANIFEST_PATH
from .prefetch import prefetcher_for

logger = logging.getLogger(__name__)


async def update(repo: Repo) -> Repo:
    prefetcher = prefetcher_for(repo)

    latest_commit = await prefetcher.latest_commit()

    if repo.locked_version is not None and repo.locked_version.rev == latest_commit:
        return repo

    sha256, repo_path = await prefetcher.prefetch(latest_commit)
    await eval_repo(repo, repo_path)
    repo.locked_version = LockedVersion(repo.url, latest_commit, sha256, repo.submodules)
    return repo


async def update_command(args: Namespace) -> None:
    logging.basicConfig(level=logging.INFO)

    manifest = load_manifest(MANIFEST_PATH, LOCK_PATH)

    log_lock = asyncio.Lock()   # serialize success/error output

    results: List[Tuple[int, Optional[Repo], Optional[BaseException]]] = []

    async def run_one(i: int, repo: Repo) -> None:
        try:
            updated = await update(repo)

            results.append((i, updated, None))

            async with log_lock:
                if updated.locked_version is not None:
                    logger.info(f"Updated repository {repo.name} -> {updated.locked_version.rev}")
                else:
                    logger.info(f"Updated repository {repo.name}")
        except BaseException as e:
            results.append((i, None, e))

            async with log_lock:
                if isinstance(e, EvalError) and repo.locked_version is None:
                    logger.error(
                        f"repository {repo.name} failed to evaluate: {e}. "
                        "This repo is not yet in our lock file!!!!"
                    )
                elif isinstance(e, EvalError):
                    logger.error(f"repository {repo.name} failed to evaluate: {e}")
                else:
                    logger.exception(f"Failed to update repository {repo.name}", exc_info=e)

    tasks = [asyncio.create_task(run_one(i, repo)) for i, repo in enumerate(manifest.repos)]
    await asyncio.gather(*tasks)

    updated_repos: List[Repo] = list(manifest.repos)

    for i, updated, err in results:
        if err is None and updated is not None:
            updated_repos[i] = updated

    update_lock_file(updated_repos, LOCK_PATH)
