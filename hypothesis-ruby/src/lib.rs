#[macro_use]
extern crate rutie;
#[macro_use]
extern crate lazy_static;
extern crate conjecture;

use std::mem;

use rutie::{AnyObject, Class, Integer, NilClass, Object, RString, VM};

use conjecture::engine::Engine;
use conjecture::data::{DataSource, Status, TestResult};
use conjecture::database::{BoxedDatabase, NoDatabase, DirectoryDatabase};
use conjecture::distributions;

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

methods!(
  HypothesisCoreDataSource,
  itself,

  fn ruby_hypothesis_core_data_source_start_draw() -> NilClass {
    itself.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER).start_draw();

    NilClass::new()
  }

  fn ruby_hypothesis_core_data_source_stop_draw() -> NilClass {
    itself.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER).stop_draw();

    NilClass::new()
  }
);

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

  fn finish_valid(&mut self, child: &mut HypothesisCoreDataSourceStruct) {
    mark_child_status(&mut self.engine, child, Status::Valid);
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
    match itself.get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER).new_source() {
      Some(ds) => Class::from_existing("HypothesisCoreDataSource").wrap_data(ds, &*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER),
      None => NilClass::new().into()
    }
  }

  fn ruby_hypothesis_core_engine_finish_valid(child: AnyObject) -> NilClass {
    let core_engine = itself.get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER);
    let mut rdata_source = child.unwrap();
    let data_source = rdata_source.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

    core_engine.finish_valid(data_source);

    NilClass::new()
  }
);

pub struct HypothesisCoreIntegersStruct {
  bitlengths: distributions::Sampler
}

impl HypothesisCoreIntegersStruct {
  fn new() -> HypothesisCoreIntegersStruct {
    return HypothesisCoreIntegersStruct { bitlengths: distributions::good_bitlengths() };
  }

  fn provide(&mut self, data: &mut HypothesisCoreDataSourceStruct) -> Option<i64> {
    data.source.as_mut().and_then(|ref mut source| {
      distributions::integer_from_bitlengths(source, &self.bitlengths).ok()
    })
  }
}

wrappable_struct!(HypothesisCoreIntegersStruct, HypothesisCoreIntegersStructWrapper, HYPOTHESIS_CORE_INTEGERS_STRUCT_WRAPPER);

class!(HypothesisCoreIntegers);

methods!(
  HypothesisCoreIntegers,
  itself,

  fn ruby_hypotheis_core_integers_new() -> AnyObject {
    let core_integers = HypothesisCoreIntegersStruct::new();

    Class::from_existing("HypothesisCoreIntegers").wrap_data(core_integers, &*HYPOTHESIS_CORE_INTEGERS_STRUCT_WRAPPER)
  }

  fn ruby_hypothesis_core_integers_provide(data: AnyObject) -> Integer {
    let core_integers = itself.get_data_mut(&*HYPOTHESIS_CORE_INTEGERS_STRUCT_WRAPPER);
    let mut rdata = data.unwrap();
    let data_source = rdata.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

     Integer::new(core_integers.provide(data_source).unwrap())
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
      klass.def("finish_valid", ruby_hypothesis_core_engine_finish_valid);
    });

    Class::new("HypothesisCoreDataSource", Some(&data_class)).define(|klass| {
      klass.def("start_draw", ruby_hypothesis_core_data_source_start_draw);
      klass.def("stop_draw", ruby_hypothesis_core_data_source_stop_draw);
    });

    Class::new("HypothesisCoreIntegers", Some(&data_class)).define(|klass| {
      klass.def_self("new", ruby_hypotheis_core_integers_new);
      klass.def("provide", ruby_hypothesis_core_integers_provide);
    });
}

fn mark_child_status(engine: &mut Engine, child: &mut HypothesisCoreDataSourceStruct, status: Status) {
  let mut replacement = None;
  mem::swap(&mut replacement, &mut child.source);

  match replacement {
      Some(source) => engine.mark_finished(source, status),
      None => (),
  }
}

