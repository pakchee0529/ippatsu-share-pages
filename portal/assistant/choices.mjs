export function numberedChoices(message=''){
  const rows=message.trim().split(/\r?\n/);
  const options=[];
  for(const line of rows){
    const match=line.trim().match(/^(\d{1,2})[.．、)）]\s*(\S.*)$/u);
    if(!match){if(options.length)break;continue;}
    if(Number(match[1])!==options.length+1)return [];
    options.push(match[2]);
  }
  return options.length>=2?options:[];
}

export function resolveChoice(reply,options){
  if(!options?.length)return null;
  const matches=reply.normalize('NFKC').trim().match(/^(前者|後者|最初|最後|[1-9]\d?(?:番目|番|つ目|個目))(?:の方)?(?:で(?:お願い|いい|ええ)?|にして|をお願い)?[。!！\s]*$/u);
  if(!matches)return null;
  const word=matches[1];
  const clarify={question:options.map((s,i)=>(i+1)+'．'+s).join('\n')+'\nどの候補にしますか？ 番号で選べます。'};
  if((word==='前者'||word==='後者')&&options.length!==2)return clarify;
  const index=word==='前者'||word==='最初'?0:word==='後者'||word==='最後'?options.length-1:parseInt(word,10)-1;
  return options[index]?{value:options[index]}:clarify;
}
