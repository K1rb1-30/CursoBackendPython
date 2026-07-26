# routers/jwt_auth_users.py

from datetime import datetime, timedelta, timezone

# PyJWT: librería oficial recomendada para JWT en Python
import jwt
from jwt.exceptions import InvalidTokenError

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

# pwdlib: librería moderna para hashing de contraseñas
# PasswordHash es el objeto principal que usaremos
from pwdlib import PasswordHash

# ------------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------------

# Algoritmo de firma del token JWT.
# HS256 = HMAC con SHA-256: rápido, simétrico (misma clave para firmar y verificar).
# Para APIs públicas con múltiples servicios se usaría RS256 (asimétrico),
# pero para una API propia HS256 es la elección correcta.
ALGORITHM = "HS256"

# Tiempo de vida del token en minutos.
# 30 minutos es un balance razonable entre seguridad y comodidad.
# Tokens muy largos = más tiempo de exposición si son robados.
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Clave secreta para firmar los tokens.
# ⚠️ NUNCA la hardcodees en producción: usa variables de entorno.
# Para generar una nueva clave segura ejecuta en terminal(git bash):
#   openssl rand -hex 32
import os
from dotenv import load_dotenv

load_dotenv()

SECRET = os.getenv("SECRET_KEY")

# ------------------------------------------------------------------
# ROUTER
# ------------------------------------------------------------------
# Todas las rutas de este módulo tendrán el prefijo /jwtauth
router = APIRouter(
    prefix="/jwtauth",
    tags=["jwtauth"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "No encontrado"}}
)

# ------------------------------------------------------------------
# ESQUEMA OAuth2
# ------------------------------------------------------------------
# OAuth2PasswordBearer tiene dos responsabilidades:
#
# 1. EN TIEMPO DE DOCUMENTACIÓN:
#    tokenUrl le dice a FastAPI dónde está el endpoint de login.
#    Esto es metadata para /docs: hace aparecer el botón "Authorize"
#    y permite probar endpoints protegidos directamente desde el navegador.
#
# 2. EN TIEMPO DE EJECUCIÓN (la responsabilidad real):
#    Actúa como dependencia inyectable. Cuando un endpoint la usa
#    con Depends(oauth2), extrae automáticamente el token del header:
#        Authorization: Bearer eyJhbGci...
#    y lo pasa como string a la función que lo necesite.
#    Si el header no existe o tiene formato incorrecto → 401 automático.
#
#    Se usa en TODOS los endpoints protegidos, no solo en /login.
#    En este router: auth_user lo usa para proteger /users/me.
oauth2 = OAuth2PasswordBearer(tokenUrl="/jwtauth/login")

# ------------------------------------------------------------------
# MOTOR DE HASHING
# ------------------------------------------------------------------
# PasswordHash.recommended() configura automáticamente Argon2id,
# el algoritmo más seguro disponible actualmente.
# Lo instanciamos UNA sola vez a nivel de módulo (es costoso de crear).
password_hash = PasswordHash.recommended()

# Hash ficticio para protección anti timing-attack.
DUMMY_HASH = password_hash.hash("dummypassword")

# ------------------------------------------------------------------
# BASE DE DATOS SIMULADA
# ------------------------------------------------------------------
# Simulamos una BD no relacional con un diccionario.
# En producción esto sería una consulta a MongoDB, PostgreSQL, etc.
# Las contraseñas son hashes Argon2 generados en consola con:
#  python3 -c "from pwdlib import PasswordHash; ph = PasswordHash.recommended(); print(f'Mouredev: {ph.hash(\"123456\")}'); print(f'Mouredev2: {ph.hash(\"654321\")}')"
users_db = {
    "mouredev": {
        "username": "mouredev",
        "full_name": "Brais Moure",
        "email": "braismoure@mouredev.com",
        "disabled": False,
        "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$z7RZVKOKNTQ//bTm0hsyDQ$eSD7wFDOW4BYOI97zrNlamNg6Pfpzm/2pfFaYUVPHVQ"
    },
    "mouredev2": {
        "username": "mouredev2",
        "full_name": "Brais Moure 2",
        "email": "braismoure2@mouredev.com",
        "disabled": True,
        "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$Gnrp+6mc45EDaG7o7J+8nQ$WF6HLhjiA19hHEbARICCuvJ/WliZqq34GGbVEyAHg6o"
    }
}

# ------------------------------------------------------------------
# MODELOS Pydantic
# ------------------------------------------------------------------

# Modelo de respuesta del endpoint /login.
# Solo devolvemos el token y su tipo, nunca datos del usuario aquí.
class Token(BaseModel):
    access_token: str
    token_type: str


# Datos que extraemos del payload del JWT una vez decodificado.
# El campo "sub" (subject) es el estándar JWT para identificar al usuario.
class TokenData(BaseModel):
    username: str | None = None


# Modelo PÚBLICO del usuario: lo que se devuelve en las respuestas.
# Nunca incluye la contraseña, ni siquiera el hash.
class User(BaseModel):
    username: str
    full_name: str
    email: str
    disabled: bool


# Modelo INTERNO del usuario: solo se usa dentro de la lógica de autenticación.
# Hereda de User y añade el hash de la contraseña.
# La separación User / UserDB es un patrón de seguridad fundamental:
# garantiza que nunca "se nos cuele" la contraseña en una respuesta.
class UserDB(User):
    hashed_password: str


# ------------------------------------------------------------------
# FUNCIONES AUXILIARES — USUARIOS
# ------------------------------------------------------------------

def search_user_db(username: str) -> UserDB | None:
    """Devuelve el usuario CON hash de contraseña. Solo para uso interno."""
    if username in users_db:
        return UserDB(**users_db[username])
    return None


def search_user(username: str) -> User | None:
    """Devuelve el usuario SIN contraseña. Para respuestas y dependencias."""
    if username in users_db:
        return User(**users_db[username])
    return None

# ------------------------------------------------------------------
# FUNCIONES AUXILIARES — CONTRASEÑAS
# ------------------------------------------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash.
    pwdlib maneja internamente la comparación segura (sin timing-attacks
    a nivel de comparación de strings).
    """
    return password_hash.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str) -> User | bool:
    """
    Proceso completo de autenticación:
    1. Busca al usuario en la BD.
    2. Si no existe: ejecuta verify_password contra DUMMY_HASH de todas formas.
       → Esto evita el "timing attack": sin este truco, un atacante podría
         saber si un usuario existe midiendo cuánto tarda el endpoint en responder
         (buscar + verificar hash tarda más que solo buscar y fallar).
    3. Si existe: verifica que la contraseña sea correcta.
    """
    user = search_user_db(username)
    if not user:
        verify_password(password, DUMMY_HASH)  # anti timing-attack
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# ------------------------------------------------------------------
# FUNCIONES AUXILIARES — JWT
# ------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Genera un token JWT firmado.

    El token contiene:
    - "sub" (subject): el identificador del usuario, que pasamos en `data`
    - "exp" (expiration): timestamp de expiración, que añadimos aquí

    Copiamos `data` antes de modificarlo porque los diccionarios en Python son
    mutables y se pasan por referencia.
    Si modificásemos `data` directamente, estaríamos cambiando el dict
    del llamador, lo que podría causar bugs muy difíciles de rastrear.
    """
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=15)
    )
    to_encode.update({"exp": expire})

    # jwt.encode() firma el payload con nuestra SECRET y devuelve un string
    return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)


# ------------------------------------------------------------------
# DEPENDENCIAS DE AUTENTICACIÓN
# ------------------------------------------------------------------

async def auth_user(token: str = Depends(oauth2)) -> User:
    """
    Primera capa: valida el JWT.

    FastAPI inyecta automáticamente el token del header:
        Authorization: Bearer <token>

    El flujo es:
    1. Intentamos decodificar el token con nuestra SECRET.
    2. jwt.decode() verifica la firma Y la expiración automáticamente.
       Si el token ha expirado, lanza InvalidTokenError sin que hagamos nada.
    3. Extraemos "sub" del payload y lo usamos para buscar al usuario.

    Si cualquier paso falla → 401 Unauthorized.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales de autenticaciÃ³n invÃ¡lidas",
        headers={"WWW-Authenticate": "Bearer"}
        # El header WWW-Authenticate es parte del estándar HTTP:
        # le dice al cliente qué esquema de autenticación usar.
    )

    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        # Captura cualquier problema: token malformado, expirado,
        # firma incorrecta, algoritmo no permitido...
        raise credentials_exception

    user = search_user(token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def current_user(user: User = Depends(auth_user)) -> User:
    """
    Segunda capa: verifica que el usuario no esté desactivado.

    Son dos dependencias separadas en vez de una sola, porque
    siguen el Principio de Responsabilidad Única (SRP):
    - auth_user  → "¿es este token válido?"
    - current_user → "¿está este usuario activo?"
    Son preguntas distintas y mantenerlas separadas facilita el testing
    y la reutilización (podrías tener endpoints que solo requieran auth_user).
    """
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    return user


# ------------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------------

@router.post("/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint de login. Recibe username y password como form-data (no JSON).
    Si las credenciales son correctas, devuelve un JWT firmado.

    ¿Por qué form-data y no JSON?
    Porque OAuth2 lo especifica así. Es el estándar que siguen todos
    los proveedores de identidad (Google, GitHub, etc.).

    --- Thunder Client ---
    POST http://localhost:8000/jwtauth/login
    Body → Form
      username: mouredev
      password: 123456
    """
    user = authenticate_user(form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseÃ±a incorrectos",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/users/me", response_model=User)
async def me(user: User = Depends(current_user)):
    """
    Endpoint protegido. Devuelve los datos del usuario autenticado.
    current_user (y por cascada auth_user) se ejecutan antes de llegar aquí.
    Si el token no es válido, FastAPI ni siquiera entra en esta función.

    --- Thunder Client ---
    GET http://localhost:8000/jwtauth/users/me
    Auth → Bearer Token → <pega el token del login>
    """
    return user