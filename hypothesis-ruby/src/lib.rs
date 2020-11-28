#[macro_use]
extern crate rutie;
#[macro_use]
extern crate lazy_static;
extern crate conjecture;

use std::mem;

use rutie::{AnyObject, Class, Integer, NilClass, Object, RString, VM};

use conjecture::data::{DataSource, Status, TestResult};
use conjecture::engine::Engine;
use conjecture::database::{BoxedDatabase, NoDatabase, DirectoryDatabase};

class!(RutieExample);

methods!(
    RutieExample,
    _rtself,

    fn pub_reverse(input: RString) -> RString {
        let ruby_string = input.
          map_err(|e| VM::raise_ex(e) ).
          unwrap();

        RString::new_utf8(
          &ruby_string.
          to_string().
          chars().
          rev().
          collect::<String>()
        )
    }
);

pub struct HypothesisCoreDataSourceStruct {
  source: Option<DataSource>,
}

impl HypothesisCoreDataSourceStruct {
  fn new(engine: &mut HypothesisCoreEngineStruct) -> HypothesisCoreDataSourceStruct {
    let mut result = HypothesisCoreDataSourceStruct{ source: None};
    mem::swap(&mut result.source, &mut engine.pending);
    return result;
  }

  fn start_draw(&mut self) {
    if let &mut Some(ref mut source) = &mut self.source {
      source.start_draw();
    }
  }

  fn stop_draw(&mut self) {
    if let &mut Some(ref mut source) = &mut self.source {
      source.stop_draw();
    }
  }
}

wrappable_struct!(HypothesisCoreDataSourceStruct, HypothesisCoreDataSourceStructWrapper, HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

class!(HypothesisCoreDataSource);

// methods!(
//   HypothesisCoreDataSource,
//   itself,

//   fn ruby_hypothesis_core_data_source_new(engine: AnyObject) -> Integer {
//   //  let data_source = HypothesisCoreDataSourceStruct::new(engine.unwrap());
//     Integer::new(5)

// //    Class::from_existing("HypothesisCoreDataSource").wrap_data(data_source, &*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER)
//   }
// );

pub struct HypothesisCoreEngineStruct {
  engine: Engine,
  pending: Option<DataSource>,
  interesting_examples: Vec<TestResult>,
}

impl HypothesisCoreEngineStruct {
  fn new(name: String, database_path: Option<String>, seed: u64, max_examples: u64) -> HypothesisCoreEngineStruct {
    let xs: [u32; 2] = [seed as u32, (seed >> 32) as u32];
    let db: BoxedDatabase = match database_path {
      None => Box::new(NoDatabase),
      Some(path) => Box::new(DirectoryDatabase::new(path)),
    };

    HypothesisCoreEngineStruct {
      engine: Engine::new(name, max_examples, &xs, db),
      pending: None,
      interesting_examples: Vec::new(),
    }
  }

  fn new_source(&mut self) -> Option<HypothesisCoreDataSourceStruct> {
    match self.engine.next_source() {
      None => {
        self.interesting_examples = self.engine.list_minimized_examples();
        None
      },
      Some(source) => {
        self.pending = Some(source);
        Some(HypothesisCoreDataSourceStruct::new(self))
      },
    }
  }
}

wrappable_struct!(HypothesisCoreEngineStruct, HypothesisCoreEngineStructWrapper, HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER);

class!(HypothesisCoreEngine);

methods!(
  HypothesisCoreEngine,
  itself,

  fn ruby_hypothesis_core_engine_new(name: RString, database_path: RString, seed: Integer, max_example: Integer) -> AnyObject {
    let core_engine = HypothesisCoreEngineStruct::new(
      name.unwrap().to_string(),
      Some(database_path.unwrap().to_string()),
      seed.unwrap().to_u64(),
      max_example.unwrap().to_u64()
    );

    Class::from_existing("HypothesisCoreEngine").wrap_data(core_engine, &*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER)
  }

  fn ruby_hypothesis_core_engine_new_source() -> AnyObject {
    let source = itself.get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER).new_source().unwrap();

    Class::from_existing("HypothesisCoreDataSource").wrap_data(source, &*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER)
  }
);

#[allow(non_snake_case)]
#[no_mangle]
pub extern "C" fn Init_rutie_ruby_example() {
    Class::new("RutieExample", None).define(|klass| {
        klass.def_self("reverse", pub_reverse);
    });

    let data_class = Class::from_existing("Data");
    Class::new("HypothesisCoreEngine", Some(&data_class)).define(|klass| {
      klass.def_self("new", ruby_hypothesis_core_engine_new);
      klass.def("new_source", ruby_hypothesis_core_engine_new_source);
    });

    Class::new("HypothesisCoreDataSource", None);
}
