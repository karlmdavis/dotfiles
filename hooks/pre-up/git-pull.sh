#!/bin/sh

cd ~/.dotfiles-karlmdavis.git

# Only pull if there are no local changes.
if git diff-index --quiet HEAD --; then
  git pull
else
  >&2 echo "Local ~/.dotfiles-karlmdavis.git repo not clean; won't pull."
fi

