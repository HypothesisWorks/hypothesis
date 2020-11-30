#[macro_use]
extern crate rutie;
#[macro_use]
extern crate lazy_static;
extern crate conjecture;

use std::mem;

use rutie::{AnyObject, Boolean, Class, Float, Integer, NilClass, Object, RString, VM};

use conjecture::engine::Engine;
use conjecture::data::{DataSource, Status, TestResult};
use conjecture::database::{BoxedDatabase, NoDatabase, DirectoryDatabase};
use conjecture::distributions;
use conjecture::distributions::Repeat;

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

  fn finish_overflow(&mut self, child: &mut HypothesisCoreDataSourceStruct) {
    mark_child_status(&mut self.engine, child, Status::Overflow);
  }

  fn finish_valid(&mut self, child: &mut HypothesisCoreDataSourceStruct) {
    mark_child_status(&mut self.engine, child, Status::Valid);
  }

  fn finish_interesting(&mut self, child: &mut HypothesisCoreDataSourceStruct, label: u64) {
    mark_child_status(&mut self.engine, child, Status::Interesting(label));
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

  fn ruby_hypothesis_core_engine_finish_overflow(child: AnyObject) -> NilClass {
    let core_engine = itself.get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER);
    let mut rdata_source = child.unwrap();
    let data_source = rdata_source.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

    core_engine.finish_overflow(data_source);

    NilClass::new()
  }

  fn ruby_hypothesis_core_engine_finish_valid(child: AnyObject) -> NilClass {
    let core_engine = itself.get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER);
    let mut rdata_source = child.unwrap();
    let data_source = rdata_source.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

    core_engine.finish_valid(data_source);

    NilClass::new()
  }

  fn ruby_hypothesis_core_engine_finish_interesting(child: AnyObject, label: Integer) -> NilClass {
    let core_engine = itself.get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER);
    let mut rdata_source = child.unwrap();
    let data_source = rdata_source.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

    core_engine.finish_interesting(data_source, label.unwrap().to_u64());

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

  fn ruby_hypothesis_core_integers_provide(data: AnyObject) -> AnyObject {
    let core_integers = itself.get_data_mut(&*HYPOTHESIS_CORE_INTEGERS_STRUCT_WRAPPER);
    let mut rdata = data.unwrap();
    let data_source = rdata.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

    match core_integers.provide(data_source) {
      Some(i) => Integer::new(i).into(),
      None => NilClass::new().into()
    }
  }
);

pub struct HypothesisCoreRepeatValuesStruct {
  repeat: Repeat,
}

impl HypothesisCoreRepeatValuesStruct {
  fn new(min_count: u64, max_count: u64, expected_count: f64) -> HypothesisCoreRepeatValuesStruct {
    return HypothesisCoreRepeatValuesStruct {
      repeat: Repeat::new(min_count, max_count, expected_count)
    }
  }

  fn _should_continue(&mut self, data: &mut HypothesisCoreDataSourceStruct) -> Option<bool>{
    return data.source.as_mut().and_then(|ref mut source| {
      self.repeat.should_continue(source).ok()
    })
  }

  fn reject(&mut self) {
    self.repeat.reject();
  }
}

wrappable_struct!(HypothesisCoreRepeatValuesStruct, HypothesisCoreRepeatValuesStructWrapper, HYPOTHESIS_CORE_REPEAT_VALUES_STRUCT_WRAPPER);

class!(HypothesisCoreRepeatValues);

methods!(
  HypothesisCoreRepeatValues,
  itself,

  fn ruby_hypothesis_core_repeat_values_new(min_count: Integer, max_count: Integer, expected_count: Float) -> AnyObject {
    let repeat_values = HypothesisCoreRepeatValuesStruct::new(
      min_count.unwrap().to_u64(),
      max_count.unwrap().to_u64(),
      expected_count.unwrap().to_f64()
    );

    Class::from_existing("HypothesisCoreRepeatValues").wrap_data(repeat_values, &*HYPOTHESIS_CORE_REPEAT_VALUES_STRUCT_WRAPPER)
  }

  fn ruby_hypothesis_core_repeat_values_should_continue(data: AnyObject) -> AnyObject {
    let mut rdata = data.unwrap();
    let mut data_source = rdata.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

    let should_continue = itself
      .get_data_mut(&*HYPOTHESIS_CORE_REPEAT_VALUES_STRUCT_WRAPPER)
      ._should_continue(data_source);

    match should_continue {
      Some(b) => Boolean::new(b).into(),
      None => NilClass::new().into()
    }
  }
);

#[allow(non_snake_case)]
#[no_mangle]
pub extern "C" fn Init_rutie_hypothesis_core() {
    let data_class = Class::from_existing("Data");
    Class::new("HypothesisCoreEngine", Some(&data_class)).define(|klass| {
      klass.def_self("new", ruby_hypothesis_core_engine_new);
      klass.def("new_source", ruby_hypothesis_core_engine_new_source);
      klass.def("finish_overflow", ruby_hypothesis_core_engine_finish_overflow);
      klass.def("finish_valid", ruby_hypothesis_core_engine_finish_valid);
      klass.def("finish_interesting", ruby_hypothesis_core_engine_finish_interesting);
    });

    Class::new("HypothesisCoreDataSource", Some(&data_class)).define(|klass| {
      klass.def("start_draw", ruby_hypothesis_core_data_source_start_draw);
      klass.def("stop_draw", ruby_hypothesis_core_data_source_stop_draw);
    });

    Class::new("HypothesisCoreIntegers", Some(&data_class)).define(|klass| {
      klass.def_self("new", ruby_hypotheis_core_integers_new);
      klass.def("provide", ruby_hypothesis_core_integers_provide);
    });

    Class::new("HypothesisCoreRepeatValues", None).define(|klass| {
      klass.def_self("new", ruby_hypothesis_core_repeat_values_new);
      klass.def("_should_continue", ruby_hypothesis_core_repeat_values_should_continue);
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
