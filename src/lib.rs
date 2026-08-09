// Copyright (c) LightPool Labs
// Author: xiaoyu1998

//! Release helper crate for lightpool-node.
//!
//! `build.rs` extracts the prebuilt `lightpool` binary into `bin/` and writes
//! `env.sh` so `lightpool` (node + client subcommands) and `burst_client` are
//! on `PATH`.
