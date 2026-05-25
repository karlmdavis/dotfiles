##
# local.nu — machine-LOCAL nushell config (PATH/env for tools not installed on every system).
#
# Created once by chezmoi (never overwritten); edit freely per machine. Sourced from config.nu, so
# `path add` (from `use std/util 'path add'`) is available. Put tools here that are NOT in
# .chezmoidata/system_packages_autoinstall.yaml. Examples (uncomment / adjust as needed):
#
# Do NOT delete this file: config.nu does `source local.nu`, which nushell resolves at parse time, so a
# missing local.nu breaks nushell startup. If it goes missing, run `chezmoi apply` to recreate it.
##


##
# SDKMAN (Java / Maven)
##

# nushell can't source sdkman-init.sh (no `sdk` command here); add the candidate bins directly.

# let sdkman_java = ($env.HOME | path join ".sdkman/candidates/java/current")
# if ($sdkman_java | path exists) {
#     $env.JAVA_HOME = $sdkman_java
#     path add ($sdkman_java | path join "bin")
# }
# let sdkman_maven = ($env.HOME | path join ".sdkman/candidates/maven/current")
# if ($sdkman_maven | path exists) { path add ($sdkman_maven | path join "bin") }


##
# Docker
##

# let docker_bin = ([$nu.home-path, '.docker', 'bin'] | path join)
# if ($docker_bin | path exists) { path add $docker_bin }


##
# GUI apps
##

# let obsidian_bin = '/Applications/Obsidian.app/Contents/MacOS'
# if ($obsidian_bin | path exists) { path add $obsidian_bin }
