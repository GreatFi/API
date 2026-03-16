from fastapi import FastAPI, HTTPException, Depends
from models import Task, User
from pydantic import BaseModel, Field, field_validator
from typing import Any, Annotated
from models import engine
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from datetime import datetime, timedelta, timezone
import jwt

SECRET_KEY = "18c099f815f6f5c9a811b3d1dae05929723603fe21ca3a297ba28b36ea35512a"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class Token(BaseModel):
    access_token : str
    token_type : str

class TokenData(BaseModel):
    username : str

app = FastAPI()

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class User_def(BaseModel):
    username : str= Field(max_length=30)
    password : str = Field(max_length=100)
    disabled: bool = Field(default=False)

    @field_validator('username', 'password', mode='before')
    @classmethod
    def ensure_input(cls, value:Any) -> Any:
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("This field is empty")
            else:
             
                return value
        return value
    
class User_res(BaseModel):
    id:int
    username : str
    password : str

    class Config:
        from_attributes = True

class Task_definition(BaseModel):
    name : str = Field(max_length=30, min_length=1)
    task_description : str = Field(max_length=500)
    is_completed : bool = Field(default=False)

    @field_validator('name', 'task_description',mode='before')
    @classmethod
    def ensure_input(cls, value:Any) -> Any:
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("This field must have values")
            else:
                return value
        else :
            return value
        
        

class Task_response(BaseModel):
    id:int
    name : str 
    task_description : str
    is_completed : bool

    class Config:
        from_attributes = True

async def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

@app.post("/create_account/", response_model=User_res)
async def create_user(user:User_def, db:Annotated[Session, Depends(get_db)]):

    hashed = password_hash.hash(user.password)
    user_obj = User(username= user.username,
                    password=hashed,
                    disabled = user.disabled
                    )
    db.add(user_obj)
    db.commit()
    py_response = User_res.model_validate(
        user_obj
    )
    return py_response

def verify_password(password, hashed):
    return password_hash.verify(password, hashed)

def get_user(db, username):
    statement = select(User).where(username == User.username)
    user_in_db = db.scalars(statement).first()

    return user_in_db

def authenticate_user(db, username:str, password:str):
    user = get_user(db, username)

    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


    
def create_access_token(data:dict, expires_delta:timedelta | None = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(db:Annotated[Session, Depends(get_db)], token:Annotated[str, Depends(oauth2_scheme)]):
    credential_exception = HTTPException(
        status_code=401,
        detail="Invalid credentials"
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise credential_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credential_exception
    user = get_user(db, username=token_data.username)

    if user is None:
        raise credential_exception
    return user

async def get_current_active_user(current_user:Annotated[User, Depends(get_current_user)]):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive User")
    return current_user

@app.post("/login/")
def login(form_data:Annotated[OAuth2PasswordRequestForm, Depends()], db:Annotated[Session, Depends(get_db)]) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect Username or Password",
            headers={"WWW-Authenticate":"Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data ={"sub":user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@app.get("/users/me/", response_model=User_res)
async def user(current_user:Annotated[User, Depends(get_current_active_user)]) -> User:
    return current_user

@app.post("/add_task/", response_model=Task_response)
async def create_task(task:Task_definition, db:Annotated[Session, Depends(get_db)], current_user:Annotated[User, Depends(get_current_active_user)]):
    
    task_obj = Task(name=task.name,
                    task_description = task.task_description,
                    is_completed = task.is_completed 
                    )
    db.add(task_obj)
    db.commit()
    pydantic_response = Task_response.model_validate(
        task_obj
    )
    return pydantic_response
@app.get("/tasks/", response_model=list[Task_response])
async def home(db:Annotated[Session, Depends(get_db)], current_user:Annotated[User, Depends(get_current_active_user)]):
    
    statement = select(Task)
    task_obj = db.scalars(statement).all()

    return task_obj



@app.get("/tasks/{task_id}/", response_model=Task_response)
async def single_task(task_id:int, db:Annotated[Session, Depends(get_db)], current_user:Annotated[User, Depends(get_current_active_user)]):

    statement = select(Task).where(task_id == Task.id)
    single_task = db.scalars(statement).one_or_none()

    if single_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return single_task

@app.put("/edit_tasks/{task_id}", response_model=Task_response)
async def update_task(task_id:int, task_update:Task_definition, db:Annotated[Session, Depends(get_db)], current_user:Annotated[User, Depends(get_current_active_user)]):

    statement = update(Task).where(task_id == Task.id).values(name =task_update.name, task_description=task_update.task_description, is_completed = task_update.is_completed)
    db.execute(statement)
    db.commit()
    saved_update = select(Task).where(task_id == Task.id)
    updated = db.scalars(saved_update).one_or_none()

    if updated is None:
        raise HTTPException(status_code=404, detail="Not found")
    return updated


@app.delete("/delete_task/{task_id}")
async def delete_task(task_id:int, db:Annotated[Session, Depends(get_db)], current_user:Annotated[User, Depends(get_current_active_user)]):


    single_task_check = select(Task).where(task_id == Task.id)
    single_task = db.scalars(single_task_check).one_or_none()

    if single_task is None :
        raise HTTPException(status_code=404, detail="This id is invalid")
    
    statement = delete(Task).where(task_id == Task.id)
    db.execute(statement)
    db.commit()
        
    return {"Message" : "Task deleted successfully"}




