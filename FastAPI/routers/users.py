from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(
    prefix="/user",
    tags=["user"],
    responses={404: {"message": "No encontrado"}}
)

#Para iniciar el servidor: python -m uvicorn users:app --reload

#Entidad User

class User(BaseModel):
    id: int
    name: str
    surname: str
    url: str
    age: int

users_list = [
    User(id=1,name="Gabriel",surname="Sanchez",url="miportfolio.com",age=18),
    User(id=2,name="Pepito",surname="So",url="pepi.com",age=24),
    User(id=3,name="Al",surname="Sanchez",url="sisisi.com",age=30)
]

@router.get("/usersjson")
async def usersjson():
    return [
        {"name":"Gabriel","surname":"Sanchez","url":"miportfolio.com","age":18},
        {"name":"Pepito","surname":"So","url":"pepi.com","age":24},
        {"name":"Al","surname":"Sanchez","url":"sisisi.com","age":30}
    ]

@router.get("/")
async def users():
    return users_list

#PATH
@router.get("/{id}")
async def user(id:int):
    return search_user(id)

#Query
@router.get("/")
async def user(id:int):
   return search_user(id)
    
def search_user(id:int):
    user = filter(lambda user: user.id == id, users_list)
    try:
        return list(user)[0]
    except:
        return {"error":"No se ha encontrado el usuario"}

#POST Agregar usuarios 
@router.post("/", response_model=User, status_code=201)
async def user(user: User):
    if type(search_user(user.id)) == User:
        raise HTTPException(status_code=404, detail="El usuario ya existe")
    else:
        users_list.append(user)
        return user

#PUT Actualizar usuarios
@router.put("/")
async def user(user: User):
    found = False
    for index, saved_user in enumerate(users_list):
        if saved_user.id == user.id:
            users_list[index] = user
            found = True
    if not found:
        return {"error":"No se ha encontrado el usuario"}
    else:
        return user

#DELETE Eliminar usuarios
@router.delete("/{id}")
async def user(id: int):
    found = False
    for index, saved_user in enumerate(users_list):
        if saved_user.id == id:
            del users_list[index]
            found = True
    if not found:
        return {"error":"No se ha eliminado el usuario"}
    else:
        return {"message":"Usuario eliminado"}