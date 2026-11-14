// Preserve the ordinary implementation for both adopted source and normal views.
if(document.body.dataset.sourceOnly==='true'){
 await import('./views.mjs?v=20261114-source-r3');
}else{
 await import('./views.mjs?v=20261110-transport-r1');
}
