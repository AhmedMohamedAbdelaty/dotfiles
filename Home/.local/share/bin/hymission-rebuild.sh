#!/usr/bin/env bash
set -euo pipefail

# This revision is verified against the official Hyprland 0.57.0 release.
revision=a022307005087f3f5ab2efd1ffba558304c08273
hypr_revision=0aa6745f705f2c4b0a5004eb019ef76e5bbdb426
source_dir="$HOME/.local/src/hymission"
build_dir="$HOME/.cache/hymission-build"

if ! Hyprland --version | head -n 1 | grep -Fq "$hypr_revision" ||
   ! grep -Fq "$hypr_revision" /usr/include/hyprland/src/version.h; then
    printf '%s\n' 'This pinned HyMission build requires the official Hyprland 0.57.0 binary and matching headers.' >&2
    printf '%s\n' 'Check upstream compatibility and update this recipe before rebuilding for a different version.' >&2
    exit 1
fi
if [[ ! -e "$source_dir" ]]; then
    mkdir -p "$(dirname "$source_dir")"
    git clone https://github.com/gfhdhytghd/hymission.git "$source_dir"
    git -C "$source_dir" checkout --detach "$revision"
fi
if [[ $(git -C "$source_dir" rev-parse HEAD) != "$revision" ]] ||
   [[ -n $(git -C "$source_dir" status --porcelain --untracked-files=no) ]]; then
    printf '%s\n' 'HyMission source differs from the verified revision or has local edits; leaving it untouched.' >&2
    exit 1
fi

cmake -S "$source_dir" -B "$build_dir" -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build "$build_dir" --target hymission hymission-search-input -j 2
mkdir -p "$HOME/.local/lib" "$HOME/.local/bin"
# Rename instead of overwriting an existing mapped shared library in place.
tmp_plugin=$(mktemp "$HOME/.local/lib/.hymission.XXXXXX")
tmp_helper=$(mktemp "$HOME/.local/bin/.hymission-search-input.XXXXXX")
trap 'rm -f "$tmp_plugin" "$tmp_helper"' EXIT
install -m 755 "$build_dir/libhymission.so" "$tmp_plugin"
install -m 755 "$build_dir/hymission-search-input" "$tmp_helper"
mv -f "$tmp_plugin" "$HOME/.local/lib/hymission.so"
mv -f "$tmp_helper" "$HOME/.local/bin/hymission-search-input"
printf '%s\n' 'Built HyMission. A new Hyprland session will load this build.'
