# only source this file
# to load functions that help with travis.ci
# ==========================================


is-automatic-update() {
    [[ "$TRAVIS_EVENT_TYPE" == "cron" ]] || [[ "$TRAVIS_EVENT_TYPE" == "api" ]]
}

is-pull-request(){
    [[ "$TRAVIS_PULL_REQUEST" != "false" ]]
}

is-not-pull-request(){
    [[ "$TRAVIS_PULL_REQUEST" = "false" ]]
}

dont-continue-on-pull-requests() {
    if is-pull-request
    then
        echo "stopping because this is a pull request"
        exit 0
    fi
}

only-continue-on-pull-requests() {
    if is-not-pull-request
    then
        echo "stopping because this is not a pull request"
        exit 0
    fi
}
