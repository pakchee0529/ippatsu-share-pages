const node=document.querySelector('#shared-ledger-config');if(!node)throw Error('共有台帳の生成設定がありません');export const config=JSON.parse(node.textContent);
