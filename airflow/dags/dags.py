import uuid
import requests
import pymongo
import datetime as dt
from bs4 import BeautifulSoup
import json
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

def printCollections():
    client = QdrantClient(host="qdrant_db", port=6333)
    cls = client.get_collections()
    names = [c.name for c in cls.collections]
    if names:
        print("Collections: ", names)
    else:
        print("No collection in database")

def insertMongoDB(data):
    try:
        client = pymongo.MongoClient("mongodb://admin:admin@mongo_db:27017")
        db = client["fit-iuh"]
        news = db["news"]
        if news.find_one({"title": data['title']}):
            return 0
        _ = news.insert_one(data)
        return 1
    except Exception as e:
        return 0

def createCollection():
    client = QdrantClient(host="qdrant_db", port=6333)
    cls = client.get_collections()
    names = [c.name for c in cls.collections]
    if "fit-iuh-news" not in names:
        client.recreate_collection(
            collection_name="fit-iuh-news",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print("Create collection successfully")
    else:
        print("Collection already exists")

def getNew(element):
    try:
        a_tag = element.find('a')
        title = a_tag['title']
        href = a_tag['href']
        date = element.find(class_='content-date').text
        return {
            "title": title,
            "href": href,
            "date": dt.datetime.strptime(date.strip(), "%d-%m-%Y")
        }
    except:
        return {}

def getContentNews(url):
    url = "https://fit.iuh.edu.vn/"+url
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    content = soup.select(".left-content > .content-list")
    content = content[0].text
    return content

def findLatestTimeNews():
    client = pymongo.MongoClient("mongodb://admin:admin@mongo_db:27017")
    db = client["fit-iuh"]
    news = db["news"]
    latestNews = news.find().sort("date", -1).limit(1)
    latest_news_item = next(latestNews, None)
    if latest_news_item:
        return latest_news_item['date']
    return dt.datetime.now() + dt.timedelta(days=1)

def crawlData():
    fitUrl = "https://fit.iuh.edu.vn/"
    latestTimeNews = findLatestTimeNews()
    pageNum = range(2)
    count = 0
    for page in pageNum:
        response = requests.get(fitUrl+f"news.html@102@Tin-tuc-Su-kien@p={page}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            selectorContents = ".content-list > .content > [class*=content-info]"
            contents = soup.select(selectorContents)
            for content in contents:
                new = getNew(content)
                if new:
                    if new['date'] > latestTimeNews:
                        print(new)
                        return
                    count += insertMongoDB(new)
    if count:
        print(f"Insert {count} news successfully")
    else:
        print("No news to insert")

def updateNews():
    # find all news in database not have content
    client = pymongo.MongoClient("mongodb://admin:admin@mongo_db:27017")
    db = client["fit-iuh"]
    news = db["news"]
    newsNotHaveContent = news.find({"content": {"$exists": False}})
    for new in newsNotHaveContent:
        content = getContentNews(new['href'])
        news.update_one({"_id": new['_id']}, {"$set": {"content": content}})
    print("Update news successfully")

def insertVectorDB():
    qdrantClient = QdrantClient(host="qdrant_db", port=6333)
    mongoClient = pymongo.MongoClient("mongodb://admin:admin@mongo_db:27017")
    db = mongoClient["fit-iuh"]
    news = db["news"]
    allNews = news.find()

    # with open("/opt/airflow/dags/data_iuh_title.json", "r") as f:
    #     data = json.load(f)
    # db = mongoClient["fit-iuh"]
    # news = db["news"]
    # allNews = news.find()
    # for new in allNews:
    #     id = str(new.pop('_id'))
    #     if new['title'] in data:
    #         vector = data[new['title']]
    #         point = PointStruct(id=str(uuid.uuid4()),
    #                             vector=vector,
    #                             payload=new)
    #         qdrantClient.upsert(collection_name="fit-iuh-news", points=[point])
    
    for new in allNews:
        rep = requests.get(f'http://9net.ddns.net:9008/embedding?q='+new['title'])
        vector = rep.json()['embedding']
        id = str(new.pop('_id'))
        point = PointStruct(id=str(uuid.uuid4()),
                            vector=vector,
                            payload=new)
        qdrantClient.upsert(collection_name="fit-iuh-news", points=[point])

default_args = {
    'owner': 'admin',
    'start_date': dt.datetime.now(),
    'retries': 1,
    'retry_delay': dt.timedelta(minutes=2),
}


with DAG('NEWS-IUH',
         default_args=default_args,
         schedule_interval=dt.timedelta(minutes=5),      # '0 * * * *',
         ) as dag:

    create_collection = PythonOperator(task_id='create_collection_qdrant', python_callable=createCollection)
    crawl_data = PythonOperator(task_id='crawl_data', python_callable=crawlData)
    update_content = PythonOperator(task_id='update_news', python_callable=updateNews)
    insert_vector = PythonOperator(task_id='insert_vector', python_callable=insertVectorDB)
    end = BashOperator(task_id='end', bash_command='echo "Chương trình đã hoàn thành....."')

create_collection >> crawl_data >> update_content >> insert_vector >> end