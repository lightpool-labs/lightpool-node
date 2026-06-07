use std::env;
use std::path::{Path, PathBuf};
use std::process::Command;

#[cfg(unix)]
use std::os::unix::process::CommandExt;

fn main() {
    let binary = resolve_lightpool_binary();

    if !binary.exists() {
        eprintln!(
            "lightpool binary not found at {}",
            binary.display()
        );
        eprintln!(
            "Place the prebuilt lightpool binary at bin/lightpool, or set LIGHTPOOL_BIN."
        );
        std::process::exit(1);
    }

    let args: Vec<String> = env::args().skip(1).collect();

    #[cfg(unix)]
    {
        let err = Command::new(&binary).args(&args).exec();
        eprintln!("failed to exec {}: {}", binary.display(), err);
        std::process::exit(1);
    }

    #[cfg(not(unix))]
    {
        let status = Command::new(&binary)
            .args(&args)
            .status()
            .unwrap_or_else(|err| {
                eprintln!("failed to run {}: {}", binary.display(), err);
                std::process::exit(1);
            });

        std::process::exit(status.code().unwrap_or(1));
    }
}

fn resolve_lightpool_binary() -> PathBuf {
    if let Ok(path) = env::var("LIGHTPOOL_BIN") {
        return PathBuf::from(path);
    }

    if let Ok(exe) = env::current_exe() {
        if let Some(dir) = exe.parent() {
            for candidate in candidate_paths(dir) {
                if candidate.exists() {
                    return candidate;
                }
            }
        }
    }

    PathBuf::from(env!("LIGHTPOOL_BIN_PATH"))
}

fn candidate_paths(exe_dir: &Path) -> [PathBuf; 3] {
    [
        exe_dir.join("lightpool-bin"),
        exe_dir.join("bin").join("lightpool"),
        exe_dir.join("../bin/lightpool"),
    ]
}
