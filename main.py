from typing import List
import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# --- Config ---
# Use an explicit path for SQLite so permission issues are easier to diagnose.
DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# --- App & CORS ---
app = FastAPI(title="Task Manager")

# Path to frontend folder
filepath_fe_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Serve index.html at root
@app.get("/")
def home():
    return {"msg": "Task Manager Backend is running!"}

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB setup ---
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Models ---
class TaskDB(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(String, default="")
    completed = Column(Boolean, default=False)

# --- Pydantic schemas ---
class TaskBase(BaseModel):
    title: str
    description: str = ""
    completed: bool = False

class Task(TaskBase):
    id: int
    class Config:
        orm_mode = True

# Create tables on startup
@app.on_event("startup")
def on_startup():
    # ensure directory exists (only needed if using subfolders)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)

# --- Routes ---
@app.get("/")
def home():
    return {"msg": "Task Manager Backend is running!"}

@app.get("/tasks", response_model=List[Task])
def get_tasks(db: Session = Depends(get_db)):
    return db.query(TaskDB).all()

@app.post("/tasks", response_model=Task)
def create_task(task: TaskBase, db: Session = Depends(get_db)):
    new_task = TaskDB(**task.dict())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: TaskBase, db: Session = Depends(get_db)):
    db_task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in task.dict().items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()
    return {"msg": "Task deleted successfully"}
