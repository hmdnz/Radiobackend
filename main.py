from typing import Optional, List, Dict
from fastapi import FastAPI, Response, status, HTTPException
from pydantic import BaseModel
import asyncpg
from asyncpg import Connection
from fastapi.responses import JSONResponse
from asyncpg.pool import Pool

# Define your database URL with credentials (consider storing these securely)
DATABASE_URL = "postgresql://saas_db_owner:rqg5iT7spZcF@ep-solitary-silence-a2gwz340.eu-central-1.aws.neon.tech/saas_db?sslmode=require"

app = FastAPI()

# Define a global connection pool
pool: Pool = None

class Post(BaseModel):
    """
    This class defines the schema for user data.

    Attributes:
        name (str): The name of the user.
        email (str): The email address of the user.
        phone (str): The phone number of the user (optional).
        password (str): The user's password.
        picture (Optional[str]): A URL to the user's profile picture (optional).
        is_active (bool): A boolean indicating if the user is active (defaults to True).
    """
    name: str
    email: str
    phone: Optional[str] = None
    password: str
    picture: Optional[str] = None
    is_active: bool = True

async def get_db_connection() -> Connection:
    """
    Provides a database connection from the pool.

    Returns:
        Connection: A database connection object.
    """
    async with pool.acquire() as conn:
        yield conn

@app.on_event("startup")
async def startup():
    """
    Initializes the database connection pool at startup.
    """
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    
    print("DATABASE SUCCESSFULLY CONNECTED")

@app.on_event("shutdown")
async def shutdown():
    """
    Closes the database connection pool on shutdown.
    """
    await pool.close()
    print("DATABASE DISCONNECTED")


@app.get("/users", response_model=List[Dict])
async def get_users():
    """
    Fetches all user records from the database.

    Returns:
        List[Dict]: A list of dictionaries representing all user data.
    """
    async with pool.acquire() as conn:
        result = await conn.fetch("SELECT * FROM users")
    return [dict(record) for record in result]

@app.post("/users", status_code=status.HTTP_201_CREATED, response_model=Dict)
async def create_user(post: Post):
    """
    Creates a new user record in the database.

    Args:
        post (Post): An instance of the Post class containing user data.

    Returns:
        Dict: A dictionary representing the newly created user data.
    """
    async with pool.acquire() as conn:
        try:
            result = await conn.fetchrow(
                """INSERT INTO users (name, email, phone, password) VALUES ($1, $2, $3, $4) RETURNING *""",
                post.name, post.email, post.phone, post.password
            )
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
    return dict(result)

@app.get("/users/{user_id}", response_model=Dict)
async def get_user(user_id: int):
    """
    Fetches a specific user record based on its ID.

    Args:
        user_id (int): The ID of the user to retrieve.

    Returns:
        Dict: A dictionary representing the retrieved user data, or an HTTP 404 error if the user is not found.
    """
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id:{user_id} was not found")
    return dict(result)

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int):
    """
    Deletes a user record based on its ID.

    Args:
        user_id (int): The ID of the user to delete.

    Returns:
        Dict: A dictionary indicating the success of the deletion.
    """
    async with pool.acquire() as conn:
        try:
            await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")
    return {"message": "User successfully deleted"}

@app.put("/users/{user_id}", response_model=Dict)
async def update_user(user_id: int, post: Post):
    """
    Updates a user record based on its ID.

    Args:
        user_id (int): The ID of the user to update.
        post (Post): An instance of the Post class containing updated user data.

    Returns:
        Dict: A dictionary representing the updated user data.
    """
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            """UPDATE users SET name = $1, email = $2, phone = $3, password = $4 WHERE id = $5 RETURNING *""",
            post.name, post.email, post.phone, post.password, user_id
        )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id:{user_id} was not found")
    return dict(result)
