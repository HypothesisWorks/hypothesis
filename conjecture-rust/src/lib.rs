#![allow(clippy::many_single_char_names)]
#![warn(clippy::cargo)]
extern crate byteorder;
extern crate core;
extern crate crypto_hash;
extern crate rand;

#[cfg(test)]
extern crate tempfile;

pub mod data;
pub mod database;
pub mod distributions;
pub mod engine;
pub mod intminimize;
