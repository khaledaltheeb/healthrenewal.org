import { env, pipeline } from '@huggingface/transformers';

const MODEL = 'Xenova/multilingual-e5-small';
const REVISION = '761b726dd34fb83930e26aab4e9ac3899aa1fa78';
const DIMENSIONS = 384;

function dot(left, right) {
  return left.reduce((sum, value, index) => sum + value * right[index], 0);
}

function validate(rows, runtime) {
  if (rows.length !== 3 || rows.some((row) => row.length !== DIMENSIONS)) {
    throw new Error(`${runtime}: unexpected embedding shape`);
  }
  for (const row of rows) {
    const norm = Math.sqrt(dot(row, row));
    if (Math.abs(norm - 1) > 0.015) {
      throw new Error(`${runtime}: embedding is not normalized: ${norm}`);
    }
  }
  const relevant = dot(rows[0], rows[1]);
  const unrelated = dot(rows[0], rows[2]);
  if (!(relevant > unrelated)) {
    throw new Error(`${runtime}: semantic ordering failed: relevant=${relevant}, unrelated=${unrelated}`);
  }
  return { runtime, model: MODEL, revision: REVISION, dimensions: DIMENSIONS, relevant, unrelated };
}

env.allowLocalModels = false;
env.cacheDir = `${process.env.HOME}/.cache/transformers-js`;

const extractor = await pipeline('feature-extraction', MODEL, {
  revision: REVISION,
  dtype: 'q8',
  device: 'cpu',
});
const output = await extractor([
  'query: طرق دعم اضطراب طيف التوحد',
  'passage: تشمل خطط دعم اضطراب طيف التوحد التواصل الواضح والتدخل المبكر ودعم الأسرة.',
  'passage: تتغير درجات الحرارة بين الفصول وتختلف كميات الأمطار من منطقة إلى أخرى.',
], { pooling: 'mean', normalize: true });

console.log(JSON.stringify(validate(output.tolist(), 'node-cpu')));
