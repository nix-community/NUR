#!/usr/bin/env nix-shell
#!nix-shell -p git -p nix -p bash -i bash

set -eu -o pipefail # Exit with nonzero exit code if anything fails

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

source ${DIR}/lib/setup-git.sh
set -x


# build package.json for nur-search
# ---------------------------------

nix build "${DIR}#"

cd "${DIR}/.."

OUTPUT_FILE="nur-search/data/packages.json"
NEW_OUTPUT="$(mktemp)"
trap 'rm -f "${NEW_OUTPUT}"' EXIT

nix run "${DIR}#" -- index nur-combined > "${NEW_OUTPUT}"

# Check to make sure we haven't accidentally deleted a bunch of stuff
# Should prevent something like d9476003f9fb528d4e3a59c1455b97c2a3e11a8
OLD_SIZE=0
if [[ -f "${OUTPUT_FILE}" ]]; then
    OLD_SIZE="$(stat -c%s "${OUTPUT_FILE}")"
fi
NEW_SIZE="$(stat -c%s "${NEW_OUTPUT}")"
MIN_SIZE=$(( OLD_SIZE / 2 ))
if [[ "${NEW_SIZE}" -lt "${MIN_SIZE}" || "${NEW_SIZE}" -lt 1024 ]]; then
    echo "refusing to update ${OUTPUT_FILE}: new size (${NEW_SIZE} bytes) is far smaller than the previous size (${OLD_SIZE} bytes)" >&2
    exit 1
fi

mv "${NEW_OUTPUT}" "${OUTPUT_FILE}"

# rebuild and publish nur-search repository
# -----------------------------------------

cd nur-search
if [[ ! -z "$(git diff --exit-code)" ]]; then
    git add ./data/packages.json
    git commit -m "automatic update package.json"
else
    echo "nothings changed will not commit anything"
fi
