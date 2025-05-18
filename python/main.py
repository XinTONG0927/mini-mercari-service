import os
import logging
import pathlib
from fastapi import FastAPI, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pydantic import BaseModel
from contextlib import contextmanager, asynccontextmanager

#---newly added---
import hashlib
from typing import Optional, List
from fastapi.concurrency import run_in_threadpool


# Define the path to the images & sqlite3 database
images_dir = pathlib.Path(__file__).parent.resolve() / "images"
DB = pathlib.Path(__file__).parent.resolve() / "db" / "mercari.sqlite3"

@contextmanager
def get_db():
    if not DB.exists():
        sqlite3.connect(DB).close()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def safe_cursor(db: sqlite3.Connection):
    cursor = db.cursor()
    try:
        yield cursor

    except sqlite3.Error as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB Error: {str(e)}")
    finally:
        cursor.close()


# STEP 5-1: set up the database connection
def setup_database():
    sql_schema = pathlib.Path(__file__).parent.resolve() / "db" / "items.sql"
    with get_db() as db:
        with sql_schema.open("r") as f:
            schema = f.read()
        with safe_cursor(db) as cursor:
            cursor.execute(schema)
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_database()
    yield


app = FastAPI(lifespan=lifespan)

logger = logging.getLogger("uvicorn")
logger.level = logging.INFO
images_dir = pathlib.Path(__file__).parent.resolve() / "images"
origins = [os.environ.get("FRONT_URL", "http://localhost:3000")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


class HelloResponse(BaseModel):
    message: str

@app.get("/", response_model=HelloResponse)
def hello():
    return HelloResponse(**{"message": "Hello, world!"})


class AddItemResponse(BaseModel):
    message: str

# add_item is a handler to add a new item for POST /items .
@app.post("/items", response_model=AddItemResponse)
async def Add_item(
    name: str = Form(...),
    category: str = Form(...),
    image_file: UploadFile = File(None)
):
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    image_name = None
    if image_file is not None:
        # save img
        read = await image_file.read()
        image_name = hashlib.sha256(read).hexdigest()
        image_name = f"{image_name}.jpg"
        with (images_dir / image_name).open('wb') as f:
            f.write(read)

    insert_item(Item(name=name, category=category, image_name=image_name))

    return AddItemResponse(**{"message": f"item received: {name}"})




# get_image is a handler to return an image for GET /images/{filename} .
@app.get("/images/{image_name}")
async def get_image(image_name):
    # Create image path
    image = images_dir / image_name

    if not image_name.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.debug(f"Image not found: {image}")
        image = images_dir / "default.jpg"

    return FileResponse(image)


class Item(BaseModel):
    name: str
    category: str
    image_name: Optional[str] = None

# STEP 4-2: add an implementation to store an item
def insert_item(item: Item):
    table_name = "items"
    with get_db() as db:
        with safe_cursor(db) as cursor:
            cursor.execute(f"Insert into {table_name} (id, name, category, image_name) "
                                f"values (NULL, ?, ?, ?)", (item.name, item.category, item.image_name))
        db.commit()


class GetItemResponse(BaseModel):
    items: List[Item]

@app.get("/items", response_model=GetItemResponse)
def GetItems():
    table_name = "items"

    with get_db() as db:
        with safe_cursor(db) as cursor:
            cursor.execute(f"Select * from {table_name}")
            items = [dict(row) for row in cursor.fetchall()]

    return GetItemResponse(items=items)

@app.get("/search", response_model=GetItemResponse)
def Search_item(keyword: str):
    table_name = "items"

    with get_db() as db:
        with safe_cursor(db) as cursor:
            like_pattern = f"%{keyword}%"
            cursor.execute(f"SELECT * FROM {table_name} WHERE name LIKE ?", (like_pattern,))
            items = [dict(row) for row in cursor.fetchall()]

    return GetItemResponse(items=items)