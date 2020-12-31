# only source this file
# to setup git to push and pull repositories via ssh
# ==================================================

# set up git and ssh
# ------------------
keys_dir=$(mktemp -d)
openssl aes-256-cbc \
        -K $encrypted_080f214a372c_key \
        -iv $encrypted_080f214a372c_iv \
        -in ci/keys.tar.gz.enc -out ci/keys.tar.gz -d
tar -C "$keys_dir" -xzvf ci/keys.tar.gz
eval "$(ssh-agent -s)"
chmod 600 "${keys_dir}/ssh-key"
ssh-add "${keys_dir}/ssh-key"
gpg --import "${keys_dir}/gpg-private-key"
rm -rf "$keys_dir"

export encrypted_080f214a372c_key= encrypted_080f214a372c_iv=

git config --global user.name "Nur a bot"
git config --global user.email "joerg.nur-bot@thalheim.io"
git config --global user.signingkey "B4E40EEC9053254E"
git config --global commit.gpgsign true
