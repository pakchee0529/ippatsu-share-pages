// Published null is an explicit unknown, never inferred from a displayed zero.
export function compatiblePublishedBase(current,published){return Object.keys(published||{}).length===15&&Object.entries(published).every(([code,value])=>Object.hasOwn(current||{},code)&&(value===null?(current[code]===null||current[code]===0):Number.isSafeInteger(value)&&value>=0&&current[code]===value));}
export function publishedSource(source,entry){if(!compatiblePublishedBase(source?.planned,entry?.base))throw Error('現在の数量と公開原典の基準が一致しません');return {...source,planned:{...entry.base}};}
