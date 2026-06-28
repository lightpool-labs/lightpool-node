use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::SystemTime;

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;

fn main() {
    let manifest_dir = env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR");
    let manifest_path = Path::new(&manifest_dir);
    let bin_dir = manifest_path.join("bin");
    let node_binary_path = bin_dir.join("lightpool");
    let cli_binary_path = bin_dir.join("lightpool-cli");

    register_rerun_paths(&bin_dir);

    let profile = env::var("PROFILE").unwrap_or_default();
    if profile == "release" {
        if !node_binary_path.exists() {
            if let Err(err) = extract_binary_from_archive(
                &bin_dir,
                "lightpool-v",
                "lightpool",
                &node_binary_path,
            ) {
                println!("cargo:warning={err}");
            }
        }

        if !cli_binary_path.exists() {
            if let Err(err) = extract_binary_from_archive(
                &bin_dir,
                "lightpool-cli-v",
                "lightpool-cli",
                &cli_binary_path,
            ) {
                println!("cargo:warning={err}");
            }
        }
    }

    println!(
        "cargo:rustc-env=LIGHTPOOL_BIN_PATH={}",
        node_binary_path.display()
    );

    if !node_binary_path.exists() {
        println!(
            "cargo:warning=bin/lightpool not found; place lightpool-v*.tar.gz in bin/ and run cargo build --release"
        );
        return;
    }

    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("OUT_DIR"));
    let bundled_dest = out_dir.join("lightpool-bin");
    copy_binary(&node_binary_path, &bundled_dest);

    if let Some(profile_dir) = out_dir.ancestors().nth(3) {
        let profile_dest = profile_dir.join("lightpool-bin");
        copy_binary(&node_binary_path, &profile_dest);
    }
}

fn register_rerun_paths(bin_dir: &Path) {
    println!("cargo:rerun-if-changed=bin");
    println!("cargo:rerun-if-env-changed=PROFILE");

    let entries = match fs::read_dir(bin_dir) {
        Ok(entries) => entries,
        Err(_) => return,
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if is_release_archive(&path) {
            println!("cargo:rerun-if-changed={}", path.display());
        }
    }
}

fn is_release_archive(path: &Path) -> bool {
    path.file_name()
        .and_then(|name| name.to_str())
        .map(|name| {
            (name.starts_with("lightpool-v") || name.starts_with("lightpool-cli-v"))
                && name.ends_with(".tar.gz")
        })
        .unwrap_or(false)
}

fn extract_binary_from_archive(
    bin_dir: &Path,
    archive_prefix: &str,
    binary_name: &str,
    dest: &Path,
) -> Result<(), String> {
    let archive = find_newest_archive(bin_dir, archive_prefix)?;
    let tmp = env::temp_dir().join(format!(
        "lightpool-extract-{}-{}",
        binary_name,
        std::process::id()
    ));

    if tmp.exists() {
        fs::remove_dir_all(&tmp).map_err(|err| err.to_string())?;
    }
    fs::create_dir_all(&tmp).map_err(|err| err.to_string())?;

    let extract_result = (|| -> Result<(), String> {
        let status = Command::new("tar")
            .arg("-xzf")
            .arg(&archive)
            .arg("-C")
            .arg(&tmp)
            .status()
            .map_err(|err| format!("failed to run tar: {err}"))?;

        if !status.success() {
            return Err(format!("tar extraction failed for {}", archive.display()));
        }

        let extracted = find_named_binary(&tmp, binary_name)?;
        if let Some(parent) = dest.parent() {
            fs::create_dir_all(parent).map_err(|err| err.to_string())?;
        }
        fs::copy(&extracted, dest).map_err(|err| err.to_string())?;

        #[cfg(unix)]
        {
            let mut perms = fs::metadata(dest).map_err(|err| err.to_string())?.permissions();
            perms.set_mode(0o755);
            fs::set_permissions(dest, perms).map_err(|err| err.to_string())?;
        }

        println!(
            "cargo:warning=Extracted {} -> {}",
            archive.display(),
            dest.display()
        );
        Ok(())
    })();

    let _ = fs::remove_dir_all(&tmp);
    extract_result
}

fn find_newest_archive(bin_dir: &Path, prefix: &str) -> Result<PathBuf, String> {
    let mut archives: Vec<(SystemTime, PathBuf)> = fs::read_dir(bin_dir)
        .map_err(|err| err.to_string())?
        .filter_map(|entry| entry.ok())
        .map(|entry| entry.path())
        .filter(|path| {
            path.file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.starts_with(prefix) && name.ends_with(".tar.gz"))
        })
        .filter_map(|path| {
            let modified = fs::metadata(&path)
                .and_then(|metadata| metadata.modified())
                .unwrap_or(SystemTime::UNIX_EPOCH);
            Some((modified, path))
        })
        .collect();

    if archives.is_empty() {
        return Err(format!(
            "no {prefix}*.tar.gz found in {}",
            bin_dir.display()
        ));
    }

    archives.sort_by_key(|(modified, _)| *modified);
    Ok(archives.pop().expect("checked non-empty").1)
}

fn find_named_binary(root: &Path, binary_name: &str) -> Result<PathBuf, String> {
    fn walk(dir: &Path, binary_name: &str) -> Option<PathBuf> {
        let entries = fs::read_dir(dir).ok()?;
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                if path
                    .file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| name.starts_with('.'))
                {
                    continue;
                }
                if let Some(found) = walk(&path, binary_name) {
                    return Some(found);
                }
                continue;
            }

            if path.file_name().and_then(|name| name.to_str()) == Some(binary_name) {
                return Some(path);
            }
        }
        None
    }

    walk(root, binary_name)
        .ok_or_else(|| format!("{binary_name} binary not found inside archive"))
}

fn copy_binary(src: &Path, dest: &Path) {
    if let Some(parent) = dest.parent() {
        let _ = fs::create_dir_all(parent);
    }
    if fs::copy(src, dest).is_ok() {
        println!(
            "cargo:warning=Bundled lightpool binary to {}",
            dest.display()
        );
    }
}
