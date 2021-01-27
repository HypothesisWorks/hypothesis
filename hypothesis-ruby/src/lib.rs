#[macro_use]
extern crate rutie;
#[macro_use]
extern crate lazy_static;
extern crate conjecture;

use std::convert::TryFrom;
use std::mem;

use rutie::{
    AnyException, AnyObject, Array, Boolean, Class, Exception, Float, Integer, NilClass, Object,
    RString, Symbol, VM,
};

use conjecture::data::{DataSource, Status, TestResult};
use conjecture::database::{BoxedDatabase, DirectoryDatabase, NoDatabase};
use conjecture::distributions;
use conjecture::distributions::Repeat;
use conjecture::engine::{Engine, Phase};

pub struct HypothesisCoreDataSourceStruct {
    source: Option<DataSource>,
}

impl HypothesisCoreDataSourceStruct {
    fn new(engine: &mut HypothesisCoreEngineStruct) -> HypothesisCoreDataSourceStruct {
        HypothesisCoreDataSourceStruct {
            source: mem::take(&mut engine.pending),
        }
    }

    fn start_draw(&mut self) {
        if let Some(ref mut source) = self.source {
            source.start_draw();
        }
    }

    fn stop_draw(&mut self) {
        if let Some(ref mut source) = self.source {
            source.stop_draw();
        }
    }
}

wrappable_struct!(
    HypothesisCoreDataSourceStruct,
    HypothesisCoreDataSourceStructWrapper,
    HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER
);

class!(HypothesisCoreDataSource);

#[rustfmt::skip]
methods!(
    HypothesisCoreDataSource,
    itself,
    fn ruby_hypothesis_core_data_source_start_draw() -> NilClass {
        itself
            .get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER)
            .start_draw();

        NilClass::new()
    }
    fn ruby_hypothesis_core_data_source_stop_draw() -> NilClass {
        itself
            .get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER)
            .stop_draw();

        NilClass::new()
    }
);

pub struct HypothesisCoreEngineStruct {
    engine: Engine,
    pending: Option<DataSource>,
    interesting_examples: Vec<TestResult>,
}

impl HypothesisCoreEngineStruct {
    fn new(
        name: String,
        database_path: Option<String>,
        seed: u64,
        max_examples: u64,
        phases: Vec<Phase>,
    ) -> HypothesisCoreEngineStruct {
        let xs: [u32; 2] = [seed as u32, (seed >> 32) as u32];
        let db: BoxedDatabase = match database_path {
            None => Box::new(NoDatabase),
            Some(path) => Box::new(DirectoryDatabase::new(path)),
        };

        HypothesisCoreEngineStruct {
            engine: Engine::new(name, max_examples, phases, &xs, db),
            pending: None,
            interesting_examples: Vec::new(),
        }
    }

    fn new_source(&mut self) -> Option<HypothesisCoreDataSourceStruct> {
        match self.engine.next_source() {
            None => {
                self.interesting_examples = self.engine.list_minimized_examples();
                None
            }
            Some(source) => {
                self.pending = Some(source);
                Some(HypothesisCoreDataSourceStruct::new(self))
            }
        }
    }

    fn count_failing_examples(&self) -> usize {
        self.interesting_examples.len()
    }

    fn failing_example(&mut self, i: usize) -> HypothesisCoreDataSourceStruct {
        self.pending = Some(DataSource::from_vec(
            self.interesting_examples[i].record.clone(),
        ));
        HypothesisCoreDataSourceStruct::new(self)
    }

    fn was_unsatisfiable(&mut self) -> bool {
        self.engine.was_unsatisfiable()
    }

    fn finish_overflow(&mut self, child: &mut HypothesisCoreDataSourceStruct) {
        mark_child_status(&mut self.engine, child, Status::Overflow);
    }

    fn finish_valid(&mut self, child: &mut HypothesisCoreDataSourceStruct) {
        mark_child_status(&mut self.engine, child, Status::Valid);
    }

    fn finish_invalid(&mut self, child: &mut HypothesisCoreDataSourceStruct) {
        mark_child_status(&mut self.engine, child, Status::Invalid);
    }

    fn finish_interesting(&mut self, child: &mut HypothesisCoreDataSourceStruct, label: u64) {
        mark_child_status(&mut self.engine, child, Status::Interesting(label));
    }
}

wrappable_struct!(
    HypothesisCoreEngineStruct,
    HypothesisCoreEngineStructWrapper,
    HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER
);

class!(HypothesisCoreEngine);

#[rustfmt::skip]
methods!(
    HypothesisCoreEngine,
    itself,
    fn ruby_hypothesis_core_engine_new(
        name: RString,
        database_path: RString,
        seed: Integer,
        max_example: Integer,
        phases: Array
    ) -> AnyObject {
        let rust_phases = safe_access(phases)
            .into_iter()
            .map(|ruby_phase| {
                let phase_sym = safe_access(ruby_phase.try_convert_to::<Symbol>());
                let phase = Phase::try_from(phase_sym.to_str())
                    .map_err(|e| AnyException::new("ArgumentError", Some(&e)));

                safe_access(phase)
            })
            .collect();

        let core_engine = HypothesisCoreEngineStruct::new(
            safe_access(name).to_string(),
            database_path.ok().map(|p| p.to_string()),
            safe_access(seed).to_u64(),
            safe_access(max_example).to_u64(),
            rust_phases,
        );

        Class::from_existing("HypothesisCoreEngine")
            .wrap_data(core_engine, &*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER)
    }
    fn ruby_hypothesis_core_engine_new_source() -> AnyObject {
        match itself
            .get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER)
            .new_source()
        {
            Some(ds) => Class::from_existing("HypothesisCoreDataSource")
                .wrap_data(ds, &*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER),
            None => NilClass::new().into(),
        }
    }
    fn ruby_hypothesis_core_engine_finish_overflow(child: AnyObject) -> NilClass {
        let core_engine = itself.get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER);
        let mut rdata_source = safe_access(child);
        let data_source = rdata_source.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

        core_engine.finish_overflow(data_source);

        NilClass::new()
    }
    fn ruby_hypothesis_core_engine_finish_valid(child: AnyObject) -> NilClass {
        let core_engine = itself.get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER);
        let mut rdata_source = safe_access(child);
        let data_source = rdata_source.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

        core_engine.finish_valid(data_source);

        NilClass::new()
    }
    fn ruby_hypothesis_core_engine_finish_invalid(child: AnyObject) -> NilClass {
        let core_engine = itself.get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER);
        let mut rdata_source = safe_access(child);
        let data_source = rdata_source.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

        core_engine.finish_invalid(data_source);

        NilClass::new()
    }
    fn ruby_hypothesis_core_engine_finish_interesting(
        child: AnyObject,
        label: Integer
    ) -> NilClass {
        let core_engine = itself.get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER);
        let mut rdata_source = safe_access(child);
        let data_source = rdata_source.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

        core_engine.finish_interesting(data_source, safe_access(label).to_u64());

        NilClass::new()
    }
    fn ruby_hypothesis_core_engine_count_failing_examples() -> Integer {
        let core_engine = itself.get_data(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER);

        Integer::new(core_engine.count_failing_examples() as i64)
    }
    fn ruby_hypothesis_core_failing_example(i: Integer) -> AnyObject {
        let core_engine = itself.get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER);
        let int = safe_access(i).to_u64() as usize;

        let data_source = core_engine.failing_example(int);

        Class::from_existing("HypothesisCoreDataSource")
            .wrap_data(data_source, &*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER)
    }
    fn ruby_hypothesis_core_engine_was_unsatisfiable() -> Boolean {
        let core_engine = itself.get_data_mut(&*HYPOTHESIS_CORE_ENGINE_STRUCT_WRAPPER);

        Boolean::new(core_engine.was_unsatisfiable())
    }
);

pub struct HypothesisCoreIntegersStruct {
    bitlengths: distributions::Sampler,
}

impl HypothesisCoreIntegersStruct {
    fn new() -> HypothesisCoreIntegersStruct {
        HypothesisCoreIntegersStruct {
            bitlengths: distributions::good_bitlengths(),
        }
    }

    fn provide(&mut self, data: &mut HypothesisCoreDataSourceStruct) -> Option<i64> {
        data.source.as_mut().and_then(|ref mut source| {
            distributions::integer_from_bitlengths(source, &self.bitlengths).ok()
        })
    }
}

wrappable_struct!(
    HypothesisCoreIntegersStruct,
    HypothesisCoreIntegersStructWrapper,
    HYPOTHESIS_CORE_INTEGERS_STRUCT_WRAPPER
);

class!(HypothesisCoreIntegers);

#[rustfmt::skip]
methods!(
    HypothesisCoreIntegers,
    itself,
    fn ruby_hypothesis_core_integers_new() -> AnyObject {
        let core_integers = HypothesisCoreIntegersStruct::new();

        Class::from_existing("HypothesisCoreIntegers")
            .wrap_data(core_integers, &*HYPOTHESIS_CORE_INTEGERS_STRUCT_WRAPPER)
    }
    fn ruby_hypothesis_core_integers_provide(data: AnyObject) -> AnyObject {
        let core_integers = itself.get_data_mut(&*HYPOTHESIS_CORE_INTEGERS_STRUCT_WRAPPER);
        let mut rdata = safe_access(data);
        let data_source = rdata.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

        match core_integers.provide(data_source) {
            Some(i) => Integer::new(i).into(),
            None => NilClass::new().into(),
        }
    }
);

pub struct HypothesisCoreRepeatValuesStruct {
    repeat: Repeat,
}

impl HypothesisCoreRepeatValuesStruct {
    fn new(
        min_count: u64,
        max_count: u64,
        expected_count: f64,
    ) -> HypothesisCoreRepeatValuesStruct {
        HypothesisCoreRepeatValuesStruct {
            repeat: Repeat::new(min_count, max_count, expected_count),
        }
    }

    fn _should_continue(&mut self, data: &mut HypothesisCoreDataSourceStruct) -> Option<bool> {
        return data
            .source
            .as_mut()
            .and_then(|ref mut source| self.repeat.should_continue(source).ok());
    }

    fn reject(&mut self) {
        self.repeat.reject();
    }
}

wrappable_struct!(
    HypothesisCoreRepeatValuesStruct,
    HypothesisCoreRepeatValuesStructWrapper,
    HYPOTHESIS_CORE_REPEAT_VALUES_STRUCT_WRAPPER
);

class!(HypothesisCoreRepeatValues);

#[rustfmt::skip]
methods!(
    HypothesisCoreRepeatValues,
    itself,
    fn ruby_hypothesis_core_repeat_values_new(
        min_count: Integer,
        max_count: Integer,
        expected_count: Float
    ) -> AnyObject {
        let repeat_values = HypothesisCoreRepeatValuesStruct::new(
            safe_access(min_count).to_u64(),
            safe_access(max_count).to_u64(),
            safe_access(expected_count).to_f64(),
        );

        Class::from_existing("HypothesisCoreRepeatValues").wrap_data(
            repeat_values,
            &*HYPOTHESIS_CORE_REPEAT_VALUES_STRUCT_WRAPPER,
        )
    }
    fn ruby_hypothesis_core_repeat_values_should_continue(data: AnyObject) -> AnyObject {
        let mut rdata = safe_access(data);
        let mut data_source = rdata.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);

        let should_continue = itself
            .get_data_mut(&*HYPOTHESIS_CORE_REPEAT_VALUES_STRUCT_WRAPPER)
            ._should_continue(data_source);

        match should_continue {
            Some(b) => Boolean::new(b).into(),
            None => NilClass::new().into(),
        }
    }
    fn ruby_hypothesis_core_repeat_values_reject() -> NilClass {
        let repeat_values = itself.get_data_mut(&*HYPOTHESIS_CORE_REPEAT_VALUES_STRUCT_WRAPPER);

        repeat_values.reject();

        NilClass::new()
    }
);

pub struct HypothesisCoreBoundedIntegersStruct {
    max_value: u64,
}

impl HypothesisCoreBoundedIntegersStruct {
    fn provide(&mut self, data: &mut HypothesisCoreDataSourceStruct) -> Option<u64> {
        data.source
            .as_mut()
            .and_then(|ref mut source| distributions::bounded_int(source, self.max_value).ok())
    }
}

wrappable_struct!(
    HypothesisCoreBoundedIntegersStruct,
    HypothesisCoreBoundedIntegersStructWrapper,
    HYPOTHESIS_CORE_BOUNDED_INTEGERS_STRUCT_WRAPPER
);

class!(HypothesisCoreBoundedIntegers);

#[rustfmt::skip]
methods!(
    HypothesisCoreBoundedIntegers,
    itself,
    fn ruby_hypothesis_core_bounded_integers_new(max_value: Integer) -> AnyObject {
        let bounded_integers = HypothesisCoreBoundedIntegersStruct {
            max_value: safe_access(max_value).to_u64(),
        };

        Class::from_existing("HypothesisCoreBoundedIntegers").wrap_data(
            bounded_integers,
            &*HYPOTHESIS_CORE_BOUNDED_INTEGERS_STRUCT_WRAPPER,
        )
    }
    fn ruby_hypothesis_core_bounded_integers_provide(data: AnyObject) -> AnyObject {
        let mut rdata = safe_access(data);
        let data_source = rdata.get_data_mut(&*HYPOTHESIS_CORE_DATA_SOURCE_STRUCT_WRAPPER);
        let bounded_integers =
            itself.get_data_mut(&*HYPOTHESIS_CORE_BOUNDED_INTEGERS_STRUCT_WRAPPER);

        match bounded_integers.provide(data_source) {
            Some(i) => Integer::from(i).into(),
            None => NilClass::new().into(),
        }
    }
);

#[allow(non_snake_case)]
#[no_mangle]
pub extern "C" fn Init_rutie_hypothesis_core() {
    Class::new("HypothesisCoreEngine", None).define(|klass| {
        klass.def_self("new", ruby_hypothesis_core_engine_new);
        klass.def("new_source", ruby_hypothesis_core_engine_new_source);
        klass.def(
            "count_failing_examples",
            ruby_hypothesis_core_engine_count_failing_examples,
        );
        klass.def("failing_example", ruby_hypothesis_core_failing_example);
        klass.def(
            "was_unsatisfiable",
            ruby_hypothesis_core_engine_was_unsatisfiable,
        );
        klass.def(
            "finish_overflow",
            ruby_hypothesis_core_engine_finish_overflow,
        );
        klass.def("finish_valid", ruby_hypothesis_core_engine_finish_valid);
        klass.def("finish_invalid", ruby_hypothesis_core_engine_finish_invalid);
        klass.def(
            "finish_interesting",
            ruby_hypothesis_core_engine_finish_interesting,
        );
    });

    Class::new("HypothesisCoreDataSource", None).define(|klass| {
        klass.def("start_draw", ruby_hypothesis_core_data_source_start_draw);
        klass.def("stop_draw", ruby_hypothesis_core_data_source_stop_draw);
    });

    Class::new("HypothesisCoreIntegers", None).define(|klass| {
        klass.def_self("new", ruby_hypothesis_core_integers_new);
        klass.def("provide", ruby_hypothesis_core_integers_provide);
    });

    Class::new("HypothesisCoreRepeatValues", None).define(|klass| {
        klass.def_self("new", ruby_hypothesis_core_repeat_values_new);
        klass.def(
            "_should_continue",
            ruby_hypothesis_core_repeat_values_should_continue,
        );
        klass.def("reject", ruby_hypothesis_core_repeat_values_reject);
    });

    Class::new("HypothesisCoreBoundedIntegers", None).define(|klass| {
        klass.def_self("new", ruby_hypothesis_core_bounded_integers_new);
        klass.def("provide", ruby_hypothesis_core_bounded_integers_provide);
    });
}

fn mark_child_status(
    engine: &mut Engine,
    child: &mut HypothesisCoreDataSourceStruct,
    status: Status,
) {
    if let Some(source) = mem::take(&mut child.source) {
        engine.mark_finished(source, status)
    }
}

fn safe_access<T>(value: Result<T, AnyException>) -> T {
    value.map_err(VM::raise_ex).unwrap()
}
