from fastapi import FastAPI, HTTPException
from models import Task
from pydantic import BaseModel, Field, field_validator
from typing import Any
from models import engine
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
app = FastAPI()

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



@app.post("/add_task/", response_model=Task_response)
async def create_task(task:Task_definition):

    with Session(engine) as session:
        task_obj = Task(name=task.name,
                        task_description = task.task_description,
                        is_completed = task.is_completed 
                        )
        session.add(task_obj)
        session.commit()
        pydantic_response = Task_response.model_validate(
            task_obj
        )
    return pydantic_response

@app.get("/tasks/", response_model=list[Task_response])
async def home():

    with Session(engine) as session:
        statement = select(Task)
        task_obj = session.scalars(statement).all()

    return task_obj



@app.get("/tasks/{task_id}/", response_model=Task_response)
async def single_task(task_id:int):

    with Session(engine) as session:
        statement = select(Task).where(task_id == Task.id)
        single_task = session.scalars(statement).one_or_none()

        if single_task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        
    return single_task

@app.put("/edit_tasks/{task_id}", response_model=Task_response)
async def update_task(task_id:int, task_update:Task_definition):

    with Session(engine) as session:
        statement = update(Task).where(task_id == Task.id).values(name =task_update.name, task_description=task_update.task_description, is_completed = task_update.is_completed)
        session.execute(statement)
        session.commit()
        saved_update = select(Task).where(task_id == Task.id)
        updated = session.scalars(saved_update).one_or_none()

        if updated is None:
            raise HTTPException(status_code=404, detail="Not found")
    return updated


@app.delete("/delete_task/{task_id}")
async def delete_task(task_id:int):
    
    with Session(engine) as session:

        single_task_check = select(Task).where(task_id == Task.id)
        single_task = session.scalars(single_task_check).one_or_none()

        if single_task is None :
            raise HTTPException(status_code=404, detail="This id is invalid")
        
        statement = delete(Task).where(task_id == Task.id)
        session.execute(statement)
        session.commit()
        
    return {"Message" : "Task deleted successfully"}




