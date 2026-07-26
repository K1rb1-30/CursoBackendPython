from fastapi import FastAPI
from routers import products, users, jwt_auth_users, basic_auth_users, users_db
from fastapi.staticfiles import StaticFiles

app = FastAPI()

#url Local: http://127.0.0.1:8000

#Routers
app.include_router(products.router)
app.include_router(users.router)
app.include_router(jwt_auth_users.router)
app.include_router(basic_auth_users.router)
app.include_router(users_db.router)


#Archivos estaticos
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return "Hola FastAPI!"

#url Local: http://127.0.0.1:8000/url

@app.get("/url")
async def url():
    return {"url_curso":"https://mouredev.com/python"}

#Para iniciar el servidor: python -m uvicorn main:app --reload

#Documentacion de Swagger: http://127.0.0.1:8000/docs
#Documentacion de Redocly: http://127.0.0.1:8000/redoc