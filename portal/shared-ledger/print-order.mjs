import {photoGridHTML} from './photo-grid.mjs?v=20261028-design-normalize1';
import {partition} from './ledger-model.mjs?v=20261028-design-normalize1';
// Same subset selection, stable order and target used by adopted print model.partition.
export function printedPhotos(rows,target){if(target===null||!Number.isSafeInteger(target)||target<0)return {ordered:rows.map(x=>({...x})),exact:false};return partition(rows,target);}

export function printedPhotoGrid(rows,target,code){const result=printedPhotos(rows,target),multiple=['E10','N10'].includes(code);return {...result,html:photoGridHTML(result.ordered,{preserveOrder:true,groupByDate:false,showClaim:multiple?true:'added',showCount:multiple,showDate:multiple,showHeading:multiple})};}
