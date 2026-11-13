// Private candidate dispatcher. The unchanged normal module is loaded only on normal pages.
if(document.querySelector('#provisional-readonly-config')){
 await import('./views-readonly.mjs?v=20261110-transport-r1');
}else{
 await import('./views.mjs?v=20261110-transport-r1');
}
