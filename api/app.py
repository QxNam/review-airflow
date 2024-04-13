import requests
import flask
from flask import request, make_response
from qdrant_client import QdrantClient

# url = "https://ee0b-34-86-136-68.ngrok-free.app"
# headers = {
#     "mssv": '20020541'
# }

# def get_embedding(text):
#     response = requests.post(url+"/embedding", json={"text": text}, headers=headers)
#     return response.json()['embedding']

# def complete(message, context):
#     response = requests.post(url+"/complete", json={"question": message, "context": context}, headers=headers)
#     return response.json()

app = flask.Flask(__name__)
url = "http://9net.ddns.net:9008/embedding?q="

def get_embedding(text):
    response = requests.get(url+text)
    return response.json()['embedding'] # 384

def complete(message, context):
    # response = requests.post(url+"/complete", json={"question": message, "context": context})
    # return response.json()
    return {"question": message, "context": context}

def search(query):
    client = QdrantClient(host='qdrant_db', port=6333)
    collections = client.get_collections()
    collectionNames = [collection.name for collection in collections.collections]
    embed = get_embedding(query)
    if 'fit-iuh-news' in collectionNames:
        results = client.search(collection_name="fit-iuh-news", query_vector=embed, limit=1)
        return results[0].model_dump()
    return {"message": "No collection in database"}

@app.route('/get_collections', methods=['GET'])
def get_collections():
    client = QdrantClient(host='qdrant_db', port=6333)
    collections = client.get_collections()
    collectionNames = [collection.name for collection in collections.collections]
    if collectionNames:
        return make_response({"collections": str(collectionNames)})
    return {"message": "No collections in database"}

@app.route('/search', methods=['POST'])
def searchView():
    query = request.json['query']
    results = search(query)
    return make_response(results)

@app.route('/complete', methods=['POST'])
def completeView():
    query = request.json['query']
    result = search(query)
    context = result['payload']['title']+'\n'+result['payload']['content']
    results = complete(query, context)
    print(results)
    return make_response(results)

@app.route('/', methods=['GET'])
def home():
    return {"message": "ok nhe"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)