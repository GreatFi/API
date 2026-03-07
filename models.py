from sqlalchemy import String, Boolean, Table, Column, MetaData, Integer, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import os
import dotenv

dotenv.load_dotenv()
engine = create_engine(os.environ.get("database_url"), echo=True)
metadata_obj = MetaData()


class Base(DeclarativeBase):
    pass


class Task(Base):

    __tablename__ = "Tasks"

    id:Mapped[int] = mapped_column(primary_key=True)
    name:Mapped[str] = mapped_column(String(30), nullable=False)
    task_description : Mapped[str] = mapped_column(String(500), nullable=False)
    is_completed : Mapped[bool] = mapped_column(Boolean, default=False)


metadata_obj.create_all(engine)