import {photoTargets} from './ledger-operations.mjs?v=20261031-009-position-r1';
import {photoGridHTML} from './photo-grid.mjs?v=20261031-009-position-r1';
import {partition} from './ledger-model.mjs?v=20261031-009-position-r1';
// Same subset selection, stable order and target used by adopted print model.partition.
export function printedPhotos(rows,target){if(target===null||!Number.isSafeInteger(target)||target<0)return {ordered:rows.map(x=>({...x})),exact:false};return partition(rows,target);}

export function printedPhotoGrid(rows,target,code,ui){let result=printedPhotos(rows,target);const targets=photoTargets(ui,code);if(targets&&Number.isSafeInteger(targets.original)&&targets.original>=0){const first=partition(rows,targets.original),original=first.ordered.filter(x=>x.claim==='PLANNED'),rest=first.ordered.filter(x=>x.claim==='ADDED'),second=partition(rest,targets.changed);result={exact:first.exact&&second.exact,ordered:[...original.map(x=>({...x,quantityGroup:'original'})),...second.ordered.map(x=>({...x,quantityGroup:x.claim==='PLANNED'?'changed':'added'}))]};}const unused=0,multiple=['E10','N10'].includes(code);return {...result,html:photoGridHTML(result.ordered,{preserveOrder:true,groupByDate:false,showClaim:multiple?true:'added',showCount:multiple,showDate:multiple,showHeading:multiple})};}
