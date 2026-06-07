use std::env;
use std::fs;
use std::path::{Path, PathBuf};

fn main() {
    let manifest_dir = env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR");
    let binary_path = Path::new(&manifest_dir).join("bin/lightpool");

    println!("cargo:rerun-if-changed=bin/lightpool");
    println!(
        "cargo:rustc-env=LIGHTPOOL_BIN_PATH={}",
        binary_path.display()
    );

    if !binary_path.exists() {
        println!(
            "cargo:warning=bin/lightpool not found; build the launcher only and provide the binary before running"
        );
        return;
    }

    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("OUT_DIR"));
    let bundled_dest = out_dir.join("lightpool-bin");
    copy_binary(&binary_path, &bundled_dest);

    if let Some(profile_dir) = out_dir.ancestors().nth(3) {
        let profile_dest = profile_dir.join("lightpool-bin");
        copy_binary(&binary_path, &profile_dest);
    }
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
