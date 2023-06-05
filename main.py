from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
import json
import bcrypt
import jwt
import secrets
from passlib.context import CryptContext
from datetime import datetime, timedelta

app = FastAPI()

# CORS Configuration
origins = ["*"]  # Update this with the appropriate origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Configuration
SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User Model
class User(BaseModel):
    username: str
    password: str

# Load User Data
def load_users():
    with open("users.json") as f:
        return json.load(f)

# Authenticate User
def authenticate_user(username: str, password: str):
    users = load_users()
    if username in users and pwd_context.verify(password, users[username]):
        return True
    return False

# def authenticate_user(username: str, password: str) -> Optional[User]:
#     if username in users_data and pwd_context.verify(password, users_data[username]):
#         return User(username, password)
#     return None



# Create Access Token
def create_access_token(data: Dict[str, str], expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Verify Access Token
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return True

# Routes
@app.post("/login")
def login(user: User):
    if authenticate_user(user.username, user.password):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid username or password")

@app.get("/protected")
def protected_route(token: str = Depends(oauth2_scheme)):
    verify_token(token)
    return {"message": "You are authenticated"}

# Product Model
class Product(BaseModel):
    product_id: int
    image: str
    name: str
    price: float
    quantity: int

# Load Product Data
def load_products():
    with open("products.json") as f:
        return json.load(f)

# Save Product Data
def save_products(data):
    with open("products.json", "w") as f:
        json.dump(data, f, indent=4)

# Protected Routes
@app.post("/cart/add")
def add_to_cart(product: Product, token: str = Depends(oauth2_scheme)):
    verify_token(token)
    products = load_products()
    products.append(product.dict())
    save_products(products)
    return {"message": "Product added to cart successfully"}

@app.put("/cart/update/{product_id}")
def update_cart(product_id: int, quantity: int, token: str = Depends(oauth2_scheme)):
    verify_token(token)
    products = load_products()
    for product in products:
        if product["product_id"] == product_id:
            product["quantity"] = quantity
            save_products(products)
            return {"message": "Cart updated successfully"}
    raise HTTPException(status_code=404, detail="Product not found in cart")

@app.delete("/cart/delete/{product_id}")
def delete_from_cart(product_id: int, token: str = Depends(oauth2_scheme)):
    verify_token(token)
    products = load_products()
    for product in products:
        if product["product_id"] == product_id:
            products.remove(product)
            save_products(products)
            return {"message": "Product deleted from cart successfully"}
    raise HTTPException(status_code=404, detail="Product not found in cart")

@app.get("/cart")
def get_cart(token: str = Depends(oauth2_scheme)):
    verify_token(token)
    products = load_products()
    total_price = sum(product["price"] * product["quantity"] for product in products)
    total_quantity = sum(product["quantity"] for product in products)
    return {
        "total_price": total_price,
        "total_quantity": total_quantity,
        "products": products
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
