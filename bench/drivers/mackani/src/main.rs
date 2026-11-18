use mackani::engine::{Engine, Sampling};
use mackani::real_engine::{RealEngine, RealEngineConfig};
use std::time::Instant;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let count: usize = args[3].parse().unwrap();
    let mut config = RealEngineConfig::default();
    config.model_dir = args[1].clone().into();
    let info = config.check(None).unwrap();
    let mut engine = RealEngine::load_checked(config, info, Default::default()).unwrap();
    let sampling = Sampling { temperature: 0.0, top_p: 0.95, top_k: 20, min_p: 0.0, seed: 0 };
    for task in &args[4..] {
        engine.reset().unwrap();
        let text = std::fs::read_to_string(format!("{}/{}.ids", args[2], task)).unwrap();
        let prompt: Vec<u32> = text.split_whitespace().map(|t| t.parse().unwrap()).collect();
        let started = Instant::now();
        let mut first = None;
        let generated = engine
            .generate(&prompt, count, &sampling, None, &mut |tokens| {
                if !tokens.is_empty() {
                    first.get_or_insert_with(Instant::now);
                }
                Ok(true)
            })
            .unwrap();
        let finished = Instant::now();
        let first = first.unwrap_or(finished);
        println!(
            "{{\"task\":\"{}\",\"prompt_tokens\":{},\"generated\":{},\"prefill_s\":{:.3},\"decode_s\":{:.3}}}",
            task,
            prompt.len(),
            generated.ids.len(),
            (first - started).as_secs_f64(),
            (finished - first).as_secs_f64()
        );
    }
}
