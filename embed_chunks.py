import json
from sentence_transformers import SentenceTransformer
import chromadb
import multiprocessing
import torch
import os
torch.set_num_threads(multiprocessing.cpu_count())

def main():

    model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "chroma_db")

    client = chromadb.PersistentClient(path=DB_PATH)
    print("Using ChromaDB at:", DB_PATH)
    collection = client.get_or_create_collection("linux_kernel")

    BATCH = 512

    docs = []
    metas = []
    ids = []

    count = 0
    workers = multiprocessing.cpu_count()

    with open("chunks.jsonl") as f:

        for line in f:

            data = json.loads(line)

            docs.append(data["code"])
            metas.append({
                "file": data["file"],
                "symbol": data["symbol"]
            })
            ids.append(str(count))

            count += 1

            if len(docs) == BATCH:

                embeddings = model.encode(
                    docs,
                    batch_size=64,
                    show_progress_bar=False
                )

                collection.add(
                    documents=docs,
                    embeddings=embeddings,
                    metadatas=metas,
                    ids=ids
                )

                docs, metas, ids = [], [], []

                print("embedded:", count)

    if docs:

        embeddings = model.encode(
            docs,
            batch_size=64,
            #num_workers=workers,
            show_progress_bar=False
        )

        collection.add(
            documents=docs,
            embeddings=embeddings,
            metadatas=metas,
            ids=ids
        )

    print("done:", count)


if __name__ == "__main__":
    main()