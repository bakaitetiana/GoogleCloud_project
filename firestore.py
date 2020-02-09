from google.cloud import firestore
# [END bookshelf_firestore_client_import]


def document_to_dict(doc):
    if not doc.exists:
        return None
    doc_dict = doc.to_dict()
    doc_dict['id'] = doc.id
    return doc_dict


def next_page(limit=10, start_after=None):
    db = firestore.Client()

    query = db.collection(u'Image').limit(limit).order_by(u'title')

    if start_after:
        # Construct a new query starting at this document.
        query = query.start_after({u'title': start_after})

    docs = query.stream()
    docs = list(map(document_to_dict, docs))

    last_title = None
    if limit == len(docs):
        # Get the last document from the results and set as the last title.
        last_title = docs[-1][u'title']
    return docs, last_title


def read(image_id):
    # [START bookshelf_firestore_client]
    db = firestore.Client()
    image_ref = db.collection(u'Image').document(image_id)
    snapshot = image_ref.get()
    # [END bookshelf_firestore_client]
    return document_to_dict(snapshot)


def update(data, image_id=None):
    db = firestore.Client()
    image_ref = db.collection(u'Image').document(image_id)
    image_ref.set(data)
    return document_to_dict(image_ref.get())


create = update


def delete(id):
    db = firestore.Client()
    image_ref = db.collection(u'Image').document(id)
    image_ref.delete()
