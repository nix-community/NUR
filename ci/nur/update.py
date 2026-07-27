import asyncio
import logging
from argparse import Namespace
from typing import List, Optional, Tuple

from .error import RepositoryDeletedError
from .eval import EvalError, eval_repo
from .manifest import LockedVersion, Repo, load_manifest, remove_repos, update_lock_file
from .path import LOCK_PATH, MANIFEST_PATH
from .prefetch import prefetcher_for

logger = logging.getLogger(__name__)


async def update(
    repo: Repo, do_evaluate: bool = False
) -> Tuple[Repo, Optional[EvalError]]:
    prefetcher = prefetcher_for(repo)

    latest_commit = await prefetcher.latest_commit()

    if repo.locked_version is not None and repo.locked_version.rev == latest_commit:
        return repo, None

    sha256, repo_path = await prefetcher.prefetch(latest_commit)

    eval_error: Optional[EvalError] = None
    if do_evaluate:
        try:
            await eval_repo(repo, repo_path)
        except EvalError as e:
            eval_error = e

    repo.locked_version = LockedVersion(
        repo.url, latest_commit, sha256, repo.submodules
    )
    return repo, eval_error


async def update_command(
    args: Namespace, do_evaluate: bool = False, hold_eval_fail: bool = False
) -> None:
    logging.basicConfig(level=logging.INFO)

    manifest = load_manifest(MANIFEST_PATH, LOCK_PATH)

    log_lock = asyncio.Lock()  # serialize success/error output

    results: List[Tuple[int, Optional[Repo], Optional[BaseException]]] = []

    async def run_one(
        i: int, repo: Repo, do_evaluate: bool = False, hold_eval_fail: bool = False
    ) -> None:
        try:
            updated, eval_error = await update(repo, do_evaluate)

            async with log_lock:
                if eval_error is not None:
                    if hold_eval_fail:
                        logger.error(
                            f"repository {repo.name} failed to evaluate: {eval_error}"
                        )
                        results.append((i, None, eval_error))
                    elif updated.locked_version is None:
                        logger.error(
                            f"repository {repo.name} failed to evaluate: {eval_error}. "
                            "It also failed to get a locked_version, but updating anyway."
                        )
                        results.append((i, updated, eval_error))
                    else:
                        logger.error(
                            f"repository {repo.name} failed to evaluate: {eval_error}. "
                            f"Locking it to {updated.locked_version.rev} anyway."
                        )
                        results.append((i, updated, None))
                elif updated.locked_version is not None:
                    logger.info(
                        f"Updated repository {repo.name} -> {updated.locked_version.rev}"
                    )
                    results.append((i, updated, None))
                else:
                    logger.info(
                        f"Updated repository {repo.name} but failed to get locked_version"
                    )
                    results.append((i, updated, None))
        except BaseException as e:
            results.append((i, None, e))

            async with log_lock:
                if isinstance(e, RepositoryDeletedError):
                    logger.warning(
                        f"repository {repo.name} appears to have been deleted "
                        "upstream; removing it from the repository list"
                    )
                else:
                    logger.exception(
                        f"Failed to update repository {repo.name}", exc_info=e
                    )

    tasks = [
        asyncio.create_task(run_one(i, repo, do_evaluate, hold_eval_fail))
        for i, repo in enumerate(manifest.repos)
    ]
    await asyncio.gather(*tasks)

    updated_repos: List[Repo] = []
    deleted_repos: List[Repo] = []

    for i, updated, err in sorted(results, key=lambda i: i[0]):
        if err is None and updated is not None:
            updated_repos.append(updated)
        elif isinstance(err, RepositoryDeletedError):
            deleted_repos.append(manifest.repos[i])
        else:
            updated_repos.append(manifest.repos[i])

    update_lock_file(updated_repos, LOCK_PATH)
    remove_repos(deleted_repos, MANIFEST_PATH)
