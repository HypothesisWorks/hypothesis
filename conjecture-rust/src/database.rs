use crypto_hash::{hex_digest, Algorithm};
use std::fmt::Debug;
use std::fs;
use std::io;
use std::io::prelude::*;
use std::path::{Path, PathBuf};

pub type Key = str;

pub trait Database: Debug + Send {
    fn save(&mut self, key: &Key, value: &[u8]);
    fn delete(&mut self, key: &Key, value: &[u8]);
    fn fetch(&mut self, key: &Key) -> Vec<Vec<u8>>;
}

pub type BoxedDatabase = Box<dyn Database>;

#[derive(Debug)]
pub struct NoDatabase;

impl Database for NoDatabase {
    fn save(&mut self, _key: &Key, _value: &[u8]) {}
    fn delete(&mut self, _key: &Key, _value: &[u8]) {}
    fn fetch(&mut self, _key: &Key) -> Vec<Vec<u8>> {
        vec![]
    }
}

#[derive(Debug)]
pub struct DirectoryDatabase {
    path: PathBuf,
}

fn expect_io_error(expected: io::ErrorKind, result: io::Result<()>) {
    match result {
        Ok(()) => (),
        Err(error) => {
            if error.kind() != expected {
                panic!("IO Error: {:?}", error.kind());
            }
        }
    }
}

impl DirectoryDatabase {
    pub fn new<P: AsRef<Path>>(path: P) -> DirectoryDatabase {
        let mut result = DirectoryDatabase {
            path: PathBuf::new(),
        };
        result.path.push(path);
        result
    }

    fn path_for_key(&self, key: &Key) -> PathBuf {
        let hashed_key = hex_digest(Algorithm::SHA1, key.as_bytes());
        let mut result = PathBuf::new();
        result.push(&self.path);
        result.push(&hashed_key[0..7]);
        expect_io_error(io::ErrorKind::AlreadyExists, fs::create_dir_all(&result));
        result
    }

    fn path_for_entry(&self, key: &Key, value: &[u8]) -> PathBuf {
        let mut result = self.path_for_key(key);
        result.push(&hex_digest(Algorithm::SHA1, value)[0..7]);
        result
    }
}

impl Database for DirectoryDatabase {
    fn save(&mut self, key: &Key, value: &[u8]) {
        let mut target = fs::File::create(self.path_for_entry(key, &value)).unwrap();
        target.write_all(value).unwrap();
        target.sync_all().unwrap();
    }

    fn delete(&mut self, key: &Key, value: &[u8]) {
        let target = self.path_for_entry(key, &value);
        expect_io_error(io::ErrorKind::NotFound, fs::remove_file(target));
    }

    fn fetch(&mut self, key: &Key) -> Vec<Vec<u8>> {
        let mut results = Vec::new();
        for entry_result in fs::read_dir(self.path_for_key(key)).unwrap() {
            let path = entry_result.unwrap().path();
            let file = fs::File::open(path).unwrap();
            let mut buf_reader = io::BufReader::new(file);
            let mut contents = Vec::new();
            buf_reader.read_to_end(&mut contents).unwrap();
            results.push(contents);
        }
        results
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[derive(Debug)]
    struct TestDatabase {
        _temp: TempDir,
        db: DirectoryDatabase,
    }

    impl TestDatabase {
        pub fn new() -> TestDatabase {
            let dir = TempDir::new().unwrap();
            let db = DirectoryDatabase::new(dir.path());
            TestDatabase { _temp: dir, db }
        }
    }

    impl Database for TestDatabase {
        fn save(&mut self, key: &Key, value: &[u8]) {
            self.db.save(key, value)
        }

        fn delete(&mut self, key: &Key, value: &[u8]) {
            self.db.delete(key, value)
        }

        fn fetch(&mut self, key: &Key) -> Vec<Vec<u8>> {
            self.db.fetch(key)
        }
    }

    #[test]
    fn can_delete_non_existing_key() {
        let mut db = TestDatabase::new();
        db.delete("foo", b"bar");
    }

    #[test]
    fn appears_in_listing_after_saving() {
        let mut db = TestDatabase::new();
        db.save("foo", b"bar");
        let results = db.fetch("foo");
        assert!(results.len() == 1);
        assert!(results[0].as_slice() == b"bar");
    }

    #[test]
    fn can_delete_key() {
        let mut db = TestDatabase::new();
        db.save("foo", b"bar");
        db.delete("foo", b"bar");
        let results = db.fetch("foo");
        assert!(results.is_empty());
    }
}
