import logging
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor, as_completed

from .eval import EvalError, eval_repo
from .manifest import Repo, load_manifest, update_lock_file
from .path import LOCK_PATH, MANIFEST_PATH
from .prefetch import prefetch

logger = logging.getLogger(__name__)


async def update(repo: Repo) -> Repo:
    repo, locked_version, repo_path = await prefetch(repo)

    if repo_path:
        eval_repo(repo, repo_path)

    repo.locked_version = locked_version
    return repo


async def update_command(args: Namespace) -> None:
    logging.basicConfig(level=logging.INFO)

    manifest = load_manifest(MANIFEST_PATH, LOCK_PATH)

    for repo in manifest.repos:
        try:
            await update(repo)
        except EvalError as err:
            if repo.locked_version is None:
                logger.error(
                    f"repository {repo.name} failed to evaluate: {err}. This repo is not yet in our lock file!!!!"
                )
                raise
            logger.error(f"repository {repo.name} failed to evaluate: {err}")
        except Exception:
            logger.exception(f"Failed to update repository {repo.name}")

    update_lock_file(manifest.repos, LOCK_PATH)
