from fastapi import APIRouter, HTTPException, status
from db.models.user import User
from db.client import get_users_collection
from db.schemas.user import user_schema, users_schema
from bson import ObjectId

router = APIRouter(
    prefix="/userdb",
    tags=["userdb"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "No encontrado"}}
)

#Para iniciar el servidor: python -m uvicorn users_db:app --reload


users_list = []

@router.get("/", response_model=list[User])
async def users():
    users_collection = get_users_collection()
    return users_schema(users_collection.find())

#PATH
@router.get("/{id}")
async def user(id:str):
    return search_user("_id", ObjectId(id))

#Query
@router.get("/")
async def user(id:str):
   return search_user("_id", ObjectId(id))
    

#POST Agregar usuarios 
@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def user(user: User):
    users_collection = get_users_collection()

    if type(search_user("email", user.email)) == User:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario ya existe")
    
    user_dict = dict(user)
    del user_dict["id"]

    id = users_collection.insert_one(user_dict).inserted_id

    new_user = user_schema(users_collection.find_one({"_id": id}))

    return User(**new_user)

#PUT Actualizar usuarios
@router.put("/", response_model=User)
async def user(user: User):
    users_collection = get_users_collection()

    user_dict = dict(user)
    del user_dict["id"]
    try:
        users_collection.find_one_and_replace({"_id": ObjectId(user.id)}, user_dict)
    except:
        return {"error":"No se ha encontrado el usuario"}
    return search_user("_id", ObjectId(user.id))

#DELETE Eliminar usuarios
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def user(id: str):
    users_collection = get_users_collection()
    found = users_collection.find_one_and_delete({"_id": ObjectId(id)})
   
    if not found:
        return {"error":"No se ha eliminado el usuario"}

def search_user(field: str, key):
    try:
        users_collection = get_users_collection()
        user = users_collection.find_one({field: key})
        return User(**user_schema(user))
    except:
        return {"error": "No se ha encontrado el usuario"}