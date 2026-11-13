if(document.querySelector('#weekly-source-config')){
 await import('./views-readonly.mjs?v=20261113-weekly-source-r1');
}else if(document.querySelector('#provisional-readonly-config')){
 throw Error('Retired provisional format; regenerate from the pinned public source');
}else{
 await import('./views.mjs?v=20261110-transport-r1');
}
