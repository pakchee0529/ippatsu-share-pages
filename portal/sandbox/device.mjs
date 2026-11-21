const database = "ippatsu-sandbox";
const store = "author";

// A read/write transaction also serializes first use in two tabs.
export async function deviceCredential() {
  const db = await new Promise((resolve, reject) => {
    const request = indexedDB.open(database, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(store);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(store, "readwrite");
      const authors = tx.objectStore(store);
      const request = authors.get("device");
      let credential;
      request.onsuccess = () => {
        credential = request.result;
        if (!credential) {
          credential = Array.from(crypto.getRandomValues(new Uint8Array(32)),
            byte => byte.toString(16).padStart(2,"0")).join("");
          authors.add(credential, "device");
        }
      };
      tx.oncomplete = () => resolve(credential);
      tx.onabort = () => reject(tx.error || new Error("このブラウザに作者情報を保存できませんでした"));
    });
  } finally {
    db.close();
  }
}
